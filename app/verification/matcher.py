import os
import numpy as np
from app.search.resolver import resolve_image
from app.face.detector import detect_all_faces, check_image_quality
from app.face.embedder import generate_embedding, generate_dual_embedding

def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Computes cosine similarity between two normalized embedding vectors."""
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


def compute_composite_similarity(target_embs: dict | np.ndarray, cand_embs: dict | np.ndarray) -> float:
    """
    Computes ensemble similarity score across ArcFace and Facenet512 embeddings.
    """
    if isinstance(target_embs, np.ndarray) or isinstance(cand_embs, np.ndarray):
        t_vec = target_embs if isinstance(target_embs, np.ndarray) else target_embs.get("arcface")
        c_vec = cand_embs if isinstance(cand_embs, np.ndarray) else cand_embs.get("arcface")
        return compute_cosine_similarity(t_vec, c_vec)

    sim_arcface = compute_cosine_similarity(target_embs["arcface"], cand_embs["arcface"])
    sim_facenet = compute_cosine_similarity(target_embs["facenet512"], cand_embs["facenet512"])

    # Ensemble weighted average (ArcFace 60%, Facenet512 40%)
    return float((0.60 * sim_arcface) + (0.40 * sim_facenet))


def match_candidates(input_embeddings: dict | np.ndarray, candidates: list[dict]) -> list[dict]:
    """
    Evaluates candidate visual matches against input face embeddings.
    Saves candidate image bytes locally to artifacts/candidates/ so UI renders the exact analyzed images.
    """
    matched_results = []
    cand_dir = os.path.join("artifacts", "candidates")
    os.makedirs(cand_dir, exist_ok=True)

    for idx, candidate in enumerate(candidates, 1):
        page_url = candidate.get("page_url", "")
        remote_img_url = candidate.get("image_url", "")
        title = candidate.get("title", f"Candidate {idx}")

        # Step 1: Resolve candidate image bytes
        img_bytes = resolve_image(candidate)
        if not img_bytes:
            print(f"  Candidate {idx:02d} → Unable to resolve image bytes")
            continue

        # Save downloaded candidate image bytes locally for UI preview
        local_filename = f"candidate_{idx:02d}.jpg"
        local_filepath = os.path.join(cand_dir, local_filename)
        try:
            with open(local_filepath, "wb") as f:
                f.write(img_bytes)
            local_image_url = f"/artifacts/candidates/{local_filename}"
        except Exception:
            local_image_url = remote_img_url

        # Step 2: Detect ALL faces in candidate image (group photo friendly)
        detected_faces = detect_all_faces(img_bytes)
        if not detected_faces:
            print(f"  Candidate {idx:02d} → No valid/quality faces detected")
            continue

        best_cand_sim = -1.0
        best_face_info = None

        # Step 3: ArcFace embedding for each detected face crop
        for face_idx, face in enumerate(detected_faces, 1):
            face_crop = face["face_crop"]

            # Quality gating (min size 40px, min blur variance 15.0)
            is_ok, reason = check_image_quality(face_crop)
            if not is_ok:
                continue

            try:
                cand_emb = generate_embedding(face_crop, model_name="ArcFace")
                target_vec = input_embeddings.get("arcface") if isinstance(input_embeddings, dict) else input_embeddings
                
                sim = compute_cosine_similarity(target_vec, cand_emb)
                if sim > best_cand_sim:
                    best_cand_sim = sim
                    best_face_info = face
            except Exception as e:
                print(f"  Candidate {idx:02d} (face {face_idx}) → Embedding error: {e}")

        if best_cand_sim < 0.0 or best_face_info is None:
            print(f"  Candidate {idx:02d} → Embedding scoring failed for all faces")
            continue

        matched_results.append({
            "title": title,
            "page_url": page_url,
            "image_url": local_image_url,
            "remote_image_url": remote_img_url,
            "similarity": best_cand_sim,
            "face_detected": True,
            "candidate_image_bytes": img_bytes,
            "source": candidate.get("source", "serpapi_google_lens")
        })

        # Early stop if a very strong match (>= 0.90) is found after processing top candidates
        if idx >= 5 and best_cand_sim >= 0.90:
            print(f"  ✓ High confidence match found ({best_cand_sim:.4f} >= 0.90). Early stopping candidate processing.")
            break



    # Sort descending by composite similarity score
    matched_results.sort(key=lambda x: x["similarity"], reverse=True)

    # Ambiguity margin check: if top match and 2nd match are within 0.03, flag as ambiguous
    if len(matched_results) >= 2:
        margin = matched_results[0]["similarity"] - matched_results[1]["similarity"]
        if margin < 0.03:
            matched_results[0]["is_ambiguous"] = True
            matched_results[0]["ambiguity_reason"] = f"Similarity margin between top candidate ({matched_results[0]['similarity']:.4f}) and runner-up ({matched_results[1]['similarity']:.4f}) is too narrow ({margin:.4f} < 0.03)."
        else:
            matched_results[0]["is_ambiguous"] = False
            matched_results[0]["ambiguity_reason"] = ""
    elif len(matched_results) == 1:
        matched_results[0]["is_ambiguous"] = False
        matched_results[0]["ambiguity_reason"] = ""

    return matched_results


