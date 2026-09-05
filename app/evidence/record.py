import os
import json
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from app.evidence.hashing import canonicalize_and_hash

def build_evidence_record(
    input_image_bytes: bytes,
    matched_candidate: dict,
    search_provider: str = "serpapi_google_lens",
    fixed_timestamp: str | None = None
) -> dict:
    """
    Constructs a standardized evidence record dictionary.
    
    Args:
        input_image_bytes: Raw bytes of input target image.
        matched_candidate: Match candidate dict containing image_url, page_url, similarity, candidate_image_bytes.
        search_provider: Search provider identifier string.
        fixed_timestamp: Optional fixed UTC ISO timestamp string (used for testing).
        
    Returns:
        dict: Standardized evidence record.
    """
    input_sha256 = hashlib.sha256(input_image_bytes).hexdigest()
    
    cand_bytes = matched_candidate.get("candidate_image_bytes", b"")
    matched_sha256 = hashlib.sha256(cand_bytes).hexdigest() if cand_bytes else ""
    
    page_url = matched_candidate.get("page_url", "")
    domain = urlparse(page_url).netloc if page_url else ""
    
    similarity = round(float(matched_candidate.get("similarity", 0.0)), 4)
    
    timestamp = fixed_timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    record = {
        "schema_version": 1,
        "input_image_sha256": input_sha256,
        "matched_image_sha256": matched_sha256,
        "matched_post_url": page_url,
        "source_domain": domain,
        "similarity": similarity,
        "search_provider": search_provider,
        "timestamp": timestamp
    }

    return record


def save_artifacts(
    record: dict,
    canonical_json: str,
    evidence_hash: str,
    matched_candidate: dict,
    blockchain_receipt: dict | None = None,
    output_dir: str = "artifacts"
) -> dict:
    """
    Saves evidence.json, matched.jpg, and blockchain_receipt.json into the artifacts directory.
    
    Returns:
        dict: Saved artifact file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    evidence_path = os.path.join(output_dir, "evidence.json")
    matched_path = os.path.join(output_dir, "matched.jpg")
    receipt_path = os.path.join(output_dir, "blockchain_receipt.json")

    # Save canonical evidence JSON
    with open(evidence_path, "w", encoding="utf-8") as f:
        f.write(canonical_json)

    # Save matched candidate image if available
    cand_bytes = matched_candidate.get("candidate_image_bytes")
    if cand_bytes:
        with open(matched_path, "wb") as f:
            f.write(cand_bytes)

    # Save blockchain receipt if present
    if blockchain_receipt:
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(blockchain_receipt, f, indent=2)

    return {
        "evidence_json": evidence_path,
        "matched_jpg": matched_path if cand_bytes else None,
        "blockchain_receipt": receipt_path if blockchain_receipt else None,
        "evidence_hash": evidence_hash
    }
