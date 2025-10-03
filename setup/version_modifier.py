import argparse
import re
import sys
from pathlib import Path


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
            print(f"警告: 未找到 '#define MyAppVersion' 定义")
            return False
        
        # 写入修改后的内容
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(content)
        
        print(f"成功将版本号更新为: {new_version}")
        return True
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='修改Inno Setup脚本中的版本号')
    parser.add_argument('--version', '-v', required=True, help='新版本号')
    parser.add_argument('--file', '-f', default='setup/srasetup.iss', 
                       help='Inno Setup脚本路径 (默认: setup/srasetup.iss)')
    
    args = parser.parse_args()
    
    # 确保在项目根目录运行
    root_path = Path(__file__).parent.parent
    iss_path = root_path / args.file
    
    success = modify_version(iss_path, args.version)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()