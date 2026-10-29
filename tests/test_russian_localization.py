from __future__ import annotations

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

from SRACore.localization import Resource
from SRACore.localization.presentation import localize_schema, translate

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'SRACore/localization/presentation.json').read_text(encoding='utf-8'))


@pytest.fixture(autouse=True)
def restore_language():
    original = Resource.lang
    yield
    Resource.set_language(original)


def fields(text):
    return Counter(re.findall(r'\{(\d+)(?:[^{}]*)\}', text))


@pytest.mark.parametrize('entry', CATALOG, ids=lambda item: item['key'])
def test_presentation_placeholders_and_translation(entry):
    assert fields(entry['source']) == fields(entry['ru'])
    assert '\ufffd' not in entry['ru']
    assert '???' not in entry['ru']
    assert entry['ru'].strip()
    Resource.set_language('ru-RU')
    source = re.sub(r'\{(\d+)\}', lambda m: f'VALUE_{m[1]}', entry['source'])
    expected = re.sub(r'\{(\d+)\}', lambda m: f'VALUE_{m[1]}', entry['ru'])
    if len(re.sub(r'\{\d+\}', '', entry['source'])) >= 3 or not fields(entry['source']):
        assert translate(source) == expected


def test_original_languages_are_untouched():
    for language in (0, 1):
        Resource.set_language(language)
        for entry in CATALOG:
            assert translate(entry['source']) == entry['source']
        schema = {'properties': {'开拓者名称': {'type': 'string', 'description': '填写游戏内开拓者名称。'}}}
        assert localize_schema(schema) == schema


def test_existing_resource_keys_and_placeholders():
    resources = [json.loads((ROOT / f'SRACore/localization/resource_{lang}.json').read_text(encoding='utf-8'))
                 for lang in ('zh-cn', 'en-us', 'ru-ru')]
    assert resources[0].keys() == resources[1].keys() == resources[2].keys()
    for key in resources[0]:
        def placeholders(value):
            return Counter((f, spec, conv) for _, f, spec, conv in string.Formatter().parse(value) if f is not None)
        assert placeholders(resources[0][key]) == placeholders(resources[1][key]) == placeholders(resources[2][key])
        assert resources[2][key] or not resources[0][key]
    Resource.set_language(2)
    assert Resource.lang == 'ru-ru'
    assert Resource.task_notificationTitle == 'Уведомление о задачах'
    assert '2/3' in Resource.task_retryPreparing(2, 3)
    assert 'Тест' in Resource.task_retryFromConfig('Тест')


def test_toml_is_authoritative_for_all_generated_languages():
    from scripts.pyl10nc.__main__ import normalize_data
    data = normalize_data(tomllib.loads((ROOT / 'SRACore/localization/resource.toml').read_text(encoding='utf-8')))
    for language in ('zh-cn', 'en-us', 'ru-ru'):
        generated = json.loads((ROOT / f'SRACore/localization/resource_{language}.json').read_text(encoding='utf-8'))
        assert generated == {key: value[language] for key, value in data.items()}


@pytest.mark.parametrize('stem', ['Resources', 'ExtraResources'])
def test_gui_resource_keys_and_placeholders(stem):
    directory = ROOT / 'SRAFrontend/SRAFrontend/Localization'
    sets = [{node.attrib['name']: node.findtext('value') or ''
             for node in ET.parse(directory / f'{stem}{language}.resx').findall('data')}
            for language in ('', '.zh', '.ru-RU')]
    assert sets[0].keys() == sets[1].keys() == sets[2].keys()
    for key, russian in sets[2].items():
        assert '\ufffd' not in russian and '???' not in russian
        assert russian.strip() or not sets[1][key].strip()
        assert fields(sets[1][key]) == fields(russian), key


def test_xaml_keys_and_literal_cyrillic_have_resources():
    directory = ROOT / 'SRAFrontend/SRAFrontend/Localization'
    extra = {node.attrib['name'] for node in ET.parse(directory / 'ExtraResources.resx').findall('data')}
    for path in (ROOT / 'SRAFrontend/SRAFrontend.Desktop').rglob('*.axaml'):
        for key in re.findall(r'ExtraResources\.(\w+)', path.read_text(encoding='utf-8-sig')):
            assert key in extra, (str(path), key)


def test_currency_wars_schema_only_changes_presentation_metadata():
    from extensions.currency_wars_plus import CurrencyWarsPlusConfig
    Resource.set_language(0)
    original = CurrencyWarsPlusConfig.model_json_schema()
    before = deepcopy(original)
    Resource.set_language(2)
    localized = localize_schema(original)
    assert original == before

    def technical(value):
        if isinstance(value, dict):
            return {key: technical(item) for key, item in value.items()
                    if key not in ('title', 'description', 'x-enum-labels', 'x-refresh-label')}
        if isinstance(value, list):
            return [technical(item) for item in value]
        return value

    assert technical(localized) == technical(original)
    assert localized['properties']['难度']['x-enum-labels'] == ['Минимальная', 'Максимальная', 'Текущая']
    assert localized['properties']['攻略']['x-refresh-label'] == 'Сканировать папку стратегий'
    assert not re.search(r'[\u4e00-\u9fff]', localized['description'])
    config = CurrencyWarsPlusConfig.model_validate({'开拓者名称': 'Тест', '难度': 2})
    assert config.model_dump(by_alias=True)['开拓者名称'] == 'Тест'
    assert config.model_dump(by_alias=True)['难度'] == 2


def test_all_extension_schema_labels_and_descriptions_are_russian():
    from SRACore.extension import extension_registry, load_extensions
    load_extensions()
    Resource.set_language(2)

    def labels(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('title', 'description', 'x-refresh-label') and isinstance(item, str):
                    yield item
                elif key == 'x-enum-labels':
                    yield from item
                elif key not in ('enum', 'default', 'const', 'required', 'examples'):
                    yield from labels(item)
        elif isinstance(value, list):
            for item in value:
                yield from labels(item)

    for extension_id in extension_registry.get_ids():
        entry = extension_registry.get(extension_id)
        assert not re.search(r'[\u4e00-\u9fff]', translate(entry.name)), extension_id
        assert not re.search(r'[\u4e00-\u9fff]', translate(entry.description)), extension_id
        schema = extension_registry.get_schema(extension_id)
        if schema:
            for label in labels(localize_schema(schema)):
                assert not re.search(r'[\u4e00-\u9fff]', label), (extension_id, label)


@pytest.mark.parametrize('language', [0, 1, 2])
def test_language_selection_survives_a_real_process_restart(language, tmp_path):
    import os
    state = tmp_path / 'SRA'
    state.mkdir()
    (state / 'settings.json').write_text(json.dumps({'display': {'language': language}}), encoding='utf-8')
    env = dict(os.environ, APPDATA=str(tmp_path), HOME=str(tmp_path))
    code = ('import json; from pathlib import Path; '
            'from SRACore.service.setting_service import SettingsService; '
            'from SRACore.localization import Resource; '
            'settings=SettingsService(); '
            'Path(settings.path).write_text(json.dumps(settings.settings.to_dict()), encoding="utf-8"); '
            'Resource.set_language(settings.settings.Display.Language); print(Resource.lang)')
    for _ in range(2):
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code], cwd=ROOT, env=env,
                                capture_output=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert result.stdout.decode('utf-8').strip() == ['zh-cn', 'en-us', 'ru-ru'][language]


def test_notification_payload_localizes_text_not_protocol_fields(monkeypatch):
    from SRACore.models.app_settings import NotificationSettings
    from SRACore.notification import service
    submitted = []
    monkeypatch.setattr(service._notification_executor, 'submit', lambda fn, ctx: submitted.append(ctx))
    Resource.set_language(2)
    service.try_send_notification(NotificationSettings(isEnabled=True), Resource.task_notificationTitle,
                                  '任务 StartGameTask 开始执行。', 'success')
    context = submitted[0]
    assert context.title == 'Уведомление о задачах'
    assert context.message == 'Задача StartGameTask запущена.'
    assert context.payload['result'] == 'success'
    assert set(context.payload) == {'title', 'message', 'result', 'timestamp', 'event'}
