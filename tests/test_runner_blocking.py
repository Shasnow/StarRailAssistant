import threading
import time

from SRACore.thread.runner import Runner


class DummyRunner(Runner):
    def __init__(self) -> None:
        super().__init__()
        self.started = threading.Event()
        self.finished = threading.Event()

    def work(self) -> None:
        self.started.set()
        time.sleep(0.1)
        self.finished.set()


def test_start_and_wait_blocks_until_worker_finishes() -> None:
    runner = DummyRunner()

    done = []

    def invoke() -> None:
        runner.start_and_wait(runner.work)
        done.append("finished")

    thread = threading.Thread(target=invoke, daemon=True)
    thread.start()

    assert runner.started.wait(timeout=1.0)
    assert not done
    assert runner.finished.wait(timeout=1.0)
    thread.join(timeout=1.0)

    assert done == ["finished"]
