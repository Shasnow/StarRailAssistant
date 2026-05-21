#!/usr/bin/env python3
"""
清理脚本 - 递归删除项目中的 __pycache__ 文件夹

用法：
    python scripts/clean.py
    python scripts/clean.py --dry-run  # 仅预览，不实际删除
    python scripts/clean.py --path /path/to/project  # 指定路径
"""

import argparse
import shutil
from pathlib import Path


# 默认排除的目录
DEFAULT_EXCLUDE_DIRS = {
    '.venv',
    'venv',
    'env',
    '.git',
    'node_modules',
}


def remove_pycache_folders(
    root_dir: Path,
    dry_run: bool = False,
    exclude_dirs: set[str] = DEFAULT_EXCLUDE_DIRS
) -> int:
    """
    递归遍历目录并删除 __pycache__ 文件夹
    
    Args:
        root_dir: 要扫描的根目录
        dry_run: 如果为 True，仅预览不实际删除
        exclude_dirs: 要排除的目录名称集合
    
    Returns:
        删除的文件夹数量
    """
    count = 0
    
    for item in root_dir.iterdir():
        if item.is_dir():
            # 跳过排除的目录
            if item.name in exclude_dirs:
                continue
            
            # 检查是否为 __pycache__ 文件夹
            if item.name == '__pycache__':
                if dry_run:
                    print(f"[DRY RUN] 将删除: {item}")
                    count += 1
                else:
                    try:
                        shutil.rmtree(item)
                        print(f"已删除: {item}")    
                    except Exception as e:
                        print(f"删除失败 {item}: {e}")
            else:
                # 递归处理子目录
                count += remove_pycache_folders(item, dry_run, exclude_dirs)
    
    return count


def main():
    parser = argparse.ArgumentParser(description='清理项目中的 __pycache__ 文件夹')
    parser.add_argument('--dry-run', action='store_true', 
                        help='仅预览删除操作，不实际执行')
    parser.add_argument('--path', type=str, default='.',
                        help='要扫描的根目录，默认为当前目录')
    
    args = parser.parse_args()
    
    root_dir = Path(args.path).resolve()
    
    if not root_dir.exists():
        print(f"错误: 目录不存在 - {root_dir}")
        return
    
    print(f"{'[DRY RUN] ' if args.dry_run else ''}开始扫描目录: {root_dir}")
    print(f"排除目录: {', '.join(sorted(DEFAULT_EXCLUDE_DIRS))}")
    print("=" * 60)
    
    count = remove_pycache_folders(root_dir, args.dry_run)
    
    print("=" * 60)
    if args.dry_run:
        print(f"[DRY RUN] 预览完成，共找到 {count} 个 __pycache__ 文件夹")
    else:
        print(f"清理完成，共删除 {count} 个 __pycache__ 文件夹")


if __name__ == '__main__':
    main()
