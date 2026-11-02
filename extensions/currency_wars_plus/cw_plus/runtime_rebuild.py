"""现有恢复层耗尽后，仅在本进程内串行交接一次任务。

上下文用于转移运行状态的所有权，不是可序列化的存档格式。
保留全部运行属性，包括不可变收据及其可变重试账本，防止后续功能
在交接时静默丢失已经消耗的预算。
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time


@dataclass(frozen=True)
class RuntimeFlowFailure:
    reason: str
    error: str
    recoverable: bool = True
    exhausted: bool = True


@dataclass
class RuntimeRecoveryContext:
    state: dict
    vision_state: dict
    session_id: str
    strategy_fingerprint: str
    process_id: int
    thread_id: int
    captured_at: float
    consumed: bool = False


# Yukki：同会话存档核对成功后才允许移交原始收据与预算。
def capture_runtime_recovery(engine):
    """保留完整收据，并在停用旧引擎前验证实际存档。"""
    failure = getattr(engine, '_runtime_flow_failure', None)
    if (not isinstance(failure, RuntimeFlowFailure) or not failure.recoverable
            or not failure.exhausted or getattr(engine, '_runtime_retired', False)
            or engine.is_game_over or getattr(engine, '_checkpoint_write_failed', False)):
        return None
    engine._check_stop()
    store = engine._session_store
    checkpoint = store.checkpoint if store is not None else None
    if (checkpoint is None or checkpoint.finalized
            or checkpoint.association not in ('new', 'resumed')
            or checkpoint.terminal_outcome != 'unknown'
            or checkpoint.execution_status == 'stopped' or store.last_error is not None):
        return None
    persisted, reason, _ = store._read()
    if reason != 'loaded' or persisted != checkpoint:
        return None
    # 旧引擎已经完整返回；直接交接状态容器，不重置或复制角色单例，
    # 停用后的旧引擎不再改动这些状态。
    excluded = {'operator', '_vision', 'special_events', '_runtime_flow_failure',
                '_runtime_retired'}
    state = {key: value for key, value in vars(engine).items() if key not in excluded}
    vision_state = {key: value for key, value in vars(engine._vision).items()
                    if key not in ('operator', 'stop_check', 'layout_api')}
    context = RuntimeRecoveryContext(state, vision_state, checkpoint.run_id,
        checkpoint.strategy_fingerprint, os.getpid(), threading.get_ident(), time.monotonic())
    engine._runtime_retired = True
    engine.is_running = False
    return context


def restore_runtime_recovery(engine, context):
    """仅限同一进程与宿主线程，原单调时钟截止时间继续有效。"""
    if (not isinstance(context, RuntimeRecoveryContext) or context.consumed
            or context.process_id != os.getpid() or context.thread_id != threading.get_ident()
            or time.monotonic() < context.captured_at):
        raise ValueError('Invalid or already consumed in-process recovery context')
    engine._check_stop()
    store = context.state.get('_session_store')
    checkpoint = store.checkpoint if store is not None else None
    persisted, reason, _ = store._read() if store is not None else (None, '', '')
    if (checkpoint is None or checkpoint.run_id != context.session_id
            or checkpoint.strategy_fingerprint != context.strategy_fingerprint
            or checkpoint.finalized or checkpoint.terminal_outcome != 'unknown'
            or store.last_error is not None or reason != 'loaded' or persisted != checkpoint):
        raise ValueError('Recovery checkpoint no longer matches the original session')
    context.consumed = True
    vars(engine).update(context.state)
    vars(engine._vision).update(context.vision_state)
    engine._vision.stop_check = engine._check_stop
    engine._runtime_flow_failure = None
    engine._runtime_retired = False
    engine._runtime_rebuild_active = True
    engine.is_running = True
    engine._check_stop()


class RuntimeRebuildBudget:
    """跨引擎实例的重建额度仅由外层控制器持有。"""
    def __init__(self):
        self.used = False
        self.last_battle_id = None
        self.session_id = None
        self.battle_lower_bound = 0

    def consume(self, context):
        state = context.state
        battle_id = state.get('_last_completed_battle_id')
        count = state.get('_confirmed_battle_lower_bound', 0)
        progressed = (battle_id is not None and battle_id != self.last_battle_id
            and type(count) is int and count > 0
            and (context.session_id != self.session_id or count > self.battle_lower_bound))
        if self.used and not progressed:
            return False
        self.used = True  # 构造新对象前即消耗额度，即使构造失败也不重授。
        self.last_battle_id = battle_id
        self.session_id = context.session_id
        self.battle_lower_bound = count
        return True


# ssyb：外层先消耗唯一额度，旧引擎返回后再构造替换对象。
def run_with_runtime_rebuild(engine, factory):
    """不创建线程、不另开游戏，用户停止后不重试。"""
    budget = RuntimeRebuildBudget()
    result = engine.run()
    while not result:
        engine._check_stop()
        context = engine.export_runtime_rebuild_context()
        if context is None or not budget.consume(context):
            return False
        # 导出只在旧引擎运行返回后将其停用；停止信号仍属于原操作器，
        # 新引擎接收上下文前还须重新检查。
        event = getattr(engine.operator, 'stop_event', None)
        if event is not None and event.is_set():
            return False
        try:
            replacement = factory()
        except (OSError, ValueError, TypeError):
            return False
        replacement._check_stop()
        result = replacement.resume_runtime_rebuild(context)
        engine = replacement
    return result
