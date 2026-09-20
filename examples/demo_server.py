"""A tiny API for trying out SpecSentinel.

By default it drifts from examples/petstore.yaml on purpose:
  GET /pets/{id}  returns id as a string, leaves out name, adds an unknown field
  GET /stats      answers 503, which the spec does not document

Start it with --conform to get a server that matches the spec exactly.

    python examples/demo_server.py            # drifting
    python examples/demo_server.py --conform  # matching
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def make_handler(drift: bool):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the terminal quiet
            pass

        def _send(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/health":
                return self._send(200, {"status": "ok"})
            if path == "/pets":
                return self._send(200, [
                    {"id": 1, "name": "Rex", "status": "available"},
                    {"id": 2, "name": "Mia", "tag": "cat", "status": "sold"},
                ])
            if path.startswith("/pets/"):
                pet_id = path.rsplit("/", 1)[1]
                if pet_id == "999":
                    return self._send(404, {"code": 404, "message": "pet not found"})
                if drift:
                    return self._send(200, {"id": pet_id, "breed": "terrier",
                                            "status": "available"})
                return self._send(200, {"id": int(pet_id), "name": "Rex",
                                        "status": "available"})
            if path == "/stats":
                if drift:
                    return self._send(503, {"error": "warming up"})
                return self._send(200, {"total": 12, "active": 9})
            if path.startswith("/owners/"):
                return self._send(200, {"id": 1, "name": "Sam"})
            return self._send(404, {"code": 404, "message": "not found"})

    return Handler


def serve(port: int = 8099, drift: bool = True) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(drift))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--conform", action="store_true",
                        help="answer exactly as the spec describes")
    args = parser.parse_args()
    server = serve(args.port, drift=not args.conform)
    mode = "matching the spec" if args.conform else "drifting from the spec"
    print(f"Demo API on http://127.0.0.1:{args.port} ({mode}). Stop with Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
