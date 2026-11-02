"""扩展目录包与 ``locales/`` 约定的回归测试。"""
from __future__ import annotations

from pathlib import Path

from SRACore.extension import extension_registry, load_extensions
from SRACore.localization import Resources


def test_directory_packages_are_registered() -> None:
    load_extensions()
    ids = set(extension_registry.get_ids())
    assert {'CurrencyWarsPlus', 'HelloWorld'} <= ids


def test_schema_and_meta_follow_language() -> None:
    load_extensions()
    original = Resources.lang
    try:
        Resources.set_language(2)
        schema = extension_registry.get_schema('CurrencyWarsPlus')
        assert schema is not None
        difficulty = schema['properties']['难度']
        assert difficulty['x-enum-labels'] == ['Минимальная', 'Максимальная', 'Текущая']
        assert 'Выберите' in difficulty['description']
        assert 'x-i18n' not in difficulty
        assert extension_registry.get_meta('CurrencyWarsPlus')['name'] == 'Валютные войны Plus'

        Resources.set_language(1)
        schema = extension_registry.get_schema('CurrencyWarsPlus')
        assert schema is not None
        difficulty = schema['properties']['难度']
        assert difficulty['x-enum-labels'] == ['Lowest difficulty', 'Highest difficulty', 'Current difficulty']
        assert 'Choose the lowest difficulty' in difficulty['description']
        assert extension_registry.get_meta('CurrencyWarsPlus')['name'] == 'Currency Wars Plus'
    finally:
        Resources.set_language(original)


def test_legacy_single_file_extensions_are_ignored(tmp_path: Path) -> None:
    # 单文件扩展与无 __init__.py 的目录都不应被导入
    (tmp_path / 'legacy.py').write_text("raise RuntimeError('should not be imported')\n", encoding='utf-8')
    scores = tmp_path / 'scores'
    scores.mkdir()
    (scores / 'data.json').write_text('{}', encoding='utf-8')
    load_extensions(str(tmp_path))
