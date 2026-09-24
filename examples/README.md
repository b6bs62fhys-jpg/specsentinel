# Examples

Every example starts the demo API from `demo_server.py` on a local port, runs
SpecSentinel against it and stops the API again. Run them from anywhere with
SpecSentinel installed (`pip install specsentinel`) and bash:

| Script | What it shows | Ends with |
|---|---|---|
| `01_simple_run.sh` | A plain run against `petstore.yaml`: first the conforming demo API (match), then the drifting one (missing field, wrong type, undocumented status). | exit code 1 (drift) |
| `02_baseline.sh` | Adopting SpecSentinel on an API that already drifts: `--write-baseline` records today's findings, `--baseline` accepts them, so only new drift fails. | exit code 0 (all drift is known) |
| `03_swagger2.sh` | A Swagger 2.0 source (`swagger2.yaml`) for the same API. It is translated to OpenAPI 3 in memory and finds the same drift. | exit code 1 (drift) |

```
bash examples/01_simple_run.sh
bash examples/02_baseline.sh
bash examples/03_swagger2.sh
```

Settings through the environment: `PORT` (default 8099; example 1 also uses
`PORT + 1`), `PYTHON` (default `python3`) and, for example 2, `WORKDIR` for
the baseline file (default: a new temporary directory).

The other files:

* `demo_server.py`: the demo API. It drifts by default; `--conform` matches the spec.
* `petstore.yaml`: the OpenAPI 3 document of the demo API.
* `swagger2.yaml`: the same API as a Swagger 2.0 document.
* `split/`: the OpenAPI document split over two files with `$ref`.

`tests/test_examples.py` runs all three scripts on every test run.
