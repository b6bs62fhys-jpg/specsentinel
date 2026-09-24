# SpecSentinel in GitHub Actions

Two ways to run SpecSentinel in a workflow:

1. **The action** (`uses: b6bs62fhys-jpg/specsentinel@v0.3.0`) for the common
   case: spec, URL, an optional header, a params file and `--strict`.
2. **The CLI in a `run` step** when you need options the action does not have
   as inputs. As of `v0.3.0` the action has no inputs for, among others,
   `--baseline`, `--include`, `--exclude`, `--param`, `--timeout` and
   `--delay`.

Both pass SpecSentinel's exit code through unchanged: 0 match, 1 drift, 2 the
check could not be completed. Exit code 1 or 2 fails the step.

## Pin two versions

A reproducible check pins both:

* **The action itself**, with a release tag (`@v0.3.0`) or, stricter, with
  the full commit SHA of that tag. A tag can be moved; a SHA cannot. Never
  use a branch such as `@main`.
* **The SpecSentinel package the action installs**, with the `version`
  input. Without it the action installs the newest release from PyPI, and a
  new release with new checks can turn a green build red without any change
  on your side.

## Example 1: the action

```yaml
name: API drift
on:
  pull_request:
  schedule:
    - cron: "0 6 * * 1-5"

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: b6bs62fhys-jpg/specsentinel@v0.3.0
        with:
          version: "0.3.0"
          spec: openapi.yaml
          url: https://staging.example.com
          header: "Authorization: Bearer ${{ secrets.API_TOKEN }}"
          params_file: specsentinel-params.yaml
          strict: "false"
```

`header` is passed through an environment variable and not written to the
log. A `summary` input (job summary and one annotation per drifting
operation) is prepared for the next action release; it is not part of the
`v0.3.0` tag, so it is not used here.

## Example 2: baseline and path filters with the CLI

Use this form for an API that already drifts today (baseline) or when only
part of the API should be checked (`--include`, `--exclude`).

```yaml
name: API drift
on:
  pull_request:

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - name: Install SpecSentinel (pinned)
        run: python -m pip install "specsentinel==0.3.0"
      - name: Check API against spec
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
        run: |
          specsentinel openapi.yaml \
            --url https://staging.example.com \
            --header "Authorization: Bearer $API_TOKEN" \
            --baseline specsentinel-baseline.json \
            --include "/v1/*" \
            --exclude "/v1/internal/*"
```

`--include` and `--exclude` take a path pattern with `*` as wildcard and can
be repeated. Excluded operations are reported as SKIPPED with the reason
`excluded` and do not change the exit code.

### Creating and updating the baseline

Record today's findings once, locally or in a manual workflow run, and commit
the file:

```
specsentinel openapi.yaml --url https://staging.example.com \
  --write-baseline specsentinel-baseline.json
```

With `--baseline`, findings in the file are counted as `baselined` and no
longer fail the build; only new drift does. Findings that no longer occur are
reported as `fixed`, a signal to write the baseline again and shrink it.
Findings are matched by method, path, code and location, not by message text.

## What to check before relying on it

* Point the check at staging, not production. SpecSentinel sends only GET
  requests, but an API can misuse GET.
* A run that could not be completed (exit code 2: API unreachable, spec
  unreadable, nothing checked) also fails the step. That is on purpose: a
  check that did not run must not look green.
