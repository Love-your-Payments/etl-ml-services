"""
ai_underwriter.extractor
========================
Ultra-lean text extraction & parsing (merchant + bank).
"""

from __future__ import annotations
import re
from typing import Dict, Tuple

__all__ = ["text_from_file", "parse_merchant", "parse_bank"]

# ───────────────────────────────────────────────────────────────
# Helper regex bits
# ───────────────────────────────────────────────────────────────
_SPACES = r"\s*"                     # any whitespace (incl. newlines)
_MONEY  = r"([\d,.]+\d)"             # 12,345.67
def _grab(label: str, text: str) -> str | None:
    r"""Return the first \$amount that follows *label* (case-insensitive)."""
    pat = rf"{label}{_SPACES}\$?{_SPACES}{_MONEY}"
    m = re.search(pat, text, re.I)
    return m.group(1).replace(",", "") if m else None

def _num(s: str | None) -> float | None:
    try: return float(s) if s else None
    except ValueError: return None

# ───────────────────────────────────────────────────────────────
# Text extraction (lazy imports)
# ───────────────────────────────────────────────────────────────
def text_from_file(path: str) -> str:
    """PDF → text via PyMuPDF; fallback OCR via EasyOCR."""
    try:
        import fitz  # type: ignore
        with fitz.open(path) as doc:
            txt = "\n".join(p.get_text() for p in doc)
            if txt.strip(): return txt
    except Exception:
        pass
    try:
        import easyocr  # type: ignore
    except ModuleNotFoundError:
        raise RuntimeError("Neither PyMuPDF nor EasyOCR available.")
    reader = easyocr.Reader(["en"], gpu=False)
    return "\n".join(reader.readtext(path, detail=0))

# ───────────────────────────────────────────────────────────────
# Merchant parser
# ───────────────────────────────────────────────────────────────
def parse_merchant(text: str, cid: str) -> Tuple[Dict[str, list[dict]], float]:
    gross = _grab(r"gross\s+sales", text)
    fees  = _grab(r"total\s+fees?", text)
    net   = _grab(r"net\s+(?:deposit|payout)", text)

    row = dict(
        customer_id=cid,
        gross_sales=_num(gross),
        total_fees=_num(fees),
        net_payout=_num(net),
    )
    conf = sum(v is not None for v in (gross, fees, net)) / 3
    row["needs_review"] = conf < 0.70
    if row["needs_review"]:
        row["extracted_json"] = {"raw": text}
    return {"merchant_statements": [row]}, conf

# ───────────────────────────────────────────────────────────────
# Bank parser
# ───────────────────────────────────────────────────────────────
def parse_bank(text: str, cid: str) -> Tuple[Dict[str, list[dict]], float]:
    beg = _grab(r"beginning\s+balance", text)
    end = _grab(r"ending\s+balance", text)
    dep = _grab(r"total\s+deposits?", text)
    wdr = _grab(r"total\s+withdrawals?", text)

    row = dict(
        customer_id=cid,
        beginning_balance=_num(beg),
        ending_balance=_num(end),
        total_deposits=_num(dep),
        total_withdrawals=_num(wdr),
    )
    conf = sum(v is not None for v in (beg, end, dep, wdr)) / 4
    row["needs_review"] = conf < 0.70
    if row["needs_review"]:
        row["extracted_json"] = {"raw": text}
    return {"bank_statements": [row]}, conf