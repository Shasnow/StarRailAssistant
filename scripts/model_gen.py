#!/usr/bin/env python3
"""
根据 C# 模型自动生成统一的 Pydantic 模型。

全仓库只保留这一套 Python 侧模型定义，它同时服务两端：
- SRACore 运行时：``to_dict`` / ``from_dict`` 读写 settings.json 与 configs/*.json；
- SRAServer：作为 ``/openapi/v1.json`` 中 WebUI 动态表单依赖的组件。

字段名沿用 C# 侧的名字（``[ObservableProperty]`` 的私有字段去掉前导下划线，普通属性保持
原样），因此运行时调用点无需改动；JSON 键名与中文说明分别来自 ``[JsonPropertyName]`` 和
``[Description]``。
"""
import os
import re
import sys
import argparse


# C# 类型到 Python 类型的映射
CSHARP_TYPE_MAPPING = {
    'string': 'str',
    'int': 'int',
    'bool': 'bool',
    'double': 'float',
    'long': 'int',
    'decimal': 'float',
    'object': 'Any',
    'JsonElement': 'Any',
}

# 无默认值时按类型回退的字面量
TYPE_DEFAULTS = {
    'str': '""',
    'int': '0',
    'bool': 'False',
    'float': '0.0',
}

CLASS_PATTERN = re.compile(r'^\s*public\s+(partial\s+)?class\s+(\w+)\s*(:[^{}]*)?$', re.MULTILINE)

# 属性声明：前置特性块（可同行/换行、可多个） + 类型 + 字段名 + 可选的默认值
PROPERTY_PATTERN = re.compile(
    r'(?P<attrs>(?:\[[^\]]*\]\s*)+)'
    r'(?:private|public)\s+(?:partial\s+)?'
    r'(?P<type>[^\s<>]+(?:<[^>]+>)?)\s+_?(?P<name>\w+)'
    # 尾部 `;` 可选：自动属性（`public int Level { get; set; }`）不以分号结尾
    r'\s*(?:\{[^}]*\})?(?:\s*=\s*(?P<default>[^;]+))?;?',
    re.DOTALL,
)

JSON_NAME_PATTERN = re.compile(r'JsonPropertyName\("([^"]+)"\)')
DESCRIPTION_PATTERN = re.compile(r'Description\("([^"]*)"\)')

# 常量声明：如 `public static int StaticVersion => 4;`，用于解析默认值里引用的常量
CONST_PATTERN = re.compile(r'(?:static|const)\s+[\w<>\[\]?.]+\s+(\w+)\s*(?:=>|=)\s*([^;]+);')


def extract_class_content(content: str, start_index: int) -> str:
    """提取类的内容，处理嵌套的花括号"""
    brace_count = 1
    result = []

    i = start_index
    while i < len(content) and brace_count > 0:
        char = content[i]
        if char == '{':
            brace_count += 1
            result.append(char)
        elif char == '}':
            brace_count -= 1
            if brace_count > 0:
                result.append(char)
        else:
            result.append(char)
        i += 1

    return ''.join(result)


def convert_csharp_type(csharp_type: str) -> str:
    """将C#类型转换为Python类型"""
    if csharp_type in CSHARP_TYPE_MAPPING:
        return CSHARP_TYPE_MAPPING[csharp_type]

    generic_match = re.match(r'(\w+)<(\w+)>', csharp_type)
    if generic_match:
        base_type = generic_match.group(1)
        inner_type = generic_match.group(2)

        if base_type in ('List', 'ObservableCollection'):
            inner_python_type = CSHARP_TYPE_MAPPING.get(inner_type, inner_type)
            return f'list[{inner_python_type}]'

    return csharp_type


def is_list_type(python_type: str) -> bool:
    """判断是否为列表类型"""
    return python_type.startswith('list[') and python_type.endswith(']')


def get_list_inner_type(python_type: str) -> str:
    """获取列表元素类型"""
    if not is_list_type(python_type):
        return python_type
    return python_type[len('list['):-1].strip()


def parse_const_table(content: str) -> dict[str, str]:
    """收集文件内的常量/静态属性表达式，用于把默认值中的标识符解析回字面量"""
    return {name: value.strip() for name, value in CONST_PATTERN.findall(content)}


def parse_csharp_file(file_path: str) -> tuple[list[dict], dict[str, str]]:
    """解析C#文件，提取类信息与常量表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    const_table = parse_const_table(content)

    classes = []
    for match in CLASS_PATTERN.finditer(content):
        class_name = match.group(2)
        brace_start = content.find('{', match.end())
        if brace_start == -1:
            continue

        class_content = extract_class_content(content, brace_start + 1)
        classes.append({
            'name': class_name,
            'properties': parse_properties(class_content),
        })

    return classes, const_table


def parse_properties(class_content: str) -> list[dict]:
    """从类内容中解析属性：JSON 键名、Python 字段名/类型、默认值与中文说明

    支持的写法：
    - 普通属性：``[JsonPropertyName("xxx")] public Type Name { get; set; } = value;``
    - CommunityToolkit 属性：``[ObservableProperty] [property: JsonPropertyName("xxx")]
      [property: Description("...")] private Type _name = value;``（同行或换行均可）
    - 没有 ``[Description]`` 的属性其 description 为 None，生成时不输出该参数
    """
    properties = []
    for match in PROPERTY_PATTERN.finditer(class_content):
        attrs = match.group('attrs')
        json_match = JSON_NAME_PATTERN.search(attrs)
        if not json_match:
            # 没有 [JsonPropertyName] 的成员不参与 JSON 序列化，跳过
            continue

        description_match = DESCRIPTION_PATTERN.search(attrs)
        csharp_type = match.group('type')
        properties.append({
            'name': match.group('name'),
            'json_name': json_match.group(1),
            'csharp_type': csharp_type,
            'python_type': convert_csharp_type(csharp_type),
            'csharp_default': match.group('default').strip() if match.group('default') else None,
            'description': description_match.group(1) if description_match else None,
        })

    return properties


def convert_csharp_default(
    csharp_default: str | None,
    python_type: str,
    class_names: list[str],
    const_table: dict[str, str],
) -> str:
    """将C#默认值转换为 ``Field(...)`` 的参数表达式"""
    if csharp_default and csharp_default in const_table:
        return convert_csharp_default(const_table[csharp_default], python_type, class_names, const_table)

    # 嵌套自定义类：使用工厂默认值，保证可递归序列化
    if python_type in class_names:
        return f'default_factory={python_type}'

    if is_list_type(python_type):
        return 'default_factory=list'

    if csharp_default is None:
        return TYPE_DEFAULTS.get(python_type, 'None')

    if csharp_default == 'true':
        return 'True'
    if csharp_default == 'false':
        return 'False'
    if csharp_default == 'null':
        return 'None'

    if csharp_default.startswith('"') and csharp_default.endswith('"'):
        return csharp_default
    if csharp_default.startswith("'") and csharp_default.endswith("'"):
        return csharp_default

    if re.fullmatch(r'-?\d+', csharp_default):
        return f'{csharp_default}.0' if python_type == 'float' else csharp_default
    if re.fullmatch(r'-?\d+\.\d+', csharp_default):
        return csharp_default

    if csharp_default.startswith('new(') or csharp_default.startswith('new '):
        return 'default_factory=list'

    # 无法识别时按类型回退
    return TYPE_DEFAULTS.get(python_type, 'None')


def class_docstring(class_name: str, parent_description: str | None) -> str:
    """生成类的文档字符串。

    注意：Pydantic 生成 JSON Schema 时，若某个模型字段的说明与其 ``$ref`` 目标的说明
    **完全同文**，会丢弃字段侧那份（视为重复）。因此这里在复用父属性说明时统一补上句号，
    保证两者不同文，字段说明才能出现在 OpenAPI 组件里。
    """
    if parent_description:
        return f'{parent_description}。'
    return f'自动生成的 {class_name} 类'


def generate_python_class(
    class_info: dict,
    class_names: list[str],
    const_table: dict[str, str],
    class_descriptions: dict[str, str],
) -> str:
    """生成 Pydantic 模型类代码"""
    class_name = class_info['name']
    docstring = class_docstring(class_name, class_descriptions.get(class_name))

    lines = [
        f'class {class_name}(_Model):',
        f'    """{docstring}"""',
        '',
    ]

    for prop in class_info['properties']:
        default = convert_csharp_default(
            prop['csharp_default'], prop['python_type'], class_names, const_table
        )
        params = [default, f'alias="{prop["json_name"]}"']
        if prop['description']:
            params.append(f'description={prop["description"]!r}')
        lines.append(f'    {prop["name"]}: {prop["python_type"]} = Field({", ".join(params)})')

    lines.extend([
        '',
        '    def to_dict(self) -> dict:',
        '        """转换为字典（键为 C# 侧的 JSON 名称）"""',
        '        return self.model_dump(by_alias=True)',
        '',
        '    @classmethod',
        f'    def from_dict(cls, data: dict) -> "{class_name}":',
        '        """从字典创建对象"""',
        '        return cls.model_validate(data)',
    ])

    return '\n'.join(lines)


def generate_header(source_name: str, needs_any: bool) -> list[str]:
    """生成Python文件头部（模块说明与生成模型基类）"""
    lines = [
        '#!/usr/bin/env python3',
        '"""',
        '自动生成的 Pydantic 模型',
        f'源文件: {source_name}',
        '',
        'SRACore 运行时与 SRAServer 的 OpenAPI 组件共用这一套模型定义，请勿手工编辑：',
        '改动请修改对应的 C# 模型并执行 `npm run modelgen`。',
        '"""',
        '',
        'from __future__ import annotations',
        '',
    ]
    if needs_any:
        lines.extend(['from typing import Any', ''])
    lines.extend([
        'from pydantic import BaseModel, ConfigDict, Field',
        '',
        '',
        'class _Model(BaseModel):',
        '    """生成模型基类：允许按字段名或 JSON 别名构造，并保留未知键。"""',
        '',
        '    model_config = ConfigDict(populate_by_name=True, extra="allow")',
        '',
    ])
    return lines


def class_dependencies(class_info: dict, class_names: list[str]) -> set[str]:
    """类依赖的其他类（含列表元素类型），用于排序与前向引用检测"""
    dependencies = set()
    for prop in class_info['properties']:
        for candidate in (prop['python_type'], get_list_inner_type(prop['python_type'])):
            if candidate in class_names and candidate != class_info['name']:
                dependencies.add(candidate)
    return dependencies


def sort_classes_by_dependency(classes: list[dict], class_names: list[str]) -> list[dict]:
    """按依赖关系排序类：被嵌套引用的类先输出，避免前向引用导致解析失败"""
    ordered: list[dict] = []
    emitted: set[str] = set()
    pending = list(classes)

    while pending:
        progress = False
        remaining = []
        for class_info in pending:
            if class_dependencies(class_info, class_names) <= emitted:
                ordered.append(class_info)
                emitted.add(class_info['name'])
                progress = True
            else:
                remaining.append(class_info)
        if not progress:  # 存在循环依赖时保持原顺序
            ordered.extend(remaining)
            break
        pending = remaining

    return ordered


def find_forward_references(ordered: list[dict], class_names: list[str]) -> list[str]:
    """找出引用了后置类（循环依赖等）的类名，需要在其后补 ``model_rebuild()``"""
    index = {class_info['name']: i for i, class_info in enumerate(ordered)}
    forward = []
    for i, class_info in enumerate(ordered):
        if any(index[dep] > i for dep in class_dependencies(class_info, class_names)):
            forward.append(class_info['name'])
    return forward


def build_class_descriptions(classes: list[dict]) -> dict[str, str]:
    """用引用它的属性说明作为类的文档字符串（如 ``startGame`` 的"启动游戏配置"）"""
    descriptions: dict[str, str] = {}
    for class_info in classes:
        for prop in class_info['properties']:
            for candidate in (prop['python_type'], get_list_inner_type(prop['python_type'])):
                if prop['description'] and candidate not in descriptions:
                    descriptions[candidate] = prop['description']
    return descriptions


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='根据C#类自动生成对应的Python类')
    parser.add_argument('input', help='C#文件路径')
    parser.add_argument('-o', '--output', help='输出Python文件路径')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'[ERROR] 文件不存在: {args.input}')
        sys.exit(1)

    classes, const_table = parse_csharp_file(args.input)
    class_names = [class_info['name'] for class_info in classes]
    needs_any = any(
        'Any' in prop['python_type']
        for class_info in classes
        for prop in class_info['properties']
    )

    output_lines = generate_header(args.input, needs_any)
    ordered = sort_classes_by_dependency(classes, class_names)
    class_descriptions = build_class_descriptions(classes)

    for class_info in ordered:
        output_lines.append(generate_python_class(class_info, class_names, const_table, class_descriptions))
        output_lines.append('')

    forward_references = find_forward_references(ordered, class_names)
    if forward_references:
        output_lines.append('# 存在前向引用（循环依赖），统一在此解析')
        for class_name in forward_references:
            output_lines.append(f'{class_name}.model_rebuild()')
        output_lines.append('')

    output = '\n'.join(output_lines)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f'[OK] Python类已生成到: {args.output}')
    else:
        print(output)


if __name__ == '__main__':
    main()