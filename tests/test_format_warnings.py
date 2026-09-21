from specsentinel.checker import WARNING, validate_value

SPEC = {"openapi": "3.0.3"}


def codes(result):
    return sorted(f.code for f in result)


def _first(result, code):
    return next(f for f in result if f.code == code)


def test_valid_date_time_passes():
    schema = {"type": "string", "format": "date-time"}
    assert validate_value(SPEC, schema, "2020-01-01T00:00:00Z", "b") == []
    assert validate_value(SPEC, schema, "2020-01-01T12:30:45.123+02:00", "b") == []


def test_date_time_accepts_any_number_of_fractional_digits():
    schema = {"type": "string", "format": "date-time"}
    for value in (
        "2020-01-01T00:00:00.1Z",
        "2020-01-01T00:00:00.123Z",
        "2020-01-01T00:00:00.123456789Z",
    ):
        assert validate_value(SPEC, schema, value, "b") == []


def test_date_time_with_z_and_offset_passes():
    schema = {"type": "string", "format": "date-time"}
    assert validate_value(SPEC, schema, "2020-01-01T00:00:00Z", "b") == []
    assert validate_value(SPEC, schema, "2020-01-01T00:00:00+05:30", "b") == []
    assert validate_value(SPEC, schema, "2020-01-01T00:00:00.123-08:00", "b") == []


def test_date_time_without_timezone_passes():
    schema = {"type": "string", "format": "date-time"}
    assert validate_value(SPEC, schema, "2020-01-01T00:00:00", "b") == []
    assert validate_value(SPEC, schema, "2020-01-01T00:00:00.123", "b") == []


def test_date_time_rejects_month_out_of_range():
    schema = {"type": "string", "format": "date-time"}
    assert codes(validate_value(SPEC, schema, "2020-13-01T00:00:00Z", "b")) == ["FORMAT_MISMATCH"]


def test_date_time_rejects_missing_t_separator():
    schema = {"type": "string", "format": "date-time"}
    assert codes(validate_value(SPEC, schema, "2020-01-01 00:00:00Z", "b")) == ["FORMAT_MISMATCH"]


def test_invalid_date_time_is_a_warning():
    schema = {"type": "string", "format": "date-time"}
    result = validate_value(SPEC, schema, "tomorrow", "b")
    assert codes(result) == ["FORMAT_MISMATCH"]
    assert result[0].severity == WARNING


def test_valid_uuid_passes():
    schema = {"type": "string", "format": "uuid"}
    assert validate_value(SPEC, schema, "123e4567-e89b-12d3-a456-426614174000", "b") == []


def test_invalid_uuid_is_a_warning():
    result = validate_value(SPEC, {"type": "string", "format": "uuid"},
                            "not-a-uuid", "b")
    assert codes(result) == ["FORMAT_MISMATCH"]


def test_email_format():
    schema = {"type": "string", "format": "email"}
    assert validate_value(SPEC, schema, "a@example.com", "b") == []
    result = validate_value(SPEC, schema, "no-at-sign", "b")
    assert codes(result) == ["FORMAT_MISMATCH"]


def test_uri_format():
    schema = {"type": "string", "format": "uri"}
    assert validate_value(SPEC, schema, "https://example.com/x", "b") == []
    result = validate_value(SPEC, schema, "not a uri", "b")
    assert codes(result) == ["FORMAT_MISMATCH"]


def test_unknown_format_is_ignored():
    assert validate_value(SPEC, {"type": "string", "format": "byte"}, "anything", "b") == []


def test_min_length_and_max_length():
    schema = {"type": "string", "minLength": 3, "maxLength": 5}
    assert validate_value(SPEC, schema, "abc", "b") == []
    result = validate_value(SPEC, schema, "ab", "b")
    assert _first(result, "LENGTH_MISMATCH").location == "b"
    result = validate_value(SPEC, schema, "abcdef", "b")
    assert codes(result) == ["LENGTH_MISMATCH"]


def test_minimum_and_maximum():
    schema = {"type": "integer", "minimum": 1, "maximum": 4}
    assert validate_value(SPEC, schema, 3, "b") == []
    assert _first(validate_value(SPEC, schema, 0, "b"), "RANGE_MISMATCH").message.startswith("number 0 is below")
    assert codes(validate_value(SPEC, schema, 5, "b")) == ["RANGE_MISMATCH"]


def test_number_range_applies_to_floats_too():
    schema = {"type": "number", "maximum": 2.5}
    assert validate_value(SPEC, schema, 2.4, "b") == []
    assert codes(validate_value(SPEC, schema, 2.6, "b")) == ["RANGE_MISMATCH"]


def test_pattern_matches_and_does_not():
    schema = {"type": "string", "pattern": r"^\d{4}-[A-Z]{2}$"}
    assert validate_value(SPEC, schema, "1234-AB", "b") == []
    result = validate_value(SPEC, schema, "nope", "b")
    assert codes(result) == ["PATTERN_MISMATCH"]


def test_invalid_pattern_in_spec_is_ignored():
    assert validate_value(SPEC, {"type": "string", "pattern": "["}, "x", "b") == []


def test_warnings_only_fail_with_strict(capsys, tmp_path, start_server):
    from specsentinel.cli import main

    spec = tmp_path / "spec.yaml"
    spec.write_text(
        "openapi: 3.0.3\n"
        "paths:\n"
        "  /pets:\n"
        "    get:\n"
        "      responses:\n"
        "        '200':\n"
        "          description: ok\n"
        "          content:\n"
        "            application/json:\n"
        "              schema:\n"
        "                type: array\n"
        "                items:\n"
        "                  type: object\n"
        "                  required: [id]\n"
        "                  properties:\n"
        "                    id:\n"
        "                      type: integer\n"
        "                      minimum: 100\n"
    )
    url = start_server(drift=False)  # demo returns id 1
    code = main([str(spec), "--url", url])
    assert code == 0 and "RANGE_MISMATCH" in capsys.readouterr().out
    code = main([str(spec), "--url", url, "--strict"])
    assert code == 1 and "RANGE_MISMATCH" in capsys.readouterr().out