"""The manifest is the only source of runtime settings.

Registry.settings() builds its dictionary strictly from the manifest fields, so a
knob that lives only in DEFAULTS is silently unreachable: the code falls back
through an exception path and the user cannot change it in Module settings.
"""
import json
from pathlib import Path
from open_notebook.modules.hybrid_search import service

MODULE = Path(__file__).parents[1]
MANIFEST = json.loads((MODULE / 'module.json').read_text())
FIELDS = {f['key']: f for f in MANIFEST['settings']}


def test_every_default_is_exposed_as_a_setting():
    missing = sorted(set(service.DEFAULTS) - set(FIELDS))
    assert not missing, f'only reachable through the fallback path: {missing}'


def test_no_setting_is_missing_a_default():
    assert not sorted(set(FIELDS) - set(service.DEFAULTS))


def test_manifest_defaults_match_the_code():
    for key, field in FIELDS.items():
        assert field['default'] == service.DEFAULTS[key], key


def test_numeric_defaults_sit_inside_their_own_bounds():
    for key, field in FIELDS.items():
        if field['kind'] == 'integer':
            assert field['minimum'] <= field['default'] <= field['maximum'], key


def test_every_field_declares_its_labels():
    for key, field in FIELDS.items():
        assert field.get('label_key') and field.get('help_key'), key


def test_declared_labels_exist_in_english_and_turkish():
    locales = (MODULE.parents[1] / 'frontend/src/lib/modules/locales.ts').read_text()
    for field in FIELDS.values():
        for entry in (field['label_key'], field['help_key']):
            name = entry.rsplit('.', 1)[-1]
            assert locales.count(f'"{name}":') >= 2, f'{name} is not translated in both locales'
