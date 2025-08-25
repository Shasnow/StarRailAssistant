from pathlib import Path

from rich.progress import Progress

ui_dir = Path('resources/ui')  # .ui 文件目录
generated_result_dir = Path('SRACore/ui')  # 生成的 Python 文件目录


def compile_ui_files():
    """编译 .ui 文件为 Python 代码，并显示进度条"""
    import os

    # 获取所有.ui文件
    ui_files = list(ui_dir.glob('*.ui'))
    total_files = len(ui_files)

    if not ui_files:
        print("没有找到任何.ui文件！")
        return

    # 创建进度条
    with Progress() as progress:
        task = progress.add_task("[green]编译.ui文件...", total=total_files)

        for ui_file in ui_files:
            # 构建命令
            output_file = generated_result_dir / ui_file.name.replace('.ui', '_ui.py')
            command = f"pyside6-uic {ui_file} > {output_file}"

            # 执行命令
            exit_code = os.system(command)

            # 检查是否成功
            if exit_code != 0:
                progress.console.print(f"[bold red]错误:[/bold red] 编译 {ui_file.name} 失败")
            else:
                progress.console.print(f"[blue]已编译:[/blue] {ui_file.name} -> {output_file.name}")

            # 更新进度条
            progress.update(task, advance=1)


if __name__ == '__main__':
    compile_ui_files()