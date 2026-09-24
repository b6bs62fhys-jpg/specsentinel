import json

from specsentinel.checker import (
    check_response, match_response, pick_media_type, validate_value,
)

SPEC = {"openapi": "3.0.3", "components": {"schemas": {
    "Base": {"type": "object", "required": ["id"], "properties": {"id": {"type": "integer"}}},
    "Named": {"allOf": [
        {"$ref": "#/components/schemas/Base"},
        {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
    ]},
}}}


def codes(findings):
    return sorted(f.code for f in findings)


def test_matching_value_has_no_findings():
    schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}
    assert validate_value(SPEC, schema, {"a": "x"}, "body") == []


def test_missing_required_field():
    schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}
    result = validate_value(SPEC, schema, {}, "body")
    assert codes(result) == ["MISSING_FIELD"]
    assert result[0].location == "body.a"


def test_missing_optional_field_is_fine():
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    assert validate_value(SPEC, schema, {}, "body") == []


def test_wrong_type():
    schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
    result = validate_value(SPEC, schema, {"n": "5"}, "body")
    assert codes(result) == ["TYPE_MISMATCH"]
    assert "expected integer, got string" in result[0].message


def test_bool_is_not_an_integer():
    schema = {"type": "integer"}
    assert codes(validate_value(SPEC, schema, True, "body")) == ["TYPE_MISMATCH"]


def test_integer_accepted_as_number_and_whole_float_as_integer():
    assert validate_value(SPEC, {"type": "number"}, 3, "b") == []
    assert validate_value(SPEC, {"type": "integer"}, 3.0, "b") == []
    assert codes(validate_value(SPEC, {"type": "integer"}, 3.5, "b")) == ["TYPE_MISMATCH"]


def test_null_only_allowed_when_nullable():
    assert codes(validate_value(SPEC, {"type": "string"}, None, "b")) == ["TYPE_MISMATCH"]
    assert validate_value(SPEC, {"type": "string", "nullable": True}, None, "b") == []
    assert validate_value(SPEC, {"type": ["string", "null"]}, None, "b") == []


def test_undocumented_field_is_warning_by_default():
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    result = validate_value(SPEC, schema, {"a": "x", "extra": 1}, "body")
    assert [(f.code, f.severity) for f in result] == [("UNDOCUMENTED_FIELD", "warning")]


def test_undocumented_field_is_error_when_additional_properties_false():
    schema = {"type": "object", "properties": {"a": {"type": "string"}},
              "additionalProperties": False}
    result = validate_value(SPEC, schema, {"a": "x", "extra": 1}, "body")
    assert [(f.code, f.severity) for f in result] == [("UNDOCUMENTED_FIELD", "error")]


def test_free_form_object_is_not_reported():
    assert validate_value(SPEC, {"type": "object"}, {"anything": 1}, "body") == []


def test_enum():
    schema = {"type": "string", "enum": ["a", "b"]}
    assert validate_value(SPEC, schema, "a", "b") == []
    assert codes(validate_value(SPEC, schema, "c", "b")) == ["ENUM_MISMATCH"]


def test_array_items_are_checked_with_short_path():
    schema = {"type": "array", "items": {"type": "object", "required": ["id"],
                                         "properties": {"id": {"type": "integer"}}}}
    result = validate_value(SPEC, schema, [{"id": 1}, {}], "body")
    assert codes(result) == ["MISSING_FIELD"]
    assert result[0].location == "body[].id"


def test_all_of_merges_properties_without_false_warnings():
    ref = {"$ref": "#/components/schemas/Named"}
    assert validate_value(SPEC, ref, {"id": 1, "name": "x"}, "body") == []
    assert codes(validate_value(SPEC, ref, {"id": 1}, "body")) == ["MISSING_FIELD"]


def test_one_of_accepts_any_matching_alternative():
    schema = {"oneOf": [{"type": "string"}, {"type": "integer"}]}
    assert validate_value(SPEC, schema, "x", "b") == []
    assert validate_value(SPEC, schema, 4, "b") == []
    assert "NO_SCHEMA_MATCH" in codes(validate_value(SPEC, schema, [1], "b"))


def test_match_response_exact_range_and_default():
    responses = {"200": 1, "4XX": 2, "default": 3}
    assert match_response(responses, 200) == 1
    assert match_response(responses, 404) == 2
    assert match_response(responses, 500) == 3
    assert match_response({"200": 1}, 500) is None


def test_yaml_style_integer_status_keys_work():
    assert match_response({200: "ok"}, 200) == "ok"


def test_pick_media_type():
    content = {"application/json": {}}
    assert pick_media_type(content, "application/json; charset=utf-8") == "application/json"
    assert pick_media_type(content, "text/html") is None
    assert pick_media_type({"*/*": {}}, "text/html") == "*/*"


def _operation(schema=None, status="200", content_type="application/json"):
    content = {content_type: {"schema": schema}} if schema else {}
    return {"responses": {status: {"description": "x", "content": content}}}


def test_undocumented_status_lists_documented_ones():
    result = check_response(SPEC, _operation({"type": "object"}), 409, {}, b"{}")
    assert codes(result) == ["UNDOCUMENTED_STATUS"]
    assert "documented: 200" in result[0].message


def test_undocumented_status_points_at_the_spec_response():
    result = check_response(SPEC, _operation({"type": "object"}), 409, {}, b"{}",
                            spec_path="paths./pets.get")
    assert codes(result) == ["UNDOCUMENTED_STATUS"]
    assert "in paths./pets.get.responses" in result[0].message


def test_undocumented_content_type():
    result = check_response(SPEC, _operation({"type": "object"}), 200,
                            {"Content-Type": "text/html"}, b"<html>")
    assert codes(result) == ["UNDOCUMENTED_CONTENT_TYPE"]


def test_invalid_json_body():
    result = check_response(SPEC, _operation({"type": "object"}), 200,
                            {"content-type": "application/json"}, b"not json")
    assert codes(result) == ["INVALID_JSON"]


def test_empty_body_when_body_is_documented():
    result = check_response(SPEC, _operation({"type": "object"}), 200, {}, b"")
    assert codes(result) == ["EMPTY_BODY"]


def test_response_without_documented_body_passes():
    op = {"responses": {"204": {"description": "no content"}}}
    assert check_response(SPEC, op, 204, {}, b"") == []


def test_full_matching_response():
    schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
    body = json.dumps({"a": 1}).encode()
    assert check_response(SPEC, _operation(schema), 200,
                          {"Content-Type": "application/json"}, body) == []


def test_server_error_only_covered_by_default_is_a_warning():
    op = {"responses": {"200": {"description": "ok"}, "default": {"description": "e"}}}
    found = check_response({}, op, 500, {}, b"")
    assert [(f.severity, f.code) for f in found] == [("warning", "SERVER_ERROR")]


def test_documented_server_error_is_not_reported():
    op = {"responses": {"200": {"description": "ok"}, "503": {"description": "d"}}}
    assert check_response({}, op, 503, {}, b"") == []
    assert check_response({}, {"responses": {"5XX": {"description": "e"}}}, 500, {}, b"") == []
