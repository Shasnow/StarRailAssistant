"""Import and dispatch compatibility without a game or installed GUI dependencies.

Each check runs in a fresh, bytecode-disabled child process. It imports every
production currency_wars module, the five real task modules, and the real task
registry; no application imports are removed or rewritten. External services,
configuration types and GUI adapters are stubbed. Gameplay and strategy loading
are mocked only after import, so these checks cover loading/dispatch compatibility,
not OCR accuracy, the bundled core binary, or actual gameplay. An audit hook
rejects file writes in the child, and its module substitutions never reach the
parent test process.
"""
from __future__ import annotations

import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TASK_NAMES = (
    "StartGameTask", "TrailblazePowerTask", "ReceiveRewardsTask",
    "CosmicStrifeTask", "MissionAccomplishTask",
)


def _forbid_writes(event, args):
    if event == "open":
        mode, flags = args[1], args[2]
        if (isinstance(mode, str) and any(flag in mode for flag in "wax+")) or (
            isinstance(flags, int)
            and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            raise AssertionError("Isolation probe attempted a file write")
    elif event in {"os.mkdir", "os.remove", "os.rename", "os.rmdir",
                   "os.system", "subprocess.Popen", "socket.connect"}:
        raise AssertionError(f"Isolation probe attempted external I/O: {event}")


def _stub(name, *, package_path=None, **attributes):
    module = types.ModuleType(name)
    if package_path is not None:
        module.__path__ = [str(package_path)]
    module.__dict__.update(attributes)
    sys.modules[name] = module
    return module


def _unexpected_io(*args, **kwargs):
    raise AssertionError("Isolation probe reached an unstubbed game/service action")


class _QuietLogger:
    def __getattr__(self, name):
        if name in {"trace", "debug", "info", "success", "warning", "error", "exception"}:
            return lambda *args, **kwargs: None
        raise AssertionError(f"Task attempted to reconfigure the shared logger: {name}")


def _install_shared_boundaries():
    # Keep real lightweight core code (task registry, boxes, errors and matchers).
    # Import the real source interfaces while stubbing external service boundaries.
    core = ROOT / "SRACore"
    logger = _QuietLogger()
    _stub("SRACore", package_path=core)
    _stub("SRACore.util", package_path=core / "util")
    _stub("SRACore.operators", package_path=core / "operators")
    _stub("SRACore.models", package_path=core / "models")
    _stub("loguru", logger=logger)
    _stub("SRACore.util.logger", logger=logger)
    _stub("SRACore.localization", Resource=types.SimpleNamespace())
    _stub("SRACore.models.tasks_config", TasksConfig=object, TrailblazePowerTaskItem=object)
    _stub("SRACore.operators.ioperator", IOperator=object)
    _stub("SRACore.operators.factory",
          OperatorType=types.SimpleNamespace(Local="Local", Browser="Browser"))
    _stub("SRACore.notification", try_send_notification=_unexpected_io)
    _stub("SRACore.util.const", LogsScreenshotDir=ROOT / "unexpected_probe_output")
    _stub("SRACore.util.encryption", decrypt=_unexpected_io, encrypt=_unexpected_io)
    _stub("SRACore.util.sys_util", task_kill=_unexpected_io,
          shutdown=_unexpected_io, sleep_system=_unexpected_io)
    _stub("PIL", package_path="")
    _stub("PIL.Image", Image=object)
    _stub("typing_extensions", deprecated=lambda *args, **kwargs: lambda value: value)


class _NoGameOperator:
    def __init__(self):
        self.settings = types.SimpleNamespace(General=types.SimpleNamespace(hotkeyF4="f4"))

    def __getattr__(self, name):
        raise AssertionError(f"Probe attempted a game/operator operation: {name}")


def _import_production_tree(tree):
    sys.path.insert(0, str(tree))
    _install_shared_boundaries()
    # This follows the existing eager import path from the shared task entry.
    cosmic = importlib.import_module("tasks.CosmicStrifeTask")
    package = importlib.import_module("tasks.currency_wars")
    imported = []
    for path in sorted((tree / "tasks" / "currency_wars").glob("*.py")):
        if path.stem == "__init__":
            continue
        module = importlib.import_module("tasks.currency_wars." + path.stem)
        assert Path(module.__file__).resolve() == path.resolve(), module.__name__
        imported.append(path.stem)
    for name in TASK_NAMES:
        module = importlib.import_module("tasks." + name)
        assert Path(module.__file__).resolve() == (tree / "tasks" / (name + ".py")).resolve()
    divergent = importlib.import_module("tasks.divergent_universe.DivergentUniverse")
    assert Path(divergent.__file__).resolve() == (
        tree / "tasks" / "divergent_universe" / "DivergentUniverse.py").resolve()
    return cosmic, package, divergent, imported


def _cosmic_config(**overrides):
    values = dict(
        isDivergentUniverseEnabled=False, divergentUniverseRuntimes=1,
        isDivergentUniverseUseTechnique=False, isPointRewardsEnabled=False,
        divergentUniverseMode=0, isCurrencyWarsEnabled=False,
    )
    values.update(overrides)
    return types.SimpleNamespace(CosmicStrife=types.SimpleNamespace(**values))


def _probe_exports(package, imported):
    main = importlib.import_module("tasks.currency_wars.CurrencyWars")
    reroll = importlib.import_module("tasks.currency_wars.RerollStart")
    registry = importlib.import_module("SRACore.task").task_registry
    assert registry.get_ids() == list(TASK_NAMES), registry.get_ids()
    assert package.CurrencyWars is main.CurrencyWars
    assert package.RerollStart is reroll.RerollStart
    assert package.StageName is main.StageName
    assert issubclass(package.RerollStart, package.CurrencyWars)
    return {"tasks": registry.get_ids(), "modules": imported, "exports": list(package.__all__)}


def _probe_divergent_only(cosmic, package, divergent):
    operator = _NoGameOperator()
    original_operator_state = copy.deepcopy(vars(operator))
    task = cosmic.CosmicStrifeTask(operator, _cosmic_config(isDivergentUniverseEnabled=True))
    cls = divergent.DivergentUniverse
    # Run the real DU constructor and run method; replace only gameplay steps.
    with patch.object(cls, "page_locate", autospec=True, return_value=True) as locate, \
         patch.object(cls, "_start_divergent_universe", autospec=True, return_value=True) as start, \
         patch.object(cls, "game_loop", autospec=True, return_value=True) as loop, \
         patch.object(cls, "_return_to_main_menu", autospec=True) as ending, \
         patch.object(package.CurrencyWars, "__init__", side_effect=AssertionError("CW was enabled")), \
         patch.object(package.RerollStart, "__init__", side_effect=AssertionError("Reroll was enabled")):
        assert task.run() is True
        instance = locate.call_args.args[0]
        assert type(instance) is cls and instance.operator is operator
        locate.assert_called_once_with(instance)
        start.assert_called_once_with(instance, 0)
        loop.assert_called_once_with(instance)
        ending.assert_called_once_with(instance)
    assert vars(operator) == original_operator_state
    return {"divergent_run": True, "currency_wars_constructed": False}


def _probe_modes(cosmic, package):
    operator = _NoGameOperator()
    original_operator_state = copy.deepcopy(vars(operator))
    modes = []
    for mode in (0, 1, 2):
        config = _cosmic_config(
            isCurrencyWarsEnabled=True, currencyWarsMode=mode,
            currencyWarsUsername="隔离测试", currencyWarsStrategy="probe_strategy",
            currencyWarsRuntimes=2, currencyWarsDifficulty=1,
            currencyWarsRerollBossNames="", currencyWarsRerollBossAffixes="",
            currencyWarsRerollInvestEnvironments="", currencyWarsRerollInvestStrategies="",
        )
        task = cosmic.CosmicStrifeTask(operator, config)
        selected = package.RerollStart if mode == 2 else package.CurrencyWars
        with patch.object(package.CurrencyWars, "load_strategy", autospec=True) as strategy, \
             patch.object(package.CurrencyWars, "run", autospec=True, return_value=True) as run:
            assert task.run() is True
            instance = run.call_args.args[0]
            assert type(instance) is selected
            assert instance.operator is operator and instance.runtimes == 2
            assert instance.difficulty == 1
            assert instance.is_overclock is (mode == 1)
            strategy.assert_called_once_with(instance, "probe_strategy")
            run.assert_called_once_with(instance)
            assert task.notify is (mode != 2)
        modes.append(selected.__name__)
    assert vars(operator) == original_operator_state
    return {"selected_classes": modes}


def _run_child(tree, scenario):
    sys.dont_write_bytecode = True
    sys.addaudithook(_forbid_writes)
    cosmic, package, divergent, imported = _import_production_tree(tree)
    _probe_exports(package, imported)
    if scenario == "exports":
        result = _probe_exports(package, imported)
    elif scenario == "divergent":
        result = _probe_divergent_only(cosmic, package, divergent)
    elif scenario == "modes":
        result = _probe_modes(cosmic, package)
    else:
        raise AssertionError(f"Unknown probe: {scenario}")
    print(json.dumps(result, ensure_ascii=True))


class CurrencyWarsModuleIsolationTests(unittest.TestCase):
    def probe(self, tree, scenario):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--probe", str(tree), scenario],
            cwd=tree, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_source_other_task_registration_and_original_exports(self):
        result = self.probe(ROOT, "exports")
        self.assertEqual(result["tasks"], list(TASK_NAMES))
        self.assertIn("CurrencyWars", result["modules"])

    def test_source_currency_disabled_keeps_divergent_entry(self):
        self.assertTrue(self.probe(ROOT, "divergent")["divergent_run"])

    def test_source_regular_overclock_and_reroll_dispatch(self):
        self.assertEqual(self.probe(ROOT, "modes")["selected_classes"],
                         ["CurrencyWars", "CurrencyWars", "RerollStart"])








if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--probe":
        _run_child(Path(sys.argv[2]).resolve(), sys.argv[3])
    else:
        unittest.main()
