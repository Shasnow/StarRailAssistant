import argparse
import re
import sys
from pathlib import Path
import locale
import codecs


def modify_version(file_path, new_version):
    """
    修改Inno Setup脚本中的版本号
    
    Args:
        file_path (str): Inno Setup脚本路径
        new_version (str): 新版本号
    """
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
        
        # 查找并替换版本号定义行
        modified = False
        for i, line in enumerate(content):
            if line.startswith('#define MyAppVersion'):
                content[i] = f'#define MyAppVersion "{new_version}"\n'
                modified = True
                break
        
        if not modified:
            print(f"Warning: Could not find '#define MyAppVersion' definition")
            return False
        
        # 写入修改后的内容
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(content)
        
        print(f"Successfully updated version to: {new_version}")
        return True
        
    except FileNotFoundError:
        print(f"Error: Cannot find file {file_path}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    # 设置标准输出编码为UTF-8，避免Windows环境下中文输出错误
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
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