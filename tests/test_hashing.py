import pytest
from app.evidence.record import build_evidence_record
from app.evidence.hashing import canonicalize_and_hash

def test_evidence_hashing_determinism():
    """Verifies that canonical evidence hashing is 100% deterministic given identical records."""
    dummy_input = b"input_image_bytes_12345"
    dummy_cand = {
        "candidate_image_bytes": b"cand_image_bytes_67890",
        "page_url": "https://example.com/post/1",
        "similarity": 0.84219999
    }
    
    # Build record with fixed timestamp
    record1 = build_evidence_record(dummy_input, dummy_cand, fixed_timestamp="2026-09-04T12:00:00Z")
    record2 = build_evidence_record(dummy_input, dummy_cand, fixed_timestamp="2026-09-04T12:00:00Z")

    json1, hash1 = canonicalize_and_hash(record1)
    json2, hash2 = canonicalize_and_hash(record2)

    assert json1 == json2
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 length


def test_evidence_hashing_tamper_detection():
    """Verifies that altering any field in evidence record alters the SHA-256 hash."""
    dummy_input = b"input_image_bytes_12345"
    dummy_cand = {
        "candidate_image_bytes": b"cand_image_bytes_67890",
        "page_url": "https://example.com/post/1",
        "similarity": 0.8421
    }
    
    record = build_evidence_record(dummy_input, dummy_cand, fixed_timestamp="2026-09-04T12:00:00Z")
    _, original_hash = canonicalize_and_hash(record)

    # Tamper with URL
    record_tampered = dict(record)
    record_tampered["matched_post_url"] = "https://example.com/post/tampered"
    _, tampered_hash = canonicalize_and_hash(record_tampered)

    assert original_hash != tampered_hash
