from sim.sample_payloads import SAMPLE_DOORDASH_ORDER, SAMPLE_UBEREATS_ORDER
from tournant.escpos import extract_text


def test_extract_text_strips_control_codes_and_keeps_order_lines():
    text = extract_text(SAMPLE_UBEREATS_ORDER)
    assert "UBER EATS" in text
    assert "Order #A1B2C3" in text
    assert "Cheeseburger" in text
    assert "\x1b" not in text
    assert "\x1d" not in text


def test_extract_text_doordash_sample():
    text = extract_text(SAMPLE_DOORDASH_ORDER)
    assert "DOORDASH" in text
    assert "Veggie Bowl" in text


def test_extract_text_handles_empty_and_unknown_bytes_without_raising():
    assert extract_text(b"") == ""
    assert extract_text(b"\x1b\x99\x1d\xffhello\n") != ""
