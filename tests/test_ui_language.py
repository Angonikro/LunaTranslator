from pathlib import Path
import ast

def test_version_is_0218():
    namespace = {}
    exec((Path(__file__).parents[1] / "version.py").read_text(), namespace)
    assert namespace["VERSION"] == "0.2.18"

def test_translation_dictionary_contains_core_labels():
    source = (Path(__file__).parents[1] / "lunatranslator/ui/main_window.py").read_text()
    tree = ast.parse(source)
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)]
    mapping = next(n.value for n in assignments if any(isinstance(t, ast.Name) and t.id == "TRANSLATIONS" for t in n.targets))
    keys = {k.value for k in mapping.keys if isinstance(k, ast.Constant)}
    assert "Übersetzen" in keys
    assert "Einstellungen" in keys
    assert "Übersetzungsverlauf" in keys


def test_translation_preserves_button_padding_whitespace():
    source = (Path(__file__).parents[1] / "lunatranslator/ui/main_window.py").read_text()
    assert "stripped = text.strip()" in source
    assert "leading + translated + trailing" in source
