import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent




def _load():
    spec = importlib.util.spec_from_file_location("spec_smoke", ROOT / "tools" / "spec_smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module




def test_smoke_script_finds_no_drift_in_conforming_examples():
    result = _load().run(str(ROOT / "examples" / "petstore.yaml"))
    assert result["operations"] > 0
    assert result["checked"] > 0
    assert result["flagged"] == 0
    assert result["crashes"] == 0




def test_smoke_script_handles_recursive_schemas():
    module = _load()
    spec = {"components": {"schemas": {"Node": {
        "type": "object", "required": ["name"],
        "properties": {"name": {"type": "string"}, "child": {"$ref": "#/components/schemas/Node"}}}}}}
    value = module.generate(spec, {"$ref": "#/components/schemas/Node"})
    assert value["name"] == "x"