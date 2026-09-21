from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
CORE_INIT = ROOT / "mnemosyne" / "__init__.py"
HERMES_PROJECTS = (
    ROOT / "integrations" / "hermes" / "pyproject.toml",
    ROOT / "integrations" / "hermes-catalog" / "pyproject.toml",
)
LEGACY_HERMES_MANIFEST = ROOT / "integrations" / "hermes" / "plugin.yaml"
CORE_HERMES_MANIFEST = ROOT / "hermes_memory_provider" / "plugin.yaml"
REQUIRED_CORE_API = (
    ("mnemosyne.core.query_sanitize", "sanitize_prefetch_query"),
    ("mnemosyne.core.filters", "make_write_policy"),
    ("mnemosyne.core.filters", "resolve_write_policy"),
    ("mnemosyne.core.filters", "active_write_policy"),
    ("mnemosyne.core.filters", "current_write_policy"),
    ("mnemosyne.core.filters", "write_policy_operation"),
    ("mnemosyne.core.filters", "_SYSTEM_DERIVED_WRITE_CAPABILITY"),
    ("mnemosyne.core.filters", "admit_memory_write"),
    ("mnemosyne.core.verbatim_ledger", "VerbatimLedger"),
    ("mnemosyne.upgrade_hermes", "upgrade_command"),
)


def _core_version() -> str:
    tree = ast.parse(CORE_INIT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__version__":
                    value = ast.literal_eval(node.value)
                    assert isinstance(value, str)
                    return value
    raise AssertionError("mnemosyne.__version__ not found")


def _mnemosyne_memory_specs(project: Path) -> list[str]:
    data = tomllib.loads(project.read_text(encoding="utf-8"))
    specs = list(data["project"].get("dependencies", []))
    for values in data["project"].get("optional-dependencies", {}).values():
        specs.extend(values)
    return [spec for spec in specs if re.match(r"mnemosyne-memory(?:\[[^]]+\])?", spec)]


def test_hermes_packages_require_the_current_core_api_release() -> None:
    core_version = _core_version()
    for project in HERMES_PROJECTS:
        specs = _mnemosyne_memory_specs(project)
        assert specs, project
        assert all(f">={core_version}" in spec for spec in specs), (
            project,
            core_version,
            specs,
        )
    assert f"mnemosyne-memory>={core_version}" in LEGACY_HERMES_MANIFEST.read_text(
        encoding="utf-8"
    )
    assert f"version: {core_version}" in CORE_HERMES_MANIFEST.read_text(
        encoding="utf-8"
    )


def test_hermes_required_core_api_is_present() -> None:
    for module_name, symbol_name in REQUIRED_CORE_API:
        module = importlib.import_module(module_name)
        assert hasattr(module, symbol_name), (module_name, symbol_name)
