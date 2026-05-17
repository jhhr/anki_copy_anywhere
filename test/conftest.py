import os
import sys
import types
from unittest.mock import MagicMock

_test_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_test_dir)  # addon root
_addon_real_name = os.path.basename(_project_dir)  # e.g. "_1_copy_anywhere"

# The anki PyPI package has circular imports that only resolve inside a running
# Anki process.  Register MagicMock stubs for all Anki modules before anything
# imports them so that the circular-import chain is never triggered.
for _mod_name in [
    "anki",
    "anki.cards",
    "anki.notes",
    "anki.consts",
    "aqt",
]:
    sys.modules.setdefault(_mod_name, MagicMock())

# Register the addon and its subpackages under two names:
#   1. The current directory name, whatever it is — guards against pytest's
#      import machinery triggering __init__.py, which would call mw.addonManager
#      at module level and crash outside of Anki.
#   2. A stable alias (_anki_addon) — lets test files import without depending
#      on the current directory name.
# Each stub carries a __path__ pointing to the real directory on disk so that
# Python finds and loads actual .py files on first import, and so that relative
# imports inside those files (e.g. `from ..utils.to_lowercase_dict import ...`)
# still resolve to the real modules.
_STABLE_PACKAGE = "_anki_addon"
for _base in [_addon_real_name, _STABLE_PACKAGE]:
    for _name, _path in [
        (_base, _project_dir),
        (f"{_base}.logic", os.path.join(_project_dir, "logic")),
        (f"{_base}.utils", os.path.join(_project_dir, "utils")),
    ]:
        _mod = types.ModuleType(_name)
        _mod.__path__ = [_path]
        _mod.__package__ = _name
        sys.modules[_name] = _mod
