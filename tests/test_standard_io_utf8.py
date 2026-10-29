from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('codepage', ['cp1251', 'cp1252', 'gbk'])
def test_standard_streams_roundtrip_without_replacement(codepage):
    env = dict(os.environ, PYTHONIOENCODING=codepage + ':strict', PYTHONUTF8='0')
    text = '中文 Русский English ё — →'
    code = ('import sys; from SRACore.util.standard_io import configure_standard_streams; '
            'configure_standard_streams(); text=sys.stdin.readline().rstrip("\\n"); '
            'print(text); print(text, file=sys.stderr)')
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                            input=(text + '\n').encode('utf-8'), capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode('utf-8').strip() == text
    assert result.stderr.decode('utf-8').strip() == text


def test_in_memory_capture_streams_are_not_replaced(monkeypatch):
    from SRACore.util.standard_io import configure_standard_streams
    streams = [io.StringIO() for _ in range(3)]
    for name, stream in zip(('stdin', 'stdout', 'stderr'), streams):
        monkeypatch.setattr(sys, name, stream)
    configure_standard_streams()
    assert [sys.stdin, sys.stdout, sys.stderr] == streams


@pytest.mark.parametrize('codepage', ['cp1251', 'cp1252', 'gbk'])
@pytest.mark.parametrize('language', [0, 1, 2])
def test_read_only_cli_metadata_under_legacy_windows_codepages(codepage, language, tmp_path):
    state = tmp_path / 'SRA'
    state.mkdir()
    (state / 'settings.json').write_text(json.dumps({'display': {'language': language}}), encoding='utf-8')
    env = dict(os.environ, APPDATA=str(tmp_path), HOME=str(tmp_path),
               PYTHONIOENCODING=codepage + ':strict', PYTHONUTF8='0')
    # Metadata/help only: do not instantiate an operator or run any task/extension.
    commands = ('extension schema 中文Русский --json\nextension schema CurrencyWarsPlus --json\n'
                'extension list --json\ntask list --json\nhelp\nquit\n')
    result = subprocess.run([sys.executable, str(ROOT / 'main.py'), '--inline', '--no-admin'],
                            cwd=ROOT, env=env, input=commands.encode('utf-8'), capture_output=True, timeout=45)
    assert result.returncode == 0, result.stderr
    stdout, stderr = (value.decode('utf-8') for value in (result.stdout, result.stderr))
    assert 'UnicodeEncodeError' not in stdout + stderr
    assert 'UnicodeDecodeError' not in stdout + stderr
    assert '\ufffd' not in stdout + stderr
    responses = [json.loads(line) for line in stdout.splitlines() if line.startswith('{')]
    assert any('中文Русский' in item.get('message', '') for item in responses)
    schema = next(item['data'] for item in responses if isinstance(item.get('data'), dict)
                  and 'properties' in item['data'])
    assert schema['properties']['难度']['enum'] == [0, 1, 2]
    if language == 2:
        assert schema['properties']['难度']['x-enum-labels'] == ['Минимальная', 'Максимальная', 'Текущая']
