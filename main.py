import sys

if __name__ == '__main__':
    args=sys.argv[1:]
    if '--no-gui' in args:
        from SRACore.thread.task_thread import TaskManager

        task_manager = TaskManager()
        task_manager.run()
    else:
        from SRACore.SRA import SRA
        SRA.run()
