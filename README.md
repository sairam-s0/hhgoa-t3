<div align="center">

# 🔗 Face-Chain-Verifier

[![Version](https://img.shields.io/badge/version-1.0.0-blueviolet?style=for-the-badge)](.)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Solidity](https://img.shields.io/badge/Solidity-%5E0.8.24-363636?style=for-the-badge&logo=solidity)](contracts/EvidenceRegistry.sol)
[![Hardhat](https://img.shields.io/badge/Hardhat-2.22-f7c948?style=for-the-badge&logo=ethereum&logoColor=black)](https://hardhat.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![DeepFace](https://img.shields.io/badge/DeepFace-ArcFace%20%2B%20Facenet512-FF6B6B?style=for-the-badge&logo=tensorflow&logoColor=white)](https://github.com/serengil/deepface)
[![web3.py](https://img.shields.io/badge/web3.py-Ethereum-3C3C3D?style=for-the-badge&logo=ethereum)](https://web3py.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](.)

<br/>

**Face verification + tamper-proof blockchain evidence anchoring — end-to-end.**

> Given a single face photo, the system reverse-image-searches the web, biometrically verifies every candidate with an ArcFace + Facenet512 ensemble, produces a canonical SHA-256 evidence record, and permanently registers the hash onto an Ethereum smart contract — then re-verifies integrity before declaring a match.

</div>

---

## ✨ Feature Highlights

| Feature | Detail |
|---|---|
| 🎯 **Face Detection** | RetinaFace primary → OpenCV Haar cascade fallback; EXIF-aware, blur-gated |
| 🧠 **Dual Embedding** | ArcFace (512-d) + Facenet512 (512-d) ensemble; L2-normalised cosine similarity |
| 🔍 **Reverse Image Search** | SerpApi / Google Lens with automatic URL resolution |
| 🔗 **Blockchain Anchoring** | Solidity `EvidenceRegistry` on Hardhat local chain; idempotent on-chain writes |
| 📄 **Evidence Record** | Canonical JSON (schema v1): input SHA-256, matched SHA-256, URL, similarity, timestamp |
| ✅ **Re-verification** | Hash reconstructed from disk and cross-checked against the chain |
| 🌐 **REST API** | FastAPI dashboard at `http://127.0.0.1:8000` |
| 🖥️ **CLI** | `python -m app.main --image <path> [--threshold 0.72]` |
| 🧪 **Test Suite** | `pytest` — blockchain, face detection, hashing, matcher, search |

---

## 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                   INPUT  (file path / URL)               │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │  [1]  FACE DETECTION          │
             │  app/face/detector.py         │
             │                               │
             │  Primary : RetinaFace (DL)    │
             │  Fallback: OpenCV Haar        │
             │  EXIF auto-rotate via Pillow  │
             │  Blur gate  (Laplacian ≥ 15)  │
             │  Enforces exactly 1 face      │
             └───────────────┬───────────────┘
                             │  aligned face crop (BGR)
                             ▼
             ┌───────────────────────────────┐
             │  [2]  DUAL EMBEDDING          │
             │  app/face/embedder.py         │
             │                               │
             │  ArcFace    512-d  (L2-norm)  │
             │  Facenet512 512-d  (L2-norm)  │
             └───────────────┬───────────────┘
                             │  { arcface, facenet512 }
                             ▼
             ┌───────────────────────────────┐
             │  [3]  REVERSE IMAGE SEARCH    │
             │  app/search/serpapi.py        │
             │  app/search/resolver.py       │
             │                               │
             │  SerpApi / Google Lens API    │
             │  → candidates []              │
             │    { page_url, image_url,     │
             │      title, source }          │
             └───────────────┬───────────────┘
                             │  candidates[]
                             ▼
             ┌───────────────────────────────┐
             │  [4]  CANDIDATE VERIFICATION  │
             │  app/verification/matcher.py  │
             │                               │
             │  Per candidate:               │
             │  ├─ resolve image bytes       │
             │  ├─ detect_all_faces()        │
             │  ├─ ArcFace embed each face   │
             │  └─ cosine_similarity()       │
             │                               │
             │  Ensemble:                    │
             │  0.60×ArcFace + 0.40×FaceNet  │
             │                               │
             │  Ambiguity guard  margin<0.03 │
             │  Early-stop       sim≥0.90    │
             │  Sort descending → best match │
             └───────────────┬───────────────┘
                             │  best_match  (sim ≥ threshold)
                             ▼
             ┌───────────────────────────────┐
             │  [5]  EVIDENCE RECORD         │
             │  app/evidence/record.py       │
             │  app/evidence/hashing.py      │
             │                               │
             │  evidence.json  schema v1:    │
             │  ├─ input_image_sha256        │
             │  ├─ matched_image_sha256      │
             │  ├─ matched_post_url          │
             │  ├─ source_domain             │
             │  ├─ similarity                │
             │  ├─ search_provider           │
             │  └─ timestamp  (UTC ISO 8601) │
             │                               │
             │  Canonical JSON → SHA-256     │
             └───────────────┬───────────────┘
                             │  evidence_hash  (hex)
                             ▼
             ┌───────────────────────────────┐
             │  [6]  BLOCKCHAIN ANCHORING    │
             │  app/blockchain/client.py     │
             │  contracts/EvidenceRegistry   │
             │                               │
             │  web3.py → Hardhat JSON-RPC   │
             │  EvidenceRegistry.register()  │
             │  → tx_hash  +  block_number   │
             └───────────────┬───────────────┘
                             │  blockchain_receipt
                             ▼
             ┌───────────────────────────────┐
             │  [7]  SAVE ARTIFACTS          │
             │  artifacts/                   │
             │  ├─ evidence.json             │
             │  ├─ matched.jpg               │
             │  ├─ blockchain_receipt.json   │
             │  └─ candidates/               │
             └───────────────┬───────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │  [8]  RE-VERIFICATION         │
             │                               │
             │  Reconstruct hash from disk   │
             │  isRegistered(hash) → bool    │
             │  Hash equality check          │
             │                               │
             │  ✅ VERIFIED  /  ❌ FAILED    │
             └───────────────────────────────┘
```

---

## 📦 Repository Layout

```text
hhgoa-t3/
├── app/
│   ├── main.py                 # CLI entry point — 8-step pipeline
│   ├── server.py               # FastAPI REST API + web dashboard
│   ├── face/
│   │   ├── detector.py         # RetinaFace / OpenCV detection & alignment
│   │   └── embedder.py         # ArcFace + Facenet512 L2-normalised embeddings
│   ├── search/
│   │   ├── serpapi.py          # Google Lens search via SerpApi
│   │   └── resolver.py         # HTTP image downloader / resolver
│   ├── verification/
│   │   └── matcher.py          # Ensemble scoring, ambiguity guard
│   ├── evidence/
│   │   ├── record.py           # Evidence record builder & artifact saver
│   │   └── hashing.py          # Canonical JSON + SHA-256 hasher
│   ├── blockchain/
│   │   └── client.py           # web3.py BlockchainClient
│   ├── static/                 # Frontend static assets
│   └── templates/              # Jinja2 HTML templates
├── contracts/
│   └── EvidenceRegistry.sol    # Solidity smart contract (^0.8.24)
├── scripts/
│   └── deploy.js               # Hardhat deploy → writes .env + deployment.json
├── tests/
│   ├── test_blockchain.py
│   ├── test_face.py
│   ├── test_hashing.py
│   ├── test_matcher.py
│   └── test_search.py
├── artifacts/                  # Runtime outputs (git-ignored)
├── samples/                    # Sample input images
├── hardhat.config.js
├── package.json
├── requirements.txt
└── .env.example
```

---

## ⚙️ Smart Contract

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract EvidenceRegistry {
    struct Record {
        address submitter;
        uint256 timestamp;
    }

    mapping(bytes32 => Record) private records;

    event EvidenceRegistered(
        bytes32 indexed evidenceHash,
        address indexed submitter,
        uint256 timestamp
    );

    /// @notice Register an evidence hash on-chain (reverts if already registered)
    function register(bytes32 evidenceHash) external;

    /// @notice Returns true if the hash has been anchored
    function isRegistered(bytes32 evidenceHash) external view returns (bool);

    /// @notice Returns submitter address and block timestamp for a hash
    function getRecord(bytes32 evidenceHash) external view returns (address, uint256);
}
```

> **Idempotent by design.** Calling `register()` twice for the same hash reverts with `"Already registered"`.
> The Python `BlockchainClient` also performs a pre-flight `isRegistered()` check to avoid wasting gas.

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.10 |
| Node.js | ≥ 18 |
| Git | any |

---

### Step 1 — Clone

```bash
git clone <your-repo-url>
cd hhgoa-t3
```

---

### Step 2 — Python virtual environment

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

> **Note:** `deepface` downloads ArcFace, Facenet512, and RetinaFace weights on first run (~500 MB).

---

### Step 3 — Node / Hardhat dependencies

```bash
npm install
```

---

### Step 4 — Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
# Get a free key at https://serpapi.com
SERPAPI_KEY=your_serpapi_key_here

# Leave as-is for local Hardhat node
WEB3_PROVIDER_URI=http://127.0.0.1:8545

# Auto-populated by deploy.js — leave blank for now
CONTRACT_ADDRESS=

# Cosine similarity cutoff (0.0 – 1.0)
SIMILARITY_THRESHOLD=0.72
```

---

### Step 5 — Start Hardhat node

Open a **dedicated terminal** and leave it running:

```bash
npm run node
```

```
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/

Accounts
========
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Account #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
...
```

---

### Step 6 — Compile & deploy the smart contract

Back in your main terminal (`.venv` active):

```bash
# Compile Solidity
npm run compile

# Deploy — auto-updates CONTRACT_ADDRESS in .env
npm run deploy
```

Expected output:

```
Deploying EvidenceRegistry contract...
✓ EvidenceRegistry deployed to address: 0x5FbDB2315678afecb367f032d93F642f64180aa3
✓ Updated CONTRACT_ADDRESS in .env to 0x5FbDB2315678afecb367f032d93F642f64180aa3
```

---

### Step 7A — CLI

```bash
# Local image
python -m app.main --image samples/input.jpg

# Custom threshold
python -m app.main --image samples/input.jpg --threshold 0.80

# Direct URL
python -m app.main --image "https://example.com/photo.jpg"
```

**Example output:**

```
============================================
FACE-CHAIN-VERIFIER
============================================

[1] Face Detection
    ✓ 1 face detected

[2] Face Embedding
    ✓ ArcFace + Facenet512 dual embeddings generated on aligned face crop

[3] Reverse Image Search
    Provider: SerpApi / Google Lens
    ✓ 8 candidates discovered

[4] Candidate Verification
    Candidate 01 → 0.9123 ✓
    Candidate 02 → 0.8241
    Candidate 03 → 0.7804

[5] MATCH FOUND
    Post: https://twitter.com/example/status/...
    Similarity: 0.9123

[6] Evidence
    ✓ evidence.json
    ✓ SHA-256: a3f2c1d9e8b7...

[7] Blockchain
    ✓ Transaction: 0x4a3b2c1d...
    ✓ Block: 3

[8] Re-verification
    ✓ Hash reconstructed
    ✓ On-chain record found
    ✓ Hashes match

============================================
VERIFIED
============================================
```

---

### Step 7B — Web Dashboard

```bash
python -m app.server
# or
uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000** in your browser.

**REST endpoint:**

```
POST /api/verify
Content-Type: multipart/form-data

Fields:
  file       — image file (required)
  threshold  — float, default 0.72 (optional)
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8000/api/verify \
  -F "file=@samples/input.jpg" \
  -F "threshold=0.72"
```

**Success response:**

```json
{
  "success": true,
  "status": "VERIFIED",
  "face_count": 1,
  "similarity": 0.9123,
  "matched_post_url": "https://twitter.com/...",
  "evidence_hash": "a3f2c1d9e8b7...",
  "blockchain": {
    "tx_hash": "0x4a3b2c1d...",
    "block_number": 3,
    "status": "SUCCESS"
  },
  "reverification": {
    "hash_reconstructed": true,
    "on_chain_found": true,
    "hashes_match": true,
    "verified": true
  }
}
```

---

### Step 8 — Tests

```bash
pytest tests/ -v

# Individual modules
pytest tests/test_blockchain.py -v
pytest tests/test_face.py -v
pytest tests/test_hashing.py -v
pytest tests/test_matcher.py -v
pytest tests/test_search.py -v
```

---

## 🔬 Technical Details

### Face Detection

```
Input Image
  │
  ├─ EXIF transpose (Pillow ImageOps.exif_transpose)
  │
  ├─ [Primary]  DeepFace.extract_faces()
  │              ├─ RetinaFace  — conf ≥ 0.70, size ≥ 30 px
  │              └─ OpenCV      — conf ≥ 0.50, size ≥ 30 px
  │
  └─ [Fallback] OpenCV CascadeClassifier
                 scaleFactor=1.05, minNeighbors=7, minSize=50 px

Output → landmark-aligned BGR crop
       → blur gate   Laplacian variance ≥ 15.0
       → size gate   ≥ 40 × 40 px
```

### Embedding & Similarity

| Property | Value |
|---|---|
| ArcFace dim | 512 |
| Facenet512 dim | 512 |
| Normalisation | L2 (unit norm) |
| Metric | Cosine similarity |
| Ensemble | `0.60 × ArcFace + 0.40 × Facenet512` |
| Default threshold | `0.72` |
| Ambiguity guard | top-2 margin < 0.03 → reject |
| Early stop | sim ≥ 0.90 at candidate index ≥ 5 |

### Evidence Record (schema v1)

```json
{
  "schema_version": 1,
  "input_image_sha256": "<64-char hex>",
  "matched_image_sha256": "<64-char hex>",
  "matched_post_url": "https://...",
  "source_domain": "twitter.com",
  "similarity": 0.9123,
  "search_provider": "serpapi_google_lens",
  "timestamp": "2026-09-05T12:00:00Z"
}
```

Keys are lexicographically sorted and similarity rounded to 4 decimal places before hashing — guaranteeing byte-exact reproducibility.

### Blockchain Flow

```
Python                        Hardhat  (localhost:8545)
  │                                  │
  │  isRegistered(bytes32) ─────────►│
  │◄──────────── false ──────────────│
  │                                  │
  │  register(bytes32) ─────────────►│  emit EvidenceRegistered(hash, sender, ts)
  │◄──────── tx_hash ────────────────│
  │                                  │
  │  wait_for_transaction_receipt()  │
  │◄────────── receipt ──────────────│
  │                                  │
  │  isRegistered(bytes32) ─────────►│  re-verification
  │◄──────────── true ───────────────│
```

---

## 🌍 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SERPAPI_KEY` | ✅ | — | SerpApi key for Google Lens |
| `WEB3_PROVIDER_URI` | ✅ | `http://127.0.0.1:8545` | Ethereum JSON-RPC endpoint |
| `CONTRACT_ADDRESS` | ✅ after deploy | — | Deployed `EvidenceRegistry` address |
| `SIMILARITY_THRESHOLD` | ❌ | `0.72` | Cosine similarity cutoff |

---

## 🎛️ CLI Reference

```
python -m app.main [OPTIONS]

Options:
  --image PATH        Image file path or HTTPS URL  (default: samples/input.jpg)
  --threshold FLOAT   Similarity threshold override  (default: env / 0.72)
  -h, --help

Exit codes:
  0  VERIFIED — match found, anchored, re-verified on-chain
  1  FAILED   — no match / below threshold / ambiguous / error
```

---

## 📤 Output Artifacts

| File | Description |
|---|---|
| `artifacts/evidence.json` | Canonical evidence record (schema v1) |
| `artifacts/matched.jpg` | Best-match candidate image |
| `artifacts/blockchain_receipt.json` | tx hash, block number, submitter, status |
| `artifacts/deployment.json` | Contract address + deploy timestamp |
| `artifacts/candidates/candidate_NN.jpg` | All resolved candidate images |

---

## 🔐 Security & Privacy Notes

1. **No raw faces on-chain** — only the SHA-256 hash of the evidence record is written to contract storage.
2. **Idempotent writes** — re-running the same image produces the same hash; the contract rejects duplicates.
3. **Local node only** — `BlockchainClient` uses `accounts[0]` (pre-funded Hardhat account). For testnets/mainnet, use a proper wallet + private key signing.
4. **SerpApi requires a public URL** — for local file paths the file must be reachable publicly; use a tunnel (ngrok) or a pre-signed URL for privacy-sensitive use.

---

## 🙏 Acknowledgements

- [DeepFace](https://github.com/serengil/deepface) — ArcFace & RetinaFace
- [SerpApi](https://serpapi.com) — Google Lens reverse image search
- [Hardhat](https://hardhat.org) — Ethereum local development
- [web3.py](https://web3py.readthedocs.io) — Python Ethereum client
- [FastAPI](https://fastapi.tiangolo.com) — async REST framework

---

<div align="center">

[![Built with Python + Solidity](https://img.shields.io/badge/built%20with-Python%20%2B%20Solidity-blueviolet?style=flat-square)](.)
[![Blockchain](https://img.shields.io/badge/blockchain-Ethereum%20%28Hardhat%29-f7c948?style=flat-square&logo=ethereum)](.)
[![AI](https://img.shields.io/badge/AI-DeepFace%20ArcFace-FF6B6B?style=flat-square&logo=tensorflow)](.)

**Face-Chain-Verifier** — Biometric truth, anchored forever on-chain.

</div>
