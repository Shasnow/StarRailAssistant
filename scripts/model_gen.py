#!/usr/bin/env python3
"""
根据C#类自动生成对应的Python类
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
}


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


def parse_csharp_file(file_path: str) -> list[dict]:
    """解析C#文件，提取类信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    class_pattern = r'^\s*public\s+(partial\s+)?class\s+(\w+)\s*(:[^{}]*)?$'
    matches = list(re.finditer(class_pattern, content, re.MULTILINE))

    classes = []
    for match in matches:
        class_name = match.group(2)
        brace_start = content.find('{', match.end())
        if brace_start == -1:
            continue

        class_content = extract_class_content(content, brace_start + 1)
        properties = parse_properties(class_content)

        classes.append({
            'name': class_name,
            'is_partial': bool(match.group(1)),
            'base_classes': match.group(3).strip()[1:] if match.group(3) else '',
            'properties': properties
        })

    return classes


def parse_properties(class_content: str) -> list[dict]:
    """从类内容中解析属性，包括默认值"""
    # 匹配属性定义，支持两种格式：
    # 格式1：[property: JsonPropertyName("xxx")]\nprivate Type _name = value;
    # 格式2：[JsonPropertyName("xxx")]\npublic Type Name { get; set; } = value;
    # 支持有默认值和没有默认值的情况
    property_pattern = r'\[(?:property:\s*)?JsonPropertyName\("([^"]+)"\)\]\s*\n?\s*(?:private|public)\s+([^\s<>]+(?:<[^>]+>)?)\s+[_]?(\w+)\s*(?:\{[^}]+\})?(?:\s*=\s*([^;]+))?;?'
    prop_matches = re.findall(property_pattern, class_content, re.DOTALL)

    properties = []
    for match in prop_matches:
        json_name = match[0]
        csharp_type = match[1]
        prop_name = match[2]
        csharp_default = match[3].strip() if match[3] else None
        
        properties.append({
            'name': prop_name,
            'json_name': json_name,
            'csharp_type': csharp_type,
            'python_type': convert_csharp_type(csharp_type),
            'csharp_default': csharp_default
        })

    return properties


def convert_csharp_default(csharp_default: str | None, python_type: str) -> str:
    """将C#默认值转换为Python默认值"""
    # 如果没有默认值，使用类型默认值
    if csharp_default is None:
        defaults = {
            'str': '""',
            'int': '0',
            'bool': 'False',
            'float': '0.0',
        }
        if python_type.startswith('list'):
            return 'field(default_factory=list)'
        return defaults.get(python_type, 'None')

    if csharp_default == 'true':
        return 'True'
    elif csharp_default == 'false':
        return 'False'
    elif csharp_default == '[]':
        return 'field(default_factory=list)'
    elif csharp_default.startswith('new('):
        return 'None'
    elif csharp_default.startswith('"') and csharp_default.endswith('"'):
        return csharp_default
    elif csharp_default.startswith("'") and csharp_default.endswith("'"):
        return csharp_default
    elif '.' in csharp_default and csharp_default.replace('.', '').isdigit():
        return csharp_default
    elif csharp_default.isdigit():
        return csharp_default
    elif csharp_default.startswith('[') and csharp_default.endswith(']'):
        return 'field(default_factory=list)'
    else:
        # 如果无法识别，使用类型默认值
        defaults = {
            'str': '""',
            'int': '0',
            'bool': 'False',
            'float': '0.0',
        }
        if python_type.startswith('list'):
            return 'field(default_factory=list)'
        return defaults.get(python_type, 'None')


def generate_python_class(class_info: dict, class_names: list[str]) -> str:
    """生成Python类代码（使用dataclass）"""
    lines = ['@dataclass',
             f'class {class_info["name"]}:',
             f'    """自动生成的 {class_info["name"]} 类"""',
             '']

    for prop in class_info['properties']:
        # 使用从C#代码中提取的实际默认值
        default_value = convert_csharp_default(prop['csharp_default'], prop['python_type'])
        lines.append(f'    {prop["name"]}: {prop["python_type"]} = {default_value}')

    lines.append('')
    lines.append('    def to_dict(self) -> dict:')
    lines.append('        """转换为字典"""')

    # 生成to_dict方法的内容，处理子对象的递归转换
    to_dict_lines = []
    for prop in class_info['properties']:
        json_name = prop['json_name']
        prop_name = prop['name']
        prop_type = prop['python_type']

        # 如果属性类型是另一个自定义类，则调用其to_dict方法，添加空值检查
        if prop_type in class_names:
            to_dict_lines.append(f'"{json_name}": self.{prop_name}.to_dict()')
        else:
            to_dict_lines.append(f'"{json_name}": self.{prop_name}')

    lines.append('        return {')
    lines.append('            ' + ',\n            '.join(to_dict_lines))
    lines.append('        }')
    lines.append('')
    lines.append('    @classmethod')
    lines.append('    def from_dict(cls, data: dict):')
    lines.append('        """从字典创建对象"""')

    # 生成from_dict方法的内容，处理子对象的实例化
    from_dict_lines = []
    for prop in class_info['properties']:
        json_name = prop['json_name']
        prop_name = prop['name']
        prop_type = prop['python_type']

        # 如果属性类型是另一个自定义类，则调用其from_dict方法
        if prop_type in class_names:
            from_dict_lines.append(f'"{prop_name}": {prop_type}.from_dict(data.get("{json_name}", \u007b\u007d))')
        else:
            default_value = convert_csharp_default(prop['csharp_default'], prop['python_type'])
            if default_value == "field(default_factory=list)":
                default_value = 'list()'
            from_dict_lines.append(f'"{prop_name}": data.get("{json_name}", {default_value})')

    lines.append('        return cls(**{')
    lines.append('            ' + ',\n            '.join(from_dict_lines))
    lines.append('        })')

    return '\n'.join(lines)


def generate_header(file_path: str) -> list[str]:
    """生成Python文件头部"""
    return [
        '#!/usr/bin/env python3',
        '"""',
        '自动生成的Python类',
        f'源文件: {os.path.basename(file_path)}',
        '"""',
        '',
        'from __future__ import annotations',
        'from dataclasses import dataclass, field',
        '',
    ]


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='根据C#类自动生成对应的Python类')
    parser.add_argument('input', help='C#文件路径')
    parser.add_argument('-o', '--output', help='输出Python文件路径')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'[ERROR] 文件不存在: {args.input}')
        sys.exit(1)

    classes = parse_csharp_file(args.input)
    output_lines = generate_header(args.input)

    # 获取所有类名，用于在from_dict中判断是否需要递归实例化
    class_names = [c['name'] for c in classes]

    for class_info in classes:
        output_lines.append(generate_python_class(class_info, class_names))
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