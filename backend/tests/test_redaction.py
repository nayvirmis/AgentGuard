from backend.app.security.redaction import redact_data, redact_text


def test_redacts_secrets_and_sensitive_keys():
    redacted, matches = redact_data(
        {
            "authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
            "note": "password=secret123 and call +1 (555) 123-4567",
        }
    )
    assert "abcdefghijklmnopqrstuvwxyz" not in str(redacted)
    assert "secret123" not in str(redacted)
    assert "555" not in str(redacted)
    assert matches


def test_redacts_configured_private_identifier():
    redacted, matches = redact_text("Student ID AG-4242", ["AG-4242"])
    assert "AG-4242" not in redacted
    assert "private_identifier" in matches
