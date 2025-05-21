import pytest
import uuid

# tests/conftest.py
import sys, pathlib

# Ensure project root (parent of this file) is on sys.path
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

@pytest.fixture(scope="session")
def customer_id():
    # Any UUID – parser just passes it through
    return str(uuid.uuid4())

@pytest.fixture
def merchant_sample():
    return """
    Merchant Billing Statement
    Gross Sales            $10,000.00
    Total Fees             $   240.00
    Net Payout             $ 9,760.00
    Statement Period       01/01/2025 - 01/31/2025
    """

@pytest.fixture
def bank_sample():
    return """
    Beginning Balance      $   294.30
    Total Deposits         $     0.00
    Total Withdrawals      $    55.20
    Ending Balance         $   239.10
    """