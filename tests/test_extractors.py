# tests/test_extractors.py
from ai_underwriter.extractor import parse_merchant, parse_bank

# ---------- Merchant ---------------------------------------------------------
def test_parse_merchant_success(merchant_sample, customer_id):
    rows, conf = parse_merchant(merchant_sample, customer_id)

    # confidence should be 1.0 because all 3 core fields were found
    assert conf == 1.0

    stmt = rows["merchant_statements"][0]
    assert stmt["gross_sales"] == 10000.00
    assert stmt["total_fees"]  == 240.00
    assert stmt["net_payout"]  == 9760.00
    assert stmt["needs_review"] is False
    assert stmt["customer_id"] == customer_id

def test_parse_merchant_low_confidence(customer_id):
    # missing gross / fee lines
    snippet = "Net Payout $99.99"
    rows, conf = parse_merchant(snippet, customer_id)

    assert conf < 0.7
    stmt = rows["merchant_statements"][0]
    # ensure graceful degradation
    assert "extracted_json" in stmt and "raw" in stmt["extracted_json"]
    assert stmt["needs_review"] is True

# ---------- Bank -------------------------------------------------------------
def test_parse_bank_success(bank_sample, customer_id):
    rows, conf = parse_bank(bank_sample, customer_id)

    assert conf == 1.0
    stmt = rows["bank_statements"][0]
    assert stmt["beginning_balance"] == 294.30
    assert stmt["total_withdrawals"] == 55.20
    assert stmt["ending_balance"]    == 239.10
    assert stmt["needs_review"] is False