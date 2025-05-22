"""
ai_underwriter/main.py

Non-streaming ingest endpoint with debug prints.
Fixed download logic for Supabase storage.
"""

from __future__ import annotations
import os
import uuid
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, Path
from supabase import create_client

from ai_underwriter.extractor import text_from_file, parse_merchant, parse_bank

load_dotenv()

SB_URL = os.getenv("SUPABASE_URL")
SB_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SB_URL or not SB_KEY:
    raise RuntimeError("Need SUPABASE_URL and SUPABASE_SERVICE_KEY in env")

SB = create_client(SB_URL, SB_KEY)
app = FastAPI(title="AI-Underwriter Ingest (debug)")

BANK_KEYWORDS     = ("ENDING BALANCE", "BEGINNING BALANCE", "WITHDRAWALS", "DEPOSITS", "ACH")
MERCHANT_KEYWORDS = ("GROSS SALES", "TOTAL FEES", "NET PAYOUT", "BILLING STATEMENT", "DISCOUNT")

def classify(text: str) -> str:
    up = text.upper()
    bank_hits     = sum(k in up for k in BANK_KEYWORDS)
    merchant_hits = sum(k in up for k in MERCHANT_KEYWORDS)
    result = "bank" if bank_hits > merchant_hits else "merchant"
    print(f"[DEBUG] classify → bank_hits={bank_hits}, merchant_hits={merchant_hits} → {result}")
    return result

@app.get("/ingest/{customer_id}")
async def ingest(customer_id: uuid.UUID = Path(...)):
    cid = str(customer_id)
    bucket = SB.storage.from_("statements")

    # 1. List objects
    prefix = f"{cid}/"
    print(f"[DEBUG] listing objects at bucket=statements prefix={prefix}")
    objects = bucket.list(prefix)
    names = [o["name"] for o in objects]
    print(f"[DEBUG] found {len(objects)} objects: {names}")

    results: list[dict] = []
    for obj in objects:
        name = obj["name"]
        key  = f"{cid}/{name}"
        print(f"[DEBUG] downloading key={key}")

        # --- fixed download step ---
        local_path = tempfile.mktemp()
        data = bucket.download(key)           # returns bytes
        with open(local_path, "wb") as f:
            f.write(data)
        print(f"[DEBUG] wrote {len(data)} bytes to {local_path}")
        # --- end fix ---

        print(f"[DEBUG] extracting text from {local_path}")
        text = text_from_file(local_path)
        print(f"[DEBUG] extracted text length: {len(text)} chars")

        doc_type = classify(text)
        parser = parse_bank if doc_type == "bank" else parse_merchant
        print(f"[DEBUG] parsing with {parser.__name__}")
        rows, conf = parser(text, cid)
        print(f"[DEBUG] parse result rows={rows} confidence={conf:.2f}")

        # 3. Enrich and insert
        for table, rowset in rows.items():
            for r in rowset:
                r.update(
                    raw_file_url=key,
                    confidence=round(conf, 2),
                    needs_review=(conf < 0.70),
                )
            print(f"[DEBUG] inserting into table={table} rows={rowset}")
            SB.table(table).insert(rowset).execute()

        results.append({"file": name, "doc_type": doc_type, "confidence": round(conf, 2)})

    global_block = {"customer_id": cid}
    print(f"[DEBUG] finished all files, global={global_block}")
    return {"files": results, "global": global_block}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "ai_underwriter.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )