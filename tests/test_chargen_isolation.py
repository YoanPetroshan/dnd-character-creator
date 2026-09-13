import ast, pathlib
FORBIDDEN = {"flask", "flask_cors", "engine", "anthropic", "openai"}

def test_chargen_imports_nothing_from_the_app_or_a_model():
    """chargen must stay a pure rules library: importable with no server, no
    campaign root, and nothing that can call a model."""
    root = pathlib.Path(__file__).resolve().parent.parent / "chargen"
    offenders = []
    for py in root.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            for m in mods:
                if m.split(".")[0] in FORBIDDEN:
                    offenders.append(f"{py.name}: {m}")
    assert offenders == [], offenders
