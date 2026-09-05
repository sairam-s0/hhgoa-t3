import os
import sys
import json
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from app.face.detector import detect_single_face
from app.face.embedder import generate_dual_embedding

from app.search.serpapi import search
from app.verification.matcher import match_candidates
from app.evidence.record import build_evidence_record, save_artifacts
from app.evidence.hashing import canonicalize_and_hash
from app.blockchain.client import BlockchainClient

app = FastAPI(title="Face-Chain-Verifier Dashboard")

# Setup templates and static directories
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/templates", exist_ok=True)
os.makedirs("artifacts", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/verify")
async def verify_image(file: UploadFile = File(...), threshold: float = Form(0.72)):
    """Runs end-to-end verification pipeline from uploaded image file."""
    try:
        contents = await file.read()
        
        # Save temp file
        temp_path = os.path.join("artifacts", f"uploaded_{file.filename}")
        with open(temp_path, "wb") as f:
            f.write(contents)

        # 1. Face Detection
        try:
            detection = detect_single_face(contents)
            face_count = detection["face_count"]
        except ValueError as e:
            return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

        # 2. Face Embedding (ArcFace + Facenet512 ensemble)
        input_embedding = generate_dual_embedding(detection["face_crop"])



        # 3. Reverse Image Search
        candidates = search(temp_path)

        if not candidates:
            return JSONResponse(status_code=200, content={
                "success": False,
                "error": "No visual candidates discovered via SerpApi / Google Lens search."
            })


        # 4. Candidate Verification
        matched = match_candidates(input_embedding, candidates)
        if not matched:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "No candidate images could be resolved or matched."
            })

        best = matched[0]
        best_sim = float(best["similarity"])

        if best_sim < threshold:
            return JSONResponse(status_code=200, content={
                "success": False,
                "error": f"Best similarity ({best_sim:.4f}) below threshold ({threshold:.4f}). No verified match.",
                "best_similarity": best_sim,
                "candidates": [{"title": c["title"], "page_url": c["page_url"], "similarity": float(c["similarity"])} for c in matched]
            })

        if best.get("is_ambiguous", False):
            return JSONResponse(status_code=200, content={
                "success": False,
                "error": f"Match is ambiguous: {best.get('ambiguity_reason')}",
                "is_ambiguous": True,
                "best_similarity": best_sim,
                "candidates": [{"title": c["title"], "page_url": c["page_url"], "similarity": float(c["similarity"])} for c in matched]
            })


        # 5. Evidence JSON & Hashing
        record = build_evidence_record(contents, best)
        canonical_json, evidence_hash = canonicalize_and_hash(record)

        # 6. Blockchain Anchoring
        bc_client = BlockchainClient()
        receipt = bc_client.register_hash(evidence_hash)

        # 7. Save Artifacts
        artifacts = save_artifacts(record, canonical_json, evidence_hash, best, receipt)

        # 8. Re-verification
        recomputed_json, recomputed_hash = canonicalize_and_hash(record)
        is_on_chain = bc_client.is_registered(recomputed_hash)
        hashes_match = (recomputed_hash == evidence_hash)

        return {
            "success": True,
            "status": "VERIFIED",
            "face_count": face_count,
            "similarity": best_sim,
            "matched_post_url": best["page_url"],
            "matched_title": best["title"],
            "evidence_hash": evidence_hash,
            "evidence_record": record,
            "blockchain": receipt,
            "reverification": {
                "hash_reconstructed": True,
                "on_chain_found": is_on_chain,
                "hashes_match": hashes_match,
                "verified": is_on_chain and hashes_match
            },
            "candidates": [
                {
                    "title": c.get("title", "Candidate"),
                    "page_url": c.get("page_url", "#"),
                    "image_url": c.get("image_url", ""),
                    "similarity": float(c.get("similarity", 0.0))
                }
                for c in matched[:10]
            ]
        }


    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.server:app", host="127.0.0.1", port=8000, reload=True)
