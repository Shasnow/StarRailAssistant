import sys

if __name__ == '__main__':
    args=sys.argv[1:]
    if 'run' in args:
        from SRACore.thread.task_thread import TaskManager

        task_manager = TaskManager()
        try:
            task_manager.run()
        except KeyboardInterrupt:
            task_manager.stop()
            exit(0)
    else:
        from SRACore.SRA import SRA
        SRA.run()
