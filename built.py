from pathlib import Path
import hashlib
import json
import os
from rich.progress import Progress
from rich.console import Console

ui_dir = Path('resources/ui')  # .ui 文件目录
generated_result_dir = Path('SRACore/ui')  # 生成的 Python 文件目录
hash_cache_file = Path('.ui_hash_cache.json')  # 哈希缓存文件
console = Console()


def calculate_md5(file_path: Path) -> str:
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def load_hash_cache() -> dict:
    """加载哈希缓存"""
    if hash_cache_file.exists():
        try:
            with open(hash_cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_hash_cache(cache: dict):
    """保存哈希缓存"""
    try:
        with open(hash_cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        console.print(f"[bold yellow]警告:[/bold yellow] 无法保存哈希缓存: {e}")


def compile_ui_file(ui_file: Path, output_file: Path) -> bool:
    """编译单个.ui文件"""
    command = f"pyside6-uic {ui_file} > {output_file}"
    exit_code = os.system(command)
    return exit_code == 0


def compile_ui_files():
    """编译.ui文件为Python代码，带哈希检测和进度条"""
    # 确保输出目录存在
    generated_result_dir.mkdir(parents=True, exist_ok=True)

    # 加载哈希缓存
    hash_cache = load_hash_cache()
    current_hashes = {}
    compiled_files = 0
    skipped_files = 0

    # 获取所有.ui文件
    ui_files = list(ui_dir.glob('*.ui'))
    total_files = len(ui_files)

    if not ui_files:
        console.print("[bold yellow]警告:[/bold yellow] 没有找到任何.ui文件！")
        return

    with Progress() as progress:
        task = progress.add_task("[green]编译.ui文件...", total=total_files)

        for ui_file in ui_files:
            # 计算当前哈希
            current_hash = calculate_md5(ui_file)
            current_hashes[ui_file.name] = current_hash
            output_file = generated_result_dir / ui_file.name.replace('.ui', '_ui.py')

            # 检查是否需要重新编译
            if ui_file.name in hash_cache and hash_cache[ui_file.name] == current_hash:
                if output_file.exists():
                    progress.console.print(f"[blue]跳过:[/blue] {ui_file.name} (未修改)")
                    skipped_files += 1
                    progress.update(task, advance=1)
                    continue

            # 编译文件
            if compile_ui_file(ui_file, output_file):
                progress.console.print(f"[green]已编译:[/green] {ui_file.name} -> {output_file.name}")
                compiled_files += 1
            else:
                progress.console.print(f"[bold red]错误:[/bold red] 编译 {ui_file.name} 失败")

            progress.update(task, advance=1)

    # 保存新的哈希缓存
    save_hash_cache(current_hashes)

    # 打印汇总信息
    console.print("\n[bold]编译完成:[/bold]")
    console.print(f"  - 总文件数: {total_files}")
    console.print(f"  - 编译文件: [green]{compiled_files}[/green]")
    console.print(f"  - 跳过文件: [blue]{skipped_files}[/blue]")


if __name__ == '__main__':
    compile_ui_files()