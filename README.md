# SpecSentinel

[![PyPI](https://img.shields.io/pypi/v/specsentinel)](https://pypi.org/project/specsentinel/)
[![Python](https://img.shields.io/pypi/pyversions/specsentinel)](https://pypi.org/project/specsentinel/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![tests](https://github.com/b6bs62fhys-jpg/specsentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/b6bs62fhys-jpg/specsentinel/actions/workflows/ci.yml)

SpecSentinel checks a running API against its OpenAPI document. It calls every GET operation, compares each response with the spec and reports where the two disagree, from missing fields and wrong types to undocumented status codes. The exit code tells a pipeline what happened: 0 for a match, 1 for drift and 2 if the check could not be completed.

## What it is for

* A CI check that runs on every push or pull request and fails the build when the live API no longer matches its spec.
* It sends GET requests only. On a well-built API a GET request does not change data, but an API can misuse GET (the Petstore has `GET /user/logout`, for example), so check against staging first.
* Any OpenAPI 3.x or Swagger 2.0 document in YAML or JSON, including `$ref` across files and URLs. A Swagger 2.0 document is translated to OpenAPI 3 in memory, the base URL still comes from `--url`.

## What it does not do

* It never sends POST, PUT, PATCH or DELETE. It does not change data on a well-built API, but a GET request can be misused, so point it at staging first.
* It does not compare response bodies that are not JSON.
* It does not test business logic, performance or security, and it is not a mock server or a spec linter.
* It cannot check a spec on its own: a running API is required.

## Install and first run

Python 3.9 or newer. The demo API ships with the repository.

```
pip install specsentinel
git clone https://github.com/b6bs62fhys-jpg/specsentinel && cd specsentinel
python examples/demo_server.py &
specsentinel examples/petstore.yaml --url http://127.0.0.1:8099
```

The demo drifts on purpose. Real output:

```
SpecSentinel 0.3.0
Spec:   examples/petstore.yaml
Target: http://127.0.0.1:8099

GET /health            200  OK
GET /pets              200  OK
GET /pets/{petId}      200  DRIFT
    error   MISSING_FIELD            body.name
            required field is missing in the response
    error   TYPE_MISMATCH            body.id
            expected integer, got string
    warning UNDOCUMENTED_FIELD       body.breed
            field is returned but not described in the spec
GET /stats             503  DRIFT
    error   UNDOCUMENTED_STATUS      status
            status 503 is not documented (documented: 200)
GET /owners/{ownerId}  -    SKIPPED
    no example value for path parameter 'ownerId' (pass --param ownerId=VALUE)

4 checked, 2 with drift, 1 skipped, 0 failed
Result: DRIFT (exit code 1)
```

Start the demo with `--conform` and the same command ends with `Result: MATCH (exit code 0)`.

## New in 0.2.0

* More warnings for the values an API returns: string formats (`date-time`,
  `uuid`, `email`, `uri`), string lengths, numeric ranges and patterns, and
  required response headers that are missing.
* `--format json` now adds per severity `counts` and a flat `findings` list
  next to the per operation details.
* The GitHub Action takes a `version` input to install an exact SpecSentinel
  release instead of the latest one.

Note for `--strict` users: the new checks are warnings, so a run that used to
be green can turn red with `--strict`. Review the new findings before enabling
strict in an existing pipeline.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Every checked operation matches the spec |
| 1 | At least one operation drifts from the spec |
| 2 | The check could not be completed: bad spec, bad arguments, API unreachable, or nothing could be checked |

Code 2 is deliberately not 0. A pipeline should never turn green because nothing was actually checked.

## What counts as drift

| Finding | Severity | Meaning |
|---------|----------|---------|
| UNDOCUMENTED_STATUS | error | The API answered with a status code the spec does not list. Ranges like 4XX and `default` are honored. |
| MISSING_FIELD | error | A field marked required in the spec is not in the response. |
| TYPE_MISMATCH | error | A value has a different JSON type than the spec says. `nullable` and type lists are understood. |
| ENUM_MISMATCH | error | A value is not one of the enum values in the spec. |
| UNDOCUMENTED_CONTENT_TYPE | error | The response content type is not listed for that status. |
| INVALID_JSON | error | The spec promises JSON but the body is not valid JSON. |
| EMPTY_BODY | error | The spec documents a body but the response is empty. |
| NO_SCHEMA_MATCH | error | A value fits none of the oneOf or anyOf alternatives. |
| SERVER_ERROR | warning | The API answered 5xx and the spec only covers it through `default`. Allowed by the spec, but usually a sign the API is broken. `--strict` turns it into a failure. |
| UNDOCUMENTED_FIELD | warning | A field is returned that the spec does not describe. An error when the schema sets `additionalProperties: false`. |
| FORMAT_MISMATCH | warning | A string does not match its `format`: `date-time`, `uuid`, `email` or `uri`. |
| LENGTH_MISMATCH | warning | A string is shorter than `minLength` or longer than `maxLength`. |
| RANGE_MISMATCH | warning | A number is below `minimum` or above `maximum`. |
| PATTERN_MISMATCH | warning | A string does not match the `pattern` given in the spec. |
| MISSING_RESPONSE_HEADER | warning | The spec marks a response header as required but the response does not send it. |

Warnings do not fail the run. Add `--strict` and they do.

## Options

```
specsentinel SPEC --url BASE_URL [options]

  SPEC                   path or URL of the OpenAPI 3.x or Swagger 2.0 document, YAML or JSON
  --url BASE_URL         base URL of the running API
  -H, --header 'N: v'    header sent with every request, repeatable
  --param NAME=VALUE     value for a path or query parameter, repeatable
  --params-file FILE     YAML or JSON file with parameter values
  --include PATTERN      check only paths matching PATTERN, repeatable
  --exclude PATTERN      skip paths matching PATTERN, repeatable
  --baseline FILE        ignore findings recorded in FILE
  --write-baseline FILE  write all current findings to FILE
  --timeout SECONDS      wait per request, default 10
  --delay SECONDS        wait between requests, default 0
  --strict               treat warnings as drift
  --format text|json     output format, default text
  --version
```

Use `--format json` when another tool should read the result. The output is a
single JSON document with `exit_code`, a `summary` with the operation counts
and `counts` per severity (`error`/`warning`), a flat `findings` list (each
entry is `code`, `method`, `path` and `severity`) and one `operations` entry
per checked operation with its detailed findings. Header values are never
included in the output.

```json
{
  "version": "0.3.0",
  "spec": "examples/petstore.yaml",
  "target": "http://127.0.0.1:8099",
  "strict": false,
  "exit_code": 1,
  "summary": {
    "checked": 4,
    "drift": 1,
    "skipped": 1,
    "failed": 0,
    "counts": {"error": 1, "warning": 1},
    "baselined": 0
  },
  "findings": [
    {"code": "MISSING_FIELD", "method": "GET", "path": "/pets/{petId}", "severity": "error"},
    {"code": "UNDOCUMENTED_FIELD", "method": "GET", "path": "/pets/{petId}", "severity": "warning"}
  ],
  "fixed": [],
  "operations": [
    {
      "method": "GET",
      "path": "/pets/{petId}",
      "status": 200,
      "state": "DRIFT",
      "baselined": 0,
      "findings": [
        {"severity": "error", "code": "MISSING_FIELD", "location": "body.name", "message": "required field is missing in the response"},
        {"severity": "warning", "code": "UNDOCUMENTED_FIELD", "location": "body.extra", "message": "field is not documented in the spec"}
      ]
    }
  ]
}
```

## Adopt it in an existing project

An API that already drifts makes the first run red. Record what is there today as
a baseline, then only new drift fails:

```
specsentinel openapi.yaml --url https://staging.example.com --write-baseline baseline.json
specsentinel openapi.yaml --url https://staging.example.com --baseline baseline.json
```

The first command writes every current finding to `baseline.json` and exits 0:
recording the baseline is the goal, so a run that writes the file succeeds. The
second run ignores those findings: they are counted as `baselined` and no longer
affect the exit code. New findings behave as before, so an error still fails and
a warning still needs `--strict`.

A finding is matched by method, path, code and location, not by its message, so
editing a message does not invalidate the baseline. Baseline findings that no
longer occur are listed as `fixed`, which tells you what can be removed. Re-run
`--write-baseline` to refresh the file after fixing drift. In `--format json` the
number is `summary.baselined` and the fixed findings are in the `fixed` list.

## Choosing what to check

Not every operation is safe or useful to call. `--include` and `--exclude` take a path pattern with `*` as a wildcard, and both can be repeated:

```
specsentinel openapi.yaml --url https://staging.example.com --exclude /user/logout
specsentinel openapi.yaml --url https://staging.example.com --include '/pets*' --exclude '/pets/{petId}'
```

Without `--include` every operation is checked. With `--include` only the matching ones are, and `--exclude` takes paths out again. An excluded operation shows as SKIPPED with the reason `excluded`, does not change the exit code and appears in the JSON output. Use it for an operation such as `GET /user/logout` that is documented but has a side effect. Against staging or an API you do not own, combine `--exclude` with `--delay` to put a pause between requests.

## How requests are built

SpecSentinel sends GET requests only. Methods that change data could damage the API under test, so they are out of scope by design.

Parameter values come from the spec: `example`, `examples`, the schema `example`, `default`, or the first `enum` value. A path parameter without any of these cannot be filled in automatically. That operation is reported as SKIPPED with the exact `--param` to pass. Skipped operations do not fail the run.

### Params file

Large APIs have many operations with path parameters. Put the values in a file instead of a long command line:

```yaml
# params.yaml
petId: 1                 # used by every operation with a parameter called petId
ownerId: 7
GET /pets/{petId}:       # applies to this one operation only
  petId: 42
```

```
specsentinel openapi.yaml --url https://staging.example.com --params-file params.yaml
```

Order of precedence, later wins: spec example, params file, params file entry for one operation, `--param` on the command line.

For authentication pass the header yourself:

```
specsentinel openapi.yaml --url https://staging.example.com \
  --header "Authorization: Bearer $API_TOKEN"
```

## GitHub Actions

```yaml
name: API contract
on: [push, pull_request]

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: b6bs62fhys-jpg/specsentinel@v0.3.0
        with:
          spec: openapi.yaml
          url: https://staging.example.com
          header: "Authorization: Bearer ${{ secrets.API_TOKEN }}"
```

The action installs SpecSentinel from PyPI, runs it against your API and
passes its exit code through unchanged: 0 on match, 1 on drift, 2 if the
check could not be completed. When the API drifts, exit code 1 fails the
step and the build goes red.

Inputs: `spec` (path or URL) and `url` are required. Optional inputs are
`header` (sent with every request, passed through an environment variable and
not written to the log), `params_file`, `strict` (default `false`),
`python_version` (default `3.12`) and `version`. `version` pins the exact
SpecSentinel release that gets installed, for example `0.3.0`. When it is
empty, the latest release is installed.

## Tested against real specifications


The schema checks were run against the public OpenAPI descriptions of Swagger Petstore, GitHub and Stripe: 920 GET operations and 2032 documented JSON responses in total. For every response a conforming example was generated from its schema and fed through the checker. It produced no findings and no crashes.


You can repeat the run yourself with `python tools/spec_smoke.py <spec file or URL>`. The exact output is in `docs/smoke_results.md`.


The generator and the checker share the same reading of the schema, so this run shows that the checker raises no false alarms on large real specifications. It does not show that every kind of drift is caught, and it does not replace running SpecSentinel against your own live API.


## Found in the wild

On 2026-09-21 SpecSentinel 0.1.1 was run against the public Swagger Petstore. It reported one drift: `GET /user/login` is documented as JSON and answers with `Content-Type: application/json`, but the body is plain text. Three endpoints answered 500 and were reported as `SERVER_ERROR` warnings. The Petstore is a shared demo server, so results may differ. The full output is in `docs/live_petstore.txt`.

## Security

SpecSentinel follows `$ref` across files and URLs. A spec can make SpecSentinel read files from its own machine and fetch documents from any URL it can reach. Only check specs you trust: review a spec before running it, and only point the tool at specs from sources you control or rely on, just as you would with any code you choose to execute.

## Limits of this version

This is an early release. Known limits:

* GET operations only
* JSON response bodies only, other content types are not compared
* allOf is merged, oneOf and anyOf pass when any alternative fits

Feedback on which check should come next is very welcome. Open an issue.

## Development

```
pip install -e ".[dev]"
pytest
```

## License

MIT, see [LICENSE](LICENSE).
