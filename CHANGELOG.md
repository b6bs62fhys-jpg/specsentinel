# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
- Path and query parameters without a value over `--param` or the params file
  fall back to the spec: the parameter `example`, the `examples` map, the
  schema `example`, the schema `default`, or the first `enum` value. Only an
  operation with none of these is skipped.
- `--format junit` prints the report as JUnit XML, one testcase per operation:
  drift and failed requests are a `failure` (code and location in the text),
  skipped operations are `skipped` with the reason, warnings are collected in
  `system-out`, and the exit code is unchanged. Header values never appear in
  the XML.
- The GitHub Action writes a short summary to `$GITHUB_STEP_SUMMARY` after
  every run: the result, the `checked`/`drift`/`skipped`/`baselined` counts
  and the first 20 findings (code, method and path). The step result and exit
  code are unchanged.

## [0.3.0] - 2026-09-21

### Added

- `--write-baseline FILE` records every current finding as a JSON baseline.
  `--baseline FILE` accepts those findings, so only new drift fails. Findings
  are matched by method, path, code and location, not by message. Accepted
  findings are counted as `baselined` and no longer affect the exit code.
  Baseline entries that no longer occur are reported as `fixed`. A run that
  writes the baseline exits 0 once the file is written.

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
