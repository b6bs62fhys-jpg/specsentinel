# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `examples/` has three runnable example scripts with a README: a simple
  run, adopting SpecSentinel with a baseline, and a Swagger 2.0 source. A
  test runs all three.

- The GitHub Action writes a job summary (result, counts, operations with
  drift, full report) and one annotation per drifting operation. The new
  `summary` input (default `true`) turns this off. The exit code is passed
  through unchanged, and report lines can no longer be read as workflow
  commands. Works with every pinned SpecSentinel version, because it reads
  the text report.

### Fixed

- The README now opens with what SpecSentinel does, for whom, and an excerpt
  of a real run. The "Real output" block was out of date (it predated the
  `(in ...)` locations and the skipped notice of 0.3.0) and is replaced with
  the current output; a test compares both with a real run.
- Errors in the params file and the baseline file now always name the file
  and the place inside it, in the same `(in ...)` style as spec errors, for
  example `(in findings[1].code)`. A params or baseline file that cannot be
  read (no permission, not UTF-8) now ends with exit code 2 and a clear
  message instead of a traceback. The exit codes and the JSON format are
  unchanged.

### Changed

- CI now also runs the tests and the type check on Python 3.13 and 3.14.
  The classifiers list the versions that have passed CI; 3.13 and 3.14 are
  added there once their CI runs are green. `requires-python` is unchanged.

## [0.3.0] - 2026-09-24

### Added

- `--write-baseline FILE` records every current finding as a JSON baseline.
  `--baseline FILE` accepts those findings, so only new drift fails. Findings
  are matched by method, path, code and location, not by message. Accepted
  findings are counted as `baselined` and no longer affect the exit code.
  Baseline entries that no longer occur are reported as `fixed`. A run that
  writes the baseline exits 0 once the file is written.
- `--include PATTERN` and `--exclude PATTERN` select which paths are checked.
  Both take a path pattern with `*` as a wildcard and can be repeated. An
  excluded operation is reported as SKIPPED with the reason `excluded`, does
  not change the exit code and appears in the JSON output.
- `--delay SECONDS` waits between two requests, default 0.
- Swagger 2.0 documents are translated to OpenAPI 3 in memory, so paths,
  path/query/header parameters, responses, `definitions` and top level
  `responses` can be checked. Each response media type gets its own entry in
  `content`, and `x-nullable: true` becomes `nullable: true`. The base URL
  still comes from `--url`. An operation that cannot be translated (for
  example `type: file` or a body parameter) is reported as SKIPPED with a
  clear reason instead of stopping the run.
- The OpenAPI version of the checked spec is now validated and reported.
  `openapi` must be `3.x`; the reported version is available as
  `openapi_version` in the JSON output (for Swagger 2.0 sources it reads
  `swagger 2.0`).
- `const` and `exclusiveMinimum`/`exclusiveMaximum` are now checked. `const`
  mismatches are reported as `CONST_MISMATCH`; numeric exclusive boundaries
  (OpenAPI 3.1) and boolean modifiers on `minimum`/`maximum` (OpenAPI 3.0) as
  `RANGE_MISMATCH`.
- The `date` and `byte` string formats are now validated. `date` must be a
  full date (RFC 3339), `byte` a base64 encoded string; violations are
  reported as `FORMAT_MISMATCH`.
- `--spec-max-bytes BYTES` and `--spec-timeout SECONDS` make the download of
  remote specs and referenced documents configurable. The default limit is
  50 MiB and the default timeout 20 seconds.

### Changed

- Fatal errors (missing spec, invalid YAML or JSON, no OpenAPI document,
  unreachable target, wrong base URL, timeout, missing path parameter) print a
  single clear line and exit with code 2 instead of a traceback. With
  `--format json` the failure is also written to stdout as a JSON object.

## [0.2.0] - 2026-09-21

### Added

- Warnings for the values an API returns: `FORMAT_MISMATCH` for `date-time`,
  `uuid`, `email` and `uri`, `LENGTH_MISMATCH` for `minLength`/`maxLength`,
  `RANGE_MISMATCH` for `minimum`/`maximum`, `PATTERN_MISMATCH` for `pattern`,
  and `MISSING_RESPONSE_HEADER` for required response headers.
- `--format json` output now includes per severity `counts` and a flat
  `findings` list next to the per operation details.
- The GitHub Action accepts a `version` input to install an exact SpecSentinel
  release instead of the latest one.

## [0.1.2] - 2026-09-21

### Added

- `$ref` is resolved across files and URLs, relative to the spec, instead of
  being limited to the same document.
- A composite GitHub Action that installs SpecSentinel, runs it against the
  API and passes its exit code through unchanged.
- A live Petstore example.

### Security

- Documented that following `$ref` lets a spec read local files and fetch
  remote URLs, so only trusted specs should be checked.

## [0.1.1] - 2026-09-21

### Added

- `SERVER_ERROR` warning when a 5xx response is only covered by the spec's
  `default` response. `--strict` turns it into a failure.

## [0.1.0] - 2026-09-21

### Added

- First release. Calls the GET operations of a running API and compares each
  response with an OpenAPI 3.x document (YAML or JSON).
- Findings: `MISSING_FIELD`, `TYPE_MISMATCH`, `ENUM_MISMATCH`,
  `UNDOCUMENTED_STATUS`, `UNDOCUMENTED_CONTENT_TYPE`, `INVALID_JSON`,
  `EMPTY_BODY`, `NO_SCHEMA_MATCH` and `UNDOCUMENTED_FIELD`.
- Exit codes: 0 for a match, 1 for drift, 2 if the check could not run.
  `--strict` treats warnings as drift.
- Options `--header`, `--param`, `--params-file`, `--timeout` and
  `--format text|json`.
- A demo server, an example spec, a test suite and a CI workflow.

[Unreleased]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/b6bs62fhys-jpg/specsentinel/releases/tag/v0.1.0
