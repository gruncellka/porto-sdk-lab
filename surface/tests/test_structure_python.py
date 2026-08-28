from pathlib import Path

from surface.extract.structure_python import extract_python_module
from surface.render.structure import render_module_stub, render_structure_markdown

FIXTURE = Path(__file__).parent / "fixtures" / "python_sdk"


def test_extract_python_module_fixture():
    module = extract_python_module(
        FIXTURE / "porto_sdk" / "__init__.py",
        package_root=FIXTURE / "porto_sdk",
    )
    assert module["path"] == "__init__.py"
    names = {d["name"] for d in module["declarations"] if "name" in d}
    assert "ProviderClient" in names or any(
        d.get("name") == "ProviderClient" for d in module["declarations"]
    )


def test_render_python_stub_contains_signatures():
    module = extract_python_module(
        FIXTURE / "porto_sdk" / "__init__.py",
        package_root=FIXTURE / "porto_sdk",
    )
    stub = render_module_stub(module, language="python")
    assert "class ProviderClient" in stub
    assert "def resolve(" in stub or "async def mark(" in stub


def test_render_markdown_tree():
    from surface.extract.structure_python import extract_python_structure

    structure = extract_python_structure(FIXTURE)
    md = render_structure_markdown(structure)
    assert "porto_sdk/" in md
    assert "## Modules" in md
