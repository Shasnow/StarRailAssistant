#!/usr/bin/env python3
"""
更新项目版本号的脚本
"""
import os
import re
import sys
import json
import argparse

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 要更新的文件路径
FILES = {
    'cs': os.path.join(PROJECT_ROOT, 'SRAFrontend', 'Models', 'AppSettings.cs'),
    'const.py': os.path.join(PROJECT_ROOT, 'SRACore', 'util', 'const.py'),
    'package.json': os.path.join(PROJECT_ROOT, 'package.json')
}

def update_file_version(file_path, version):
    """更新文件中的版本号
    
    Args:
        file_path: 文件路径
        version: 新版本号
    """
    try:
        # 从文件后缀推断文件类型
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == '.json':
            file_type = 'json'
        elif file_ext == '.cs':
            file_type = 'cs'
        elif file_ext == '.py':
            file_type = 'py'
        else:
            print(f"[ERROR] 不支持的文件类型: {file_ext}")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if file_type == 'json':
            # 处理 JSON 文件
            data = json.loads(content)
            if 'version' in data:
                data['version'] = version
                new_content = json.dumps(data, indent=2, ensure_ascii=False)
                updated = True
            else:
                updated = False
        else:
            # 处理 CS 和 PY 文件
            if file_type == 'cs':
                pattern = r'public const string Version = "([^"]+)";'
                replacement = f'public const string Version = "{version}";'
            else:  # py
                pattern = r'VERSION = "([^"]+)"'
                replacement = f'VERSION = "{version}"'
            
            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, content)
                updated = True
            else:
                updated = False
        
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[OK] 更新 {os.path.basename(file_path)} 版本号为: {version}")
        else:
            print(f"[ERROR] 未找到 {os.path.basename(file_path)} 中的版本号")
    except Exception as e:
        print(f"[ERROR] 更新 {os.path.basename(file_path)} 时出错: {str(e)}")

def get_current_version():
    """从文件中获取当前版本号"""
    # 从 package.json 文件中获取当前版本号
    version_json_path = FILES['package.json']
    if os.path.exists(version_json_path):
        with open(version_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'version' in data:
            return data['version']
    
    # 如果 package.json 不存在或没有版本号，尝试从其他文件获取
    const_py_path = FILES['const.py']
    if os.path.exists(const_py_path):
        with open(const_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = r'VERSION = "([^"]+)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    
    # 如果都获取不到，返回默认版本号
    return "1.0.0"

def increment_version(version, level='patch'):
    """递增版本号

    Args:
        version: 当前版本号
        level: 递增级别，可选值: 'patch'(默认), 'minor', 'major', 'prerelease'

    Behavior:
        - 'major', 'minor', 'patch' 操作仍然作用于核心版本号，保持现有的后缀（如果有）
        - 'prerelease' 在存在后缀时递增后缀中最后一个数字部分（例如 beta.1 -> beta.2）;
          如果后缀中无数字则追加 '.1'；如果没有后缀则默认添加 'beta.1'
    """
    # 分离版本号的核心部分和后缀部分（如 -beta.1）
    core_version = version
    suffix = ''
    if '-' in version:
        core_version, suffix = version.split('-', 1)

    # 解析核心版本号为数字列表
    parts = core_version.split('.')
    # 确保至少有三个部分
    while len(parts) < 3:
        parts.append('0')

    # 转换为整数（只针对核心部分）
    parts = [int(part) for part in parts]

    # 处理 prerelease 单独逻辑
    if level == 'prerelease':
        # 如果没有后缀，默认添加 beta.1
        if not suffix:
            return f"{core_version}-beta.1"

        # 尝试将后缀按 '.' 分割，找到最后一个数字段并递增
        idents = suffix.split('.')
        for i in range(len(idents) - 1, -1, -1):
            if re.fullmatch(r"\d+", idents[i]):
                idents[i] = str(int(idents[i]) + 1)
                new_suffix = '.'.join(idents)
                return f"{core_version}-{new_suffix}"

        # 如果没有纯数字段，尝试在最后一段尾部寻找数字并递增（例如 beta1 -> beta2）
        m = re.match(r"^(.*?)(\d+)$", idents[-1])
        if m:
            prefix = m.group(1)
            num = m.group(2)
            idents[-1] = f"{prefix}{int(num) + 1}"
            new_suffix = '.'.join(idents)
            return f"{core_version}-{new_suffix}"

        # 如果完全没有数字段，则追加 .1
        idents.append('1')
        new_suffix = '.'.join(idents)
        return f"{core_version}-{new_suffix}"

    # 根据级别递增核心版本号
    if level == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif level == 'minor':
        parts[1] += 1
        parts[2] = 0
    else:  # patch (默认)
        parts[2] += 1

    # 重新组合版本号并保留后缀（如果有）
    new_core_version = '.'.join(map(str, parts))
    if suffix:
        return f"{new_core_version}-{suffix}"
    return new_core_version



def main():
    """主函数"""
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(
        description='更新项目版本号的脚本',
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 添加位置参数：直接指定版本号
    parser.add_argument(
        'version',
        nargs='?',
        help='直接指定版本号，例如: 2.11.0'
    )
    
    # 添加 --increment 选项：递增版本号
    parser.add_argument(
        '--increment', '-i',
        nargs='?',
        const='patch',
        choices=['patch', 'minor', 'major', 'prerelease'],
        help='递增版本号，可选级别: patch (默认), minor, major, prerelease\n'
             "例如: --increment minor 将 2.10.0 递增为 2.11.0；"
             "--increment prerelease 将 2.12.0-beta.1 递增为 2.12.0-beta.2"
    )
    
    # 添加 --release 选项：转换为正式版
    parser.add_argument(
        '--release', '-r',
        action='store_true',
        help='转换为正式版（移除beta后缀）\n'
             '例如: 将 2.11.0-beta.2 转换为 2.11.0'
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 确定要使用的版本号
    if args.version:
        # 直接指定版本号
        version = args.version
    elif args.increment:
        # 递增版本号
        current_version = get_current_version()
        version = increment_version(current_version, args.increment)
        print(f"当前版本号: {current_version}")
        print(f"递增后版本号: {version}")
    elif args.release:
        # 转换为正式版
        current_version = get_current_version()
        # 移除任何后缀，只保留核心版本号
        if '-' in current_version:
            version = current_version.split('-')[0]
        else:
            version = current_version
        print(f"当前版本号: {current_version}")
        print(f"转换后版本号: {version}")
    else:
        # 没有提供任何参数，显示帮助信息
        parser.print_help()
        sys.exit(1)
    
    print(f"开始更新版本号为: {version}")
    print("=" * 50)
    
    # 检查文件是否存在
    for file_name, file_path in FILES.items():
        if not os.path.exists(file_path):
            print(f"[ERROR] 文件不存在: {file_path}")
            sys.exit(1)
    
    # 更新各个文件
    update_file_version(FILES['cs'], version)
    update_file_version(FILES['const.py'], version)
    update_file_version(FILES['package.json'], version)
    
    print("=" * 50)
    print("版本号更新完成！")

if __name__ == "__main__":
    main()
