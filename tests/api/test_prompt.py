from app.prompt import process_messages


def test_rut_masked_in_user_message() -> None:
    pr = process_messages(
        [{"role": "user", "content": "Ver RUT 12.345.678-9 por favor"}],
        max_chars=1000,
        intent_header=None,
    )
    assert pr.pii_masked
    assert "[RUT]" in pr.messages[0]["content"]
    assert "12.345.678" not in pr.messages[0]["content"]


def test_intent_tag() -> None:
    pr = process_messages(
        [{"role": "user", "content": "hola"}],
        max_chars=1000,
        intent_header="administrative",
    )
    assert pr.tags.get("intent") == "administrative"


def test_truncation() -> None:
    long_text = "x" * 5000
    pr = process_messages(
        [{"role": "user", "content": long_text}],
        max_chars=100,
        intent_header=None,
    )
    assert pr.truncated
    total = sum(
        len(m["content"]) for m in pr.messages if isinstance(m.get("content"), str)
    )
    assert total <= 100
