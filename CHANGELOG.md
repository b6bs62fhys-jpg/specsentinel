# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `--write-baseline FILE` records every current finding as a JSON baseline.
  `--baseline FILE` accepts those findings, so only new drift fails. Findings
  are matched by method, path, code and location, not by message. Accepted
  findings are counted as `baselined` and no longer affect the exit code.
  Baseline entries that no longer occur are reported as `fixed`.

### Changed

- Fatal errors (missing spec, invalid YAML or JSON, no OpenAPI document,
  unreachable target, wrong base URL, timeout, missing path parameter) print a
  single clear line and exit with code 2 instead of a traceback.

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

### Fixed

- `date-time` values are validated with an RFC 3339 regular expression instead
  of `datetime.fromisoformat`, which rejected valid offsets and fractional
  seconds.

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

[Unreleased]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/b6bs62fhys-jpg/specsentinel/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/b6bs62fhys-jpg/specsentinel/releases/tag/v0.1.0
