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
    """从类内容中解析属性"""
    property_pattern = r'\[(?:property:\s*)?JsonPropertyName\("([^"]+)"\)\]\s*\n?\s*(?:private|public)\s+([^\s<>]+(?:<[^>]+>)?)\s+[_]?(\w+)'
    prop_matches = re.findall(property_pattern, class_content, re.DOTALL)

    properties = []
    for json_name, csharp_type, prop_name in prop_matches:
        properties.append({
            'name': prop_name,
            'json_name': json_name,
            'csharp_type': csharp_type,
            'python_type': convert_csharp_type(csharp_type)
        })

    return properties


def get_default_value(python_type: str) -> str:
    """根据Python类型获取默认值"""
    defaults = {
        'str': '""',
        'int': '0',
        'bool': 'False',
        'float': '0.0',
    }

    if python_type.startswith('list'):
        return '[]'
    return defaults.get(python_type, 'None')


def generate_python_class(class_info: dict) -> str:
    """生成Python类代码（使用dataclass）"""
    lines = []
    lines.append('@dataclass')
    lines.append(f'class {class_info["name"]}:')
    lines.append(f'    """自动生成的 {class_info["name"]} 类"""')
    lines.append('')

    for prop in class_info['properties']:
        if prop['python_type'].startswith('list'):
            lines.append(f'    {prop["name"]}: {prop["python_type"]} = field(default_factory=list)')
        else:
            default_value = get_default_value(prop['python_type'])
            lines.append(f'    {prop["name"]}: {prop["python_type"]} = {default_value}')

    lines.append('')
    lines.append('    def to_dict(self) -> dict:')
    lines.append('        """转换为字典"""')
    lines.append('        return {')
    lines.append('            ' + ',\n            '.join(
        f'"{p["json_name"]}": self.{p["name"]}'
        for p in class_info['properties']
    ))
    lines.append('        }')
    lines.append('')
    lines.append('    @classmethod')
    lines.append('    def from_dict(cls, data: dict):')
    lines.append('        """从字典创建对象"""')
    lines.append('        return cls(**{')
    lines.append('            ' + ',\n            '.join(
        f'"{p["name"]}": data.get("{p["json_name"]}")'
        for p in class_info['properties']
    ))
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

    for class_info in classes:
        output_lines.append(generate_python_class(class_info))
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