from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re
import string
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET

import pytest

from SRACore.localization import Resources

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def restore_language():
    original = Resources.lang
    yield
    Resources.set_language(original)


def fields(text):
    return Counter(re.findall(r'\{(\d+)(?:[^{}]*)\}', text))


def test_existing_resource_keys_and_placeholders():
    resources = [json.loads((ROOT / f'SRACore/localization/resources_{lang}.json').read_text(encoding='utf-8'))
                 for lang in ('zh-cn', 'en-us', 'ru-ru')]
    assert resources[0].keys() == resources[1].keys() == resources[2].keys()
    for key in resources[0]:
        def placeholders(value):
            return Counter((f, spec, conv) for _, f, spec, conv in string.Formatter().parse(value) if f is not None)
        assert placeholders(resources[0][key]) == placeholders(resources[1][key]) == placeholders(resources[2][key])
        assert resources[2][key] or not resources[0][key]
    Resources.set_language(2)
    assert Resources.lang == 'ru-ru'
    assert Resources.task_notificationTitle == 'Уведомление о задачах'
    assert '2/3' in Resources.task_retryPreparing(2, 3)
    assert 'Тест' in Resources.task_retryFromConfig('Тест')


def test_toml_is_authoritative_for_all_generated_languages():
    from scripts.pyl10nc.__main__ import normalize_data
    data = normalize_data(tomllib.loads((ROOT / 'SRACore/localization/resources.toml').read_text(encoding='utf-8')))
    for language in ('zh-cn', 'en-us', 'ru-ru'):
        generated = json.loads((ROOT / f'SRACore/localization/resources_{language}.json').read_text(encoding='utf-8'))
        assert generated == {key: value[language] for key, value in data.items()}


def test_resource_attributes_used_in_code_are_generated():
    """`Resources.<attr>` 必须对应生成类里的真实成员。

    `Localization.__getattribute__` 在属性缺失时回退到 `get_translation(name)`，
    再退化为原样返回键名，因此 `hasattr` 恒为真，只能静态比对 AST。
    """
    from SRACore.localization.resources import Localization

    available = {name for name in dir(Localization) if not name.startswith('_')}
    missing: list[str] = []
    for path in ROOT.rglob('*.py'):
        if {'.venv', 'node_modules', 'static', 'log'} & set(path.parts):
            continue
        if path == ROOT / 'SRACore/localization/resources.py':
            continue
        source = path.read_text(encoding='utf-8')
        if 'Resources' not in source:
            continue
        tree = ast.parse(source)
        if not any(isinstance(node, ast.ImportFrom)
                   and node.module in {'SRACore.localization', 'SRACore.localization.resources'}
                   and any(alias.name == 'Resources' for alias in node.names)
                   for node in ast.walk(tree)):
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == 'Resources' and node.attr not in available):
                missing.append(f'{path.relative_to(ROOT).as_posix()}:{node.lineno}: Resources.{node.attr}')
    assert not missing, '未定义的资源属性:\n' + '\n'.join(missing)


def test_gui_resource_keys_and_placeholders():
    directory = ROOT / 'SRAFrontend/SRAFrontend/Localization'
    sets = [{node.attrib['name']: node.findtext('value') or ''
             for node in ET.parse(directory / f'Resources{language}.resx').findall('data')}
            for language in ('', '.zh', '.ru-RU')]
    assert sets[0].keys() == sets[1].keys() == sets[2].keys()
    for key, russian in sets[2].items():
        assert '\ufffd' not in russian and '???' not in russian
        assert russian.strip() or not sets[1][key].strip()
        assert fields(sets[1][key]) == fields(russian), key
        assert fields(sets[0][key]) == fields(sets[1][key]), key


def test_xaml_keys_and_literal_cyrillic_have_resources():
    directory = ROOT / 'SRAFrontend/SRAFrontend/Localization'
    keys = {node.attrib['name'] for node in ET.parse(directory / 'Resources.resx').findall('data')}
    for path in (ROOT / 'SRAFrontend/SRAFrontend.Desktop').rglob('*.axaml'):
        for key in re.findall(r'lang:Resources\.(\w+)', path.read_text(encoding='utf-8-sig')):
            assert key in keys, (str(path), key)


def test_currency_wars_schema_carries_locales_metadata():
    from extensions.currency_wars_plus import CurrencyWarsPlusConfig
    from SRACore.extension import extension_registry, load_extensions

    load_extensions()
    Resources.set_language(2)
    schema = extension_registry.get_schema('CurrencyWarsPlus')
    assert schema is not None
    assert schema['properties']['难度']['x-enum-labels'] == ['Минимальная', 'Максимальная', 'Текущая']
    for prop in schema['properties'].values():
        assert not re.search(r'[\u4e00-\u9fff]', prop.get('description', ''))
    config = CurrencyWarsPlusConfig.model_validate({'开拓者名称': 'Тест', '难度': 2})
    assert config.model_dump(by_alias=True)['开拓者名称'] == 'Тест'
    assert config.model_dump(by_alias=True)['难度'] == 2


def test_all_extension_schema_labels_and_descriptions_are_russian():
    from SRACore.extension import extension_registry, load_extensions
    load_extensions()
    Resources.set_language(2)

    for extension_id in extension_registry.get_ids():
        meta = extension_registry.get_meta(extension_id)
        assert meta, extension_id
        assert not re.search(r'[\u4e00-\u9fff]', meta.get('name', '')), extension_id
        assert not re.search(r'[\u4e00-\u9fff]', meta.get('description', '')), extension_id
        schema = extension_registry.get_schema(extension_id)
        if not schema:
            continue
        for key, prop in (schema.get('properties') or {}).items():
            if not isinstance(prop, dict):
                continue
            assert not re.search(r'[\u4e00-\u9fff]', prop.get('description', '')), (extension_id, key)
            # 动态枚举（如攻略文件名）属于用户内容，不参与 UI 文案断言。
            if prop.get('x-allow-custom'):
                continue
            for label in prop.get('x-enum-labels') or []:
                assert not re.search(r'[\u4e00-\u9fff]', label), (extension_id, key, label)


@pytest.mark.parametrize('language', [0, 1, 2])
def test_language_selection_survives_a_real_process_restart(language, tmp_path):
    import os
    state = tmp_path / 'SRA'
    state.mkdir()
    (state / 'settings.json').write_text(json.dumps({'display': {'language': language}}), encoding='utf-8')
    env = dict(os.environ, APPDATA=str(tmp_path), HOME=str(tmp_path))
    code = ('import json; from pathlib import Path; '
            'from SRACore.services.setting_service import SettingsService; '
            'from SRACore.localization import Resources; '
            'settings=SettingsService(); '
            'Path(settings.path).write_text(json.dumps(settings.settings.to_dict()), encoding="utf-8"); '
            'Resources.set_language(settings.settings.Display.Language); print(Resources.lang)')
    for _ in range(2):
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code], cwd=ROOT, env=env,
                                capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert result.stdout.decode('utf-8').strip() == ['zh-cn', 'en-us', 'ru-ru'][language]


def test_trailblaze_power_level_names_follow_interface_language():
    from tasks.taskcli import localize_subtasks

    subtasks = tomllib.loads((ROOT / 'tasks/config/trailblaze_power.toml').read_text(encoding='utf-8'))['subtasks']

    Resources.set_language(0)
    assert localize_subtasks(subtasks) == subtasks

    cases = ((1, 'Ornament Extraction', 'Fruit of Evil'), (2, 'Извлечение украшений', 'Роковое плодоношение'))
    for language, subtask_name, level_name in cases:
        Resources.set_language(language)
        localized = localize_subtasks(subtasks)
        assert localized['ornament_extraction']['name'] == subtask_name
        assert set(localized) == set(subtasks)
        for tid, subtask in subtasks.items():
            entry = localized[tid]
            # 识别与执行依赖的字段保持原样
            assert entry['func'] == subtask['func']
            assert entry['cost'] == subtask['cost']
            assert entry['max_count'] == subtask['max_count']
            assert [level['id'] for level in entry['levels']] == [level['id'] for level in subtask['levels']]
            for level in entry['levels']:
                assert not re.search(r'[\u4e00-\u9fff]', level['name'] + level['result']), (tid, level['id'])
        level = next(lv for lv in localized['ornament_extraction']['levels'] if lv['id'] == 9)
        assert level['name'] == level_name


def test_notification_payload_localizes_text_not_protocol_fields(monkeypatch):
    from SRACore.models.app_settings import NotificationSettings
    from SRACore.notification import service
    submitted = []
    monkeypatch.setattr(service._notification_executor, 'submit', lambda fn, ctx: submitted.append(ctx))
    Resources.set_language(2)
    service.try_send_notification(NotificationSettings(isEnabled=True), Resources.task_notificationTitle,
                                  Resources.notification_taskStarted('StartGameTask'), 'success')
    context = submitted[0]
    assert context.title == 'Уведомление о задачах'
    assert context.message == 'Задача StartGameTask запущена.'
    assert context.payload['result'] == 'success'
    assert set(context.payload) == {'title', 'message', 'result', 'timestamp', 'event'}
