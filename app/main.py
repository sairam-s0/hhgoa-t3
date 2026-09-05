import os
import sys
import json
import argparse
import logging
from dotenv import load_dotenv


os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.face.detector import detect_single_face
from app.face.embedder import generate_dual_embedding
from app.search.serpapi import search
from app.verification.matcher import match_candidates
from app.evidence.record import build_evidence_record, save_artifacts
from app.evidence.hashing import canonicalize_and_hash
from app.blockchain.client import BlockchainClient

load_dotenv()

def run_pipeline(image_path: str, threshold: float | None = None) -> bool:
    """
    Executes end-to-end face verification and blockchain anchoring pipeline.
    
    Args:
        image_path: Path to target input image.
        threshold: Cosine similarity threshold (defaults to SIMILARITY_THRESHOLD env var or 0.72).
        
    Returns:
        bool: True if match found, anchored, and re-verified successfully; False otherwise.
    """
    if threshold is None:
        threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.72"))

    print("\n============================================")
    print("FACE-CHAIN-VERIFIER")
    print("============================================\n")

    # Step 1: Face Detection
    print("[1] Face Detection")
    if image_path.startswith("http://") or image_path.startswith("https://"):
        import requests
        resp = requests.get(image_path, timeout=15)
        if resp.status_code != 200:
            print(f"    ✗ Error: Failed to download URL image: {image_path}")
            return False
        input_bytes = resp.content
    else:
        if not os.path.exists(image_path):
            print(f"    ✗ Error: Image file not found: {image_path}")
            return False

        with open(image_path, "rb") as f:
            input_bytes = f.read()


    try:
        detection = detect_single_face(input_bytes)
        print(f"    ✓ {detection['face_count']} face detected")
    except ValueError as e:
        print(f"    ✗ Face Detection Failed: {e}")
        return False
    except Exception as e:
        print(f"    ✗ Error reading image: {e}")
        return False

    # Step 2: Face Embedding (ArcFace + Facenet512 ensemble)
    print("\n[2] Face Embedding")
    try:
        input_embedding = generate_dual_embedding(detection["face_crop"])
        print("    ✓ ArcFace + Facenet512 dual embeddings generated on aligned face crop")
    except Exception as e:
        print(f"    ✗ Embedding Generation Failed: {e}")
        return False



    # Step 3: Reverse Image Search (SerpApi / Google Lens)
    print("\n[3] Reverse Image Search")
    print("    Provider: SerpApi / Google Lens")
    try:
        candidates = search(image_path)
        print(f"    ✓ {len(candidates)} candidates discovered")
    except Exception as e:
        print(f"    ✗ Search Provider Error: {e}")
        return False

    if not candidates:
        print("    ✗ No candidate visual matches found.")
        return False

    # Step 4: Candidate Verification
    print("\n[4] Candidate Verification")
    matched_candidates = match_candidates(input_embedding, candidates)
    
    for idx, cand in enumerate(matched_candidates, 1):
        sim = cand['similarity']
        is_pass = sim >= threshold
        mark = "✓" if is_pass else ""
        print(f"    Candidate {idx:02d} → {sim:.4f} {mark}")

    # Step 5: Check Best Match
    if not matched_candidates:
        print("\n    ✗ No candidates passed face detection or feature matching.")
        return False

    best_match = matched_candidates[0]
    best_sim = best_match["similarity"]

    if best_sim < threshold:
        print(f"\n    ✗ No candidate passed the face similarity threshold ({threshold:.4f}). Best similarity was {best_sim:.4f}.")
        return False

    if best_match.get("is_ambiguous", False):
        print(f"\n    ⚠️ Match Ambiguous: {best_match.get('ambiguity_reason')}")
        print("    ✗ Automatic blockchain anchoring stopped due to narrow candidate similarity margin (< 0.03).")
        return False

    print("\n[5] MATCH FOUND")
    print(f"    Post: {best_match['page_url']}")
    print(f"    Similarity: {best_sim:.4f}")


    # Step 6: Evidence JSON & SHA-256
    print("\n[6] Evidence")
    record = build_evidence_record(
        input_image_bytes=input_bytes,
        matched_candidate=best_match,
        search_provider=best_match.get("source", "serpapi_google_lens")
    )
    
    canonical_json, evidence_hash = canonicalize_and_hash(record)
    print("    ✓ evidence.json")
    print(f"    ✓ SHA-256: {evidence_hash}")

    # Step 7: Blockchain Anchoring
    print("\n[7] Blockchain")
    bc_client = BlockchainClient()
    try:
        receipt = bc_client.register_hash(evidence_hash)
        print(f"    ✓ Transaction: {receipt['tx_hash']}")
        print(f"    ✓ Block: {receipt['block_number']}")
    except Exception as e:
        print(f"    ✗ Blockchain Registration Failed: {e}")
        return False

    # Save all output artifacts to disk
    artifact_paths = save_artifacts(
        record=record,
        canonical_json=canonical_json,
        evidence_hash=evidence_hash,
        matched_candidate=best_match,
        blockchain_receipt=receipt
    )

    # Step 8: Re-verification
    print("\n[8] Re-verification")
    with open(artifact_paths["evidence_json"], "r", encoding="utf-8") as f:
        read_evidence = json.load(f)
    
    recomputed_json, recomputed_hash = canonicalize_and_hash(read_evidence)
    print("    ✓ Hash reconstructed")

    is_on_chain = bc_client.is_registered(recomputed_hash)
    if not is_on_chain:
        print("    ✗ Re-verification Failed: Recomputed hash not found on blockchain.")
        return False
    print("    ✓ On-chain record found")

    if recomputed_hash != evidence_hash:
        print("    ✗ Re-verification Failed: Recomputed hash does not match evidence hash.")
        return False
    print("    ✓ Hashes match")

    print("\n============================================")
    print("VERIFIED")
    print("============================================\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Face-Chain-Verifier CLI")
    parser.add_argument("--image", type=str, default="samples/input.jpg", help="Path to input image file")
    parser.add_argument("--threshold", type=float, default=None, help="Custom similarity threshold")
    
    args = parser.parse_args()
    success = run_pipeline(args.image, args.threshold)
    sys.exit(0 if success else 1)
