import argparse
import io
import re
import sys
from pathlib import Path


def to_numeric_version(version: str) -> str:
    """将版本号转为 Inno Setup 要求的 x.x.x.x 纯数字格式"""
    cleaned = version.lstrip('v')
    # 去掉预发布后缀，如 -beta.1, -rc.2
    cleaned = re.split(r'[-+]', cleaned)[0]
    parts = cleaned.split('.')
    # 补齐到 4 段
    while len(parts) < 4:
        parts.append('0')
    return '.'.join(parts[:4])


def modify_version(file_path, new_version):
    """
    修改Inno Setup脚本中的版本号

    Args:
        file_path (str): Inno Setup脚本路径
        new_version (str): 新版本号
    """
    try:
        numeric_version = to_numeric_version(new_version)

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()

        modified_version = False
        modified_numeric = False
        for i, line in enumerate(content):
            if line.startswith('#define MyAppVersion'):
                content[i] = f'#define MyAppVersion "{new_version}"\n'
                modified_version = True
            elif line.startswith('#define MyAppNumericVersion'):
                content[i] = f'#define MyAppNumericVersion "{numeric_version}"\n'
                modified_numeric = True

        if not modified_version:
            print("Warning: Could not find '#define MyAppVersion' definition")
            return False

        # 如果没有 MyAppNumericVersion 定义，在 MyAppVersion 后插入
        if not modified_numeric:
            for i, line in enumerate(content):
                if line.startswith('#define MyAppVersion'):
                    content.insert(i + 1, f'#define MyAppNumericVersion "{numeric_version}"\n')
                    break

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(content)

        print(f"Successfully updated version to: {new_version} (numeric: {numeric_version})")
        return True

    except FileNotFoundError:
        print(f"Error: Cannot find file {file_path}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    # 设置标准输出编码为UTF-8，避免Windows环境下中文输出错误
    stdout = sys.stdout
    if isinstance(stdout, io.TextIOWrapper):
        stdout.reconfigure(encoding="utf-8")
    
    parser = argparse.ArgumentParser(description='Modify version number in Inno Setup script')
    parser.add_argument('--version', '-v', required=True, help='New version number')
    parser.add_argument('--file', '-f', default='setup/srasetup.iss', 
                       help='Inno Setup script path (default: setup/srasetup.iss)')
    
    args = parser.parse_args()
    
    # 确保在项目根目录运行
    root_path = Path(__file__).parent.parent
    iss_path = root_path / args.file
    
    success = modify_version(iss_path, args.version)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()