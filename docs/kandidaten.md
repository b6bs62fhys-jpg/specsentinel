# Candidate public APIs for testing SpecSentinel

Public APIs that ship a machine-readable OpenAPI/Swagger description and are
explicitly meant for testing or practising. They are useful for manually
exercising SpecSentinel against a spec that is not part of this repository.

SpecSentinel never calls these APIs automatically. Nothing in the test suite,
the smoke script or CI touches them. Every link below was checked by reading it
on 2026-09-21; no request was made against any of the APIs.

Only APIs where the spec, the terms and the GET status could all be confirmed
are listed. Candidates that failed one of those checks are recorded further
down so the search does not have to be repeated.

## Listed candidates

### Swagger Petstore (OpenAPI 3)

- Spec: <https://petstore3.swagger.io/api/v3/openapi.json> (OpenAPI 3.0.4)
- Terms: <https://swagger.io/terms/> (declared as `termsOfService` in the spec)
- GET requests free: yes. Public demo instance; some operations declare
  `api_key`/`oauth2` security but the read operations are reachable without a key.
- Why: the canonical sample API used to demonstrate OpenAPI tooling.

### httpbin

- Spec: <https://httpbin.org/spec.json> (Swagger 2.0)
- Terms: <https://github.com/postmanlabs/httpbin/blob/master/LICENSE> (ISC)
- GET requests free: yes, no authentication.
- Why: a service built specifically to test HTTP clients and request/response
  handling. Note that the published description is Swagger 2.0, not OpenAPI 3.x.

### ReqRes

- Spec: <https://reqres.in/openapi.json> (OpenAPI 3.0.3)
- Terms: <https://reqres.in/commercial> (MIT for the spec; a commercial licence
  is required for company use)
- GET requests free: partly. `/agent/v1/*` works without authentication
  (rate-limited per IP); the `/api/*` endpoints require a free `x-api-key`.
- Why: "The reliable test API" - designed for testing, with a sandbox aimed at
  automated tooling.

## Checked but not listed

These are public APIs that are clearly meant for testing, but that failed at
least one of the required checks. They are not listed as candidates above.

- **FakeRESTApi** - live OpenAPI 3.0.1 spec at
  <https://fakerestapi.azurewebsites.net/swagger/v1/swagger.json>, GET is free,
  and it is explicitly "for testing your application". No terms or licence are
  published: the source repository has a README only, no LICENSE file.
- **FakeStoreAPI** - free and MIT-licensed, described as suitable for "sample
  codes, tests". No machine-readable spec could be found: `/openapi.json` and
  `/docs/swagger.json` both return 404 and the repository `public/` directory
  contains only assets.
- **DummyJSON** - free fake REST API for testing. The documentation is HTML
  only; `/openapi.json` returns 404 and no OpenAPI description is published.
- **JSONPlaceholder** - free fake REST API for testing. No official OpenAPI
  description was found.
- **Postman Echo** - explicitly a testing service. No official OpenAPI
  description is published, only community gists.
- **restful-booker** - "A free to use Web API for practising API testing on",
  GET is free. The deployed documentation at
  <https://restful-booker.herokuapp.com/apidoc/index.html> is generated with
  apiDoc, not OpenAPI; `swagger.json` returns 404, so there is no OpenAPI spec
  to point at.
