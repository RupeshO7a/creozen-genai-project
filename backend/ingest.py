
import ast
import json
import os
import time

import requests
from dotenv import load_dotenv

from db import supabase

load_dotenv()

BATCH_SIZE = 10
PAGE_SIZE = 500
MAX_RETRIES = 3
EMBED_DIMENSIONS = 1024

SOURCE_TABLE = "chunks"
STAGING_TABLE = "chunks_cloudflare_staging"

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
MODEL = os.getenv(
    "CLOUDFLARE_EMBED_MODEL",
    "@cf/qwen/qwen3-embedding-0.6b",
)


def parse_embedding(value):
    """Convert a Supabase vector response into a Python list."""
    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = ast.literal_eval(value)

        if isinstance(parsed, list):
            return parsed

    return None


def fetch_all_chunks():
    """Read source chunks without modifying the source table."""
    records = []
    offset = 0

    while True:
        response = (
            supabase.table(SOURCE_TABLE)
            .select("id,content,source,page")
            .order("id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )

        batch = response.data or []
        records.extend(batch)

        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return records


def get_embeddings(texts):
    """Generate 1024-dimensional embeddings with Cloudflare."""
    if not ACCOUNT_ID or not API_TOKEN:
        raise RuntimeError(
            "Missing CLOUDFLARE_ACCOUNT_ID or "
            "CLOUDFLARE_API_TOKEN in backend/.env."
        )

    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{ACCOUNT_ID}/ai/run/{MODEL}"
    )

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        json={"text": texts},
        timeout=90,
    )

    if not response.ok:
        raise RuntimeError(
            f"Cloudflare returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    payload = response.json()

    if not payload.get("success", True):
        raise RuntimeError(
            "Cloudflare embedding error: "
            f"{str(payload.get('errors'))[:500]}"
        )

    vectors = payload.get("result", {}).get("data")

    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise RuntimeError(
            "Cloudflare returned an unexpected embedding count."
        )

    for vector in vectors:
        if (
            not isinstance(vector, list)
            or len(vector) != EMBED_DIMENSIONS
        ):
            actual = len(vector) if isinstance(vector, list) else "invalid"
            raise RuntimeError(
                f"Expected {EMBED_DIMENSIONS} dimensions; got {actual}."
            )

    return vectors


def embed_with_retry(texts):
    """Retry temporary embedding API failures."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return get_embeddings(texts)
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise

            delay = attempt * 3
            print(
                f"Embedding request failed ({type(exc).__name__}). "
                f"Retrying in {delay} seconds..."
            )
            time.sleep(delay)


def fetch_staging():
    """Read all staging rows, including stored embeddings."""
    records = []
    offset = 0

    while True:
        response = (
            supabase.table(STAGING_TABLE)
            .select("id,content,source,page,embedding")
            .order("id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )

        batch = response.data or []
        records.extend(batch)

        if len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return records


def verify_staging(original):
    """Verify IDs, source fields, row count, and vector dimensions."""
    staged_rows = fetch_staging()
    staged_by_id = {}

    for row in staged_rows:
        row_id = row["id"]

        if row_id in staged_by_id:
            raise RuntimeError(f"Duplicate staging ID: {row_id}")

        staged_by_id[row_id] = row

    if len(staged_rows) != len(original):
        raise RuntimeError(
            f"Row count mismatch: original={len(original)}, "
            f"staging={len(staged_rows)}. Do not switch retrieval."
        )

    for source_row in original:
        row_id = source_row["id"]
        staged = staged_by_id.get(row_id)

        if staged is None:
            raise RuntimeError(f"Missing staging record ID {row_id}.")

        for column in ("content", "source", "page"):
            if staged.get(column) != source_row.get(column):
                raise RuntimeError(
                    f"Data mismatch for ID {row_id}, column {column}."
                )

        vector = parse_embedding(staged.get("embedding"))

        if vector is None or len(vector) != EMBED_DIMENSIONS:
            actual = len(vector) if vector is not None else "invalid"
            raise RuntimeError(
                f"Invalid embedding for ID {row_id}; "
                f"expected {EMBED_DIMENSIONS}, got {actual}."
            )

    print("\nVerification passed.")
    print(f"Original records: {len(original)}")
    print(f"Cloudflare staging records: {len(staged_rows)}")
    print(f"Embedding dimensions: {EMBED_DIMENSIONS}")
    print("All IDs and source fields match.")


def main():
    print("Checking Cloudflare configuration...")

    if not ACCOUNT_ID or not API_TOKEN:
        raise RuntimeError(
            "Configure CLOUDFLARE_ACCOUNT_ID and "
            "CLOUDFLARE_API_TOKEN in backend/.env."
        )

    print("Reading original chunks...")
    original = fetch_all_chunks()

    if not original:
        raise RuntimeError("The original chunks table is empty.")

    original_ids = [row["id"] for row in original]

    if len(original_ids) != len(set(original_ids)):
        raise RuntimeError("Duplicate IDs found in original chunks.")

    for row in original:
        if not row.get("content"):
            raise RuntimeError(
                f"Original chunk ID {row['id']} has empty content."
            )

    print(f"Original records found: {len(original)}")

    # Verify existing staging data first. This avoids unnecessary
    # embedding API calls if all 604 records are already correct.
    staged_rows = fetch_staging()
    staged_ids = {row["id"] for row in staged_rows}
    original_id_set = set(original_ids)

    unexpected_ids = staged_ids - original_id_set
    if unexpected_ids:
        raise RuntimeError(
            "Staging contains IDs absent from the original table. "
            "Inspect staging before continuing."
        )

    print(f"Already staged: {len(staged_ids)}")

    if len(staged_ids) == len(original_ids):
        print("All source IDs are already staged; checking data now.")
        verify_staging(original)
        return

    pending = [row for row in original if row["id"] not in staged_ids]
    print(f"Records remaining to embed: {len(pending)}")

    confirmation = input(
        f"\nThis will write {len(pending)} missing records ONLY to "
        f"{STAGING_TABLE}. Type STAGE to continue: "
    ).strip()

    if confirmation != "STAGE":
        print("Cancelled. No new records written.")
        return

    completed = len(staged_ids)

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        vectors = embed_with_retry(
            [row["content"] for row in batch]
        )

        staging_rows = []

        for row, vector in zip(batch, vectors):
            staging_rows.append({
                "id": row["id"],
                "content": row["content"],
                "source": row["source"],
                "page": row["page"],
                "embedding": vector,
            })

        # Insert only missing IDs. Never overwrite existing embeddings
        # automatically, because their validity must be checked first.
        response = (
            supabase.table(STAGING_TABLE)
            .insert(staging_rows)
            .execute()
        )

        inserted = response.data or []

        if len(inserted) != len(staging_rows):
            raise RuntimeError(
                "Staging insert count mismatch. Inspect staging "
                "before retrying."
            )

        completed += len(inserted)
        print(f"Staged this run: {completed}/{len(original)}")

    print("\nVerifying the complete staging table...")
    verify_staging(original)


if __name__ == "__main__":
    main()
