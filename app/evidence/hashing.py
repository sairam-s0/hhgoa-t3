import json
import hashlib

def canonicalize_and_hash(record: dict) -> tuple[str, str]:
    """
    Deterministically serializes evidence record to JSON and computes SHA-256 hash.
    
    Args:
        record: Evidence record dictionary.
        
    Returns:
        tuple[str, str]: (canonical_json_string, sha256_hex_hash)
    """
    # Deterministic JSON string: sorted keys, compact separators, no trailing spaces
    canonical_json = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )
    
    # SHA-256 hash computation
    sha256_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    
    return canonical_json, sha256_hash
