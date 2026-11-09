import tempfile
from pathlib import Path

def test_history_module_imports():
    from lunatranslator.core.history import History
    assert History is not None
