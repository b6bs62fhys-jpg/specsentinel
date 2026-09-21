from specsentinel.checker import check_response

SPEC = {}


def _operation(headers=None, media="application/json"):
    response = {"description": "ok", "content": {media: {"schema": {"type": "object"}}}}
    if headers is not None:
        response["headers"] = headers
    return {"responses": {"200": response}}


def pairs(result):
    return [(f.severity, f.code) for f in result]


def test_missing_required_response_header_is_a_warning():
    op = _operation(headers={"X-Rate-Limit": {"required": True, "schema": {"type": "integer"}}})
    result = check_response(SPEC, op, 200, {"Content-Type": "application/json"}, b"{}")
    assert pairs(result) == [("warning", "MISSING_RESPONSE_HEADER")]
    assert result[0].location == "header.X-Rate-Limit"


def test_present_required_response_header_passes():
    op = _operation(headers={"X-Rate-Limit": {"required": True, "schema": {"type": "integer"}}})
    result = check_response(SPEC, op, 200,
                            {"Content-Type": "application/json", "X-Rate-Limit": "10"}, b"{}")
    assert result == []


def test_header_name_match_ignores_case():
    op = _operation(headers={"X-Rate-Limit": {"required": True}})
    result = check_response(SPEC, op, 200,
                            {"Content-Type": "application/json", "x-rate-limit": "10"}, b"{}")
    assert result == []


def test_optional_response_header_is_not_required():
    op = _operation(headers={"X-Trace": {"required": False, "schema": {"type": "string"}}})
    result = check_response(SPEC, op, 200, {"Content-Type": "application/json"}, b"{}")
    assert result == []


def test_header_without_required_flag_is_not_reported():
    op = _operation(headers={"X-Trace": {"schema": {"type": "string"}}})
    result = check_response(SPEC, op, 200, {"Content-Type": "application/json"}, b"{}")
    assert result == []


def test_required_header_is_checked_for_non_json_bodies():
    op = _operation(headers={"X-Rate-Limit": {"required": True}}, media="text/plain")
    result = check_response(SPEC, op, 200, {"Content-Type": "text/plain"}, b"hello")
    assert pairs(result) == [("warning", "MISSING_RESPONSE_HEADER")]


def test_header_and_body_findings_are_reported_together():
    op = _operation(headers={"X-Rate-Limit": {"required": True}})
    op["responses"]["200"]["content"]["application/json"]["schema"] = {
        "type": "object", "required": ["id"]}
    result = check_response(SPEC, op, 200, {"Content-Type": "application/json"}, b"{}")
    assert pairs(result) == [("warning", "MISSING_RESPONSE_HEADER"),
                             ("error", "MISSING_FIELD")]


def test_required_header_in_a_referenced_header_object():
    spec = {"components": {"headers": {"Rate": {"required": True, "schema": {"type": "integer"}}}}}
    op = _operation(headers={"X-Rate-Limit": {"$ref": "#/components/headers/Rate"}})
    result = check_response(spec, op, 200, {"Content-Type": "application/json"}, b"{}")
    assert pairs(result) == [("warning", "MISSING_RESPONSE_HEADER")]