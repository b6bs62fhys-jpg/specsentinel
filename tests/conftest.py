import importlib.util
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = str(ROOT / "examples" / "petstore.yaml")


def _load_demo_server():
    path = ROOT / "examples" / "demo_server.py"
    module_spec = importlib.util.spec_from_file_location("demo_server", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


@pytest.fixture
def spec_path():
    return SPEC_PATH


@pytest.fixture
def start_server():
    demo = _load_demo_server()
    servers = []

    def _start(drift: bool) -> str:
        server = demo.serve(port=0, drift=drift)  # port 0 lets the OS pick a free port
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield _start
    for server in servers:
        server.shutdown()
        server.server_close()
