<div align="center">

# 🔗 Face-Chain-Verifier

<img src="https://img.shields.io/badge/version-1.0.0-blueviolet?style=for-the-badge&logo=semver" alt="version"/>
<img src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="python"/>
<img src="https://img.shields.io/badge/solidity-%5E0.8.24-363636?style=for-the-badge&logo=solidity" alt="solidity"/>
<img src="https://img.shields.io/badge/hardhat-2.22-f7c948?style=for-the-badge&logo=ethereum&logoColor=black" alt="hardhat"/>
<img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="fastapi"/>
<img src="https://img.shields.io/badge/DeepFace-ArcFace%20%2B%20Facenet512-FF6B6B?style=for-the-badge&logo=tensorflow&logoColor=white" alt="deepface"/>
<img src="https://img.shields.io/badge/web3.py-Ethereum-3C3C3D?style=for-the-badge&logo=ethereum" alt="web3"/>
<img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="license"/>

<br/>

> **Face verification + tamper-proof blockchain evidence anchoring — in one end-to-end pipeline.**
>
> Given a single face photo, the system reverse-image-searches the web, biometrically verifies
> every candidate with an ArcFace + Facenet512 ensemble, produces a canonical SHA-256 evidence
> record, and permanently registers the hash onto an Ethereum smart contract — then re-verifies
> integrity before declaring a match.

</div>

---

## ✨ Feature Highlights

| Feature | Detail |
|---|---|
| 🎯 **Face Detection** | RetinaFace primary → OpenCV Haar cascade fallback; EXIF-aware, blur-gated |
| 🧠 **Dual Embedding** | ArcFace (512-d) + Facenet512 (512-d) ensemble; L2-normalized cosine similarity |
| 🔍 **Reverse Image Search** | SerpApi / Google Lens with automatic URL resolution |
| 🔗 **Blockchain Anchoring** | Solidity `EvidenceRegistry` on Hardhat local chain; idempotent on-chain writes |
| 📄 **Evidence Record** | Canonical JSON (schema v1): input SHA-256, matched SHA-256, URL, similarity, timestamp |
| ✅ **Re-verification** | Hash reconstructed and cross-checked against chain after anchoring |
| 🌐 **REST API** | FastAPI dashboard at `http://127.0.0.1:8000` |
| 🖥️ **CLI** | `python -m app.main --image <path> [--threshold 0.72]` |
| 🧪 **Test Suite** | `pytest` covers blockchain, face detection, hashing, matcher, and search |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INPUT (Image / URL)                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │   [1] FACE DETECTION          │
                │   app/face/detector.py        │
                │                               │
                │   Primary: RetinaFace (DL)    │
                │   Fallback: OpenCV Haar       │
                │   EXIF auto-rotate            │
                │   Blur gate (Laplacian var)   │
                │   Enforces exactly 1 face     │
                └──────────────┬───────────────┘
                               │  face_crop (aligned BGR)
                               ▼
                ┌──────────────────────────────┐
                │   [2] DUAL EMBEDDING          │
                │   app/face/embedder.py        │
                │                               │
                │   ArcFace  (512-d, L2-norm)   │
                │   Facenet512 (512-d, L2-norm) │
                └──────────────┬───────────────┘
                               │  {arcface, facenet512}
                               ▼
                ┌──────────────────────────────┐
                │   [3] REVERSE IMAGE SEARCH    │
                │   app/search/serpapi.py       │
                │   app/search/resolver.py      │
                │                               │
                │   SerpApi / Google Lens API   │
                │   → candidate list [{         │
                │       page_url, image_url,    │
                │       title, source }]        │
                └──────────────┬───────────────┘
                               │  candidates[]
                               ▼
                ┌──────────────────────────────┐
                │   [4] CANDIDATE VERIFICATION  │
                │   app/verification/matcher.py │
                │                               │
                │   For each candidate:         │
                │   ├─ Resolve image bytes      │
                │   ├─ detect_all_faces()       │
                │   ├─ ArcFace embed each face  │
                │   └─ cosine_similarity()      │
                │                               │
                │   Ensemble score:             │
                │   0.60×ArcFace + 0.40×FaceNet │
                │                               │
                │   Ambiguity guard: margin<0.03│
                │   Early-stop: sim≥0.90@idx≥5  │
                │   Sort descending → best match│
                └──────────────┬───────────────┘
                               │  best_match (sim ≥ threshold)
                               ▼
                ┌──────────────────────────────┐
                │   [5] EVIDENCE RECORD         │
                │   app/evidence/record.py      │
                │   app/evidence/hashing.py     │
                │                               │
                │   evidence.json (schema v1):  │
                │   ├─ input_image_sha256       │
                │   ├─ matched_image_sha256     │
                │   ├─ matched_post_url         │
                │   ├─ source_domain            │
                │   ├─ similarity               │
                │   ├─ search_provider          │
                │   └─ timestamp (UTC ISO)      │
                │                               │
                │   Canonical JSON → SHA-256    │
                └──────────────┬───────────────┘
                               │  evidence_hash (hex)
                               ▼
                ┌──────────────────────────────┐
                │   [6] BLOCKCHAIN ANCHORING    │
                │   app/blockchain/client.py    │
                │   contracts/EvidenceRegistry  │
                │                               │
                │   web3.py → Hardhat JSON-RPC  │
                │   EvidenceRegistry.register() │
                │   → tx_hash + block_number    │
                └──────────────┬───────────────┘
                               │  blockchain_receipt
                               ▼
                ┌──────────────────────────────┐
                │   [7] SAVE ARTIFACTS          │
                │   artifacts/                  │
                │   ├─ evidence.json            │
                │   ├─ matched.jpg              │
                │   ├─ blockchain_receipt.json  │
                │   └─ candidates/              │
                └──────────────┬───────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │   [8] RE-VERIFICATION         │
                │                               │
                │   Reconstruct hash from disk  │
                │   isRegistered(hash) → bool   │
                │   Hash equality check         │
                │   → ✅ VERIFIED / ❌ FAILED   │
                └──────────────────────────────┘
```

---

## 📦 Repository Layout

```
hhgoa-t3/
│
├── app/
│   ├── main.py                   # CLI entry point — 8-step pipeline
│   ├── server.py                 # FastAPI REST API + dashboard
│   │
│   ├── face/
│   │   ├── detector.py           # RetinaFace / OpenCV face detection & alignment
│   │   └── embedder.py           # ArcFace + Facenet512 L2-normalized embeddings
│   │
│   ├── search/
│   │   ├── serpapi.py            # Google Lens reverse image search via SerpApi
│   │   └── resolver.py           # HTTP image resolver / downloader
│   │
│   ├── verification/
│   │   └── matcher.py            # Candidate scoring, ensemble similarity, ambiguity guard
│   │
│   ├── evidence/
│   │   ├── record.py             # Evidence record builder & artifact saver
│   │   └── hashing.py            # Canonical JSON serializer + SHA-256 hasher
│   │
│   ├── blockchain/
│   │   └── client.py             # web3.py BlockchainClient — register / query on-chain
│   │
│   ├── static/                   # Frontend static assets
│   └── templates/                # Jinja2 HTML templates
│
├── contracts/
│   └── EvidenceRegistry.sol      # Solidity smart contract (Solidity ^0.8.24)
│
├── scripts/
│   └── deploy.js                 # Hardhat deploy script → writes .env + deployment.json
│
├── tests/
│   ├── test_blockchain.py        # BlockchainClient unit tests
│   ├── test_face.py              # Face detection unit tests
│   ├── test_hashing.py           # Evidence hashing unit tests
│   ├── test_matcher.py           # Matcher / cosine similarity tests
│   └── test_search.py            # Search resolver tests
│
├── artifacts/                    # Runtime outputs (git-ignored)
├── samples/                      # Sample input images
├── hardhat.config.js             # Hardhat network configuration
├── package.json                  # Node.js / Hardhat dependencies
├── requirements.txt              # Python dependencies
└── .env.example                  # Environment variable template
```

---

## ⚙️ Smart Contract — `EvidenceRegistry.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract EvidenceRegistry {
    struct Record {
        address submitter;
        uint256 timestamp;
    }

    mapping(bytes32 => Record) private records;

    event EvidenceRegistered(bytes32 indexed evidenceHash, address indexed submitter, uint256 timestamp);

    function register(bytes32 evidenceHash) external;       // Write: anchor hash on-chain
    function isRegistered(bytes32 evidenceHash) external view returns (bool);   // Query
    function getRecord(bytes32 evidenceHash) external view returns (address, uint256); // Lookup
}
```

- **Idempotent**: calling `register()` twice for the same hash reverts with `"Already registered"`.
- **Python-side guard**: `BlockchainClient.register_hash()` checks `isRegistered()` before sending a transaction — returns `ALREADY_ANCHORED_ON_CHAIN` without wasting gas.

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.10 | [python.org](https://python.org) |
| Node.js | ≥ 18 | [nodejs.org](https://nodejs.org) |
| Git | any | [git-scm.com](https://git-scm.com) |

---

### 1 — Clone & enter the project

```bash
git clone <your-repo-url>
cd hhgoa-t3
```

---

### 2 — Python environment & dependencies

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

> **Note:** `deepface` will auto-download model weights (ArcFace, Facenet512, RetinaFace) on first run — this can take a few minutes.

---

### 3 — Node.js / Hardhat setup

```bash
npm install
```

---

### 4 — Environment configuration

```bash
cp .env.example .env
```

Edit `.env` with your values:

```dotenv
# SerpApi API key — get one free at https://serpapi.com
SERPAPI_KEY=your_serpapi_key_here

# Hardhat local node (default — do not change for local dev)
WEB3_PROVIDER_URI=http://127.0.0.1:8545

# Filled automatically by deploy.js — leave blank for now
CONTRACT_ADDRESS=

# Cosine similarity threshold (0.0 – 1.0)
SIMILARITY_THRESHOLD=0.72
```

---

### 5 — Start the Hardhat local blockchain node

Open a **separate terminal** and keep it running:

```bash
npm run node
```

You will see 20 pre-funded test accounts printed. Leave this terminal open.

```
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/

Accounts
========
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Account #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
...
```

---

### 6 — Compile & deploy the smart contract

Back in your **main terminal** (with `.venv` active):

```bash
# Compile Solidity
npm run compile

# Deploy EvidenceRegistry — auto-updates CONTRACT_ADDRESS in .env
npm run deploy
```

Expected output:

```
Deploying EvidenceRegistry contract...
✓ EvidenceRegistry deployed to address: 0x5FbDB2315678afecb367f032d93F642f64180aa3
✓ Updated CONTRACT_ADDRESS in .env to 0x5FbDB2315678afecb367f032d93F642f64180aa3
```

---

### 7A — Run via CLI

```bash
# Basic run with a local image
python -m app.main --image samples/input.jpg

# Custom similarity threshold
python -m app.main --image samples/input.jpg --threshold 0.80

# Run with a direct image URL
python -m app.main --image "https://example.com/face.jpg"
```

**Example pipeline output:**

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
    ...

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

### 7B — Run via FastAPI Web Dashboard

```bash
python -m app.server
# or equivalently:
uvicorn app.server:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser: **http://127.0.0.1:8000**

**REST endpoint:**

```
POST /api/verify
Content-Type: multipart/form-data

file=<image file>
threshold=0.72   (optional, default 0.72)
```

**Example with `curl`:**

```bash
curl -X POST http://127.0.0.1:8000/api/verify \
  -F "file=@samples/input.jpg" \
  -F "threshold=0.72"
```

**Successful JSON response:**

```json
{
  "success": true,
  "status": "VERIFIED",
  "face_count": 1,
  "similarity": 0.9123,
  "matched_post_url": "https://twitter.com/...",
  "matched_title": "...",
  "evidence_hash": "a3f2c1d9e8b7...",
  "evidence_record": { "..." : "..." },
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
  },
  "candidates": [ "..." ]
}
```

---

### 8 — Run the test suite

```bash
# Run all tests
pytest tests/ -v

# Run individual modules
pytest tests/test_blockchain.py -v
pytest tests/test_face.py -v
pytest tests/test_hashing.py -v
pytest tests/test_matcher.py -v
pytest tests/test_search.py -v
```

---

## 🔬 Technical Deep Dive

### Face Detection Pipeline

```
Input Image
    │
    ├── EXIF transpose (auto-rotate) via Pillow
    │
    ├── [Primary]  DeepFace.extract_faces()
    │               ├── Backend: RetinaFace  (conf ≥ 0.70, size ≥ 30px)
    │               └── Backend: OpenCV      (conf ≥ 0.50, size ≥ 30px)
    │
    └── [Fallback] OpenCV CascadeClassifier
                    └── haarcascade_frontalface_default.xml
                         scaleFactor=1.05, minNeighbors=7, minSize=50px

Output: Landmark-aligned BGR face crop
        → Laplacian variance blur gate (var ≥ 15.0)
        → Size gate (≥ 40×40 px)
```

### Embedding & Similarity

| Property | Value |
|---|---|
| ArcFace embedding dim | 512 |
| Facenet512 embedding dim | 512 |
| Normalization | L2 (unit norm) |
| Similarity metric | Cosine similarity |
| Ensemble formula | `0.60 × ArcFace + 0.40 × Facenet512` |
| Default threshold | `0.72` (configurable via env) |
| Ambiguity margin | `< 0.03` between top-2 triggers rejection |
| Early stop | `sim ≥ 0.90` after candidate index 5 |

### Evidence Record Schema (v1)

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

The record is **canonically serialized** (sorted keys, compact) before SHA-256 hashing to guarantee byte-exact reproducibility across machines and time zones.

### Blockchain Sequence

```
Python Client                       Hardhat Node (localhost:8545)
     │                                          │
     │   web3.HTTPProvider(uri)                 │
     │ ◄────────────────────────────────────── ►│
     │                                          │
     │   isRegistered(bytes32)  ───────────────►│
     │ ◄──────────────── false ─────────────────│
     │                                          │
     │   register(bytes32)  ───────────────────►│  EvidenceRegistry.register()
     │                                          │  → emit EvidenceRegistered(hash, sender, ts)
     │ ◄─────────────── tx_hash ────────────────│
     │                                          │
     │   wait_for_transaction_receipt()         │
     │ ◄──────────────── receipt ───────────────│
     │                                          │
     │   isRegistered(bytes32)  ───────────────►│  Re-verification call
     │ ◄───────────────── true ─────────────────│
```

---

## 🌍 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SERPAPI_KEY` | ✅ | — | SerpApi API key for Google Lens search |
| `WEB3_PROVIDER_URI` | ✅ | `http://127.0.0.1:8545` | Ethereum JSON-RPC endpoint |
| `CONTRACT_ADDRESS` | ✅ after deploy | — | Deployed `EvidenceRegistry` address |
| `SIMILARITY_THRESHOLD` | ❌ | `0.72` | Cosine similarity cutoff (0.0 – 1.0) |

---

## 🎛️ CLI Reference

```
python -m app.main [OPTIONS]

Options:
  --image PATH        Path to input image file or HTTPS URL
                      (default: samples/input.jpg)
  --threshold FLOAT   Cosine similarity threshold override
                      (default: $SIMILARITY_THRESHOLD or 0.72)
  -h, --help          Show this message and exit

Exit codes:
  0 — VERIFIED (match found, anchored, re-verified on-chain)
  1 — FAILED   (no match, below threshold, ambiguous, or error)
```

---

## 📤 Output Artifacts

After a successful run, the following files are written to `artifacts/`:

| File | Description |
|---|---|
| `evidence.json` | Canonical evidence record (schema v1) |
| `matched.jpg` | Downloaded best-match candidate image |
| `blockchain_receipt.json` | Transaction hash, block number, submitter, status |
| `deployment.json` | Contract address + deploy timestamp (written by deploy.js) |
| `candidates/candidate_NN.jpg` | All resolved candidate images (for UI preview) |
| `uploaded_<filename>` | Uploaded image saved by the FastAPI server |

---

## 🛠️ Development

### Adding a new search provider

1. Create `app/search/my_provider.py` with a `search(image_path: str) -> list[dict]` function.
2. Each result dict must contain: `page_url`, `image_url`, `title`, `source`.
3. Wire it in `app/search/serpapi.py` or import directly in `main.py` / `server.py`.

### Deploying to a public testnet

1. Add the network to `hardhat.config.js` (e.g., Sepolia).
2. Export your private key via an environment variable.
3. Run: `npx hardhat run scripts/deploy.js --network sepolia`
4. Update `WEB3_PROVIDER_URI` in `.env` to your Alchemy / Infura RPC URL.

---

## 🙏 Acknowledgements

- [DeepFace](https://github.com/serengil/deepface) — ArcFace & RetinaFace inference
- [SerpApi](https://serpapi.com) — Google Lens reverse image search
- [Hardhat](https://hardhat.org) — Ethereum development environment
- [web3.py](https://web3py.readthedocs.io) — Python Ethereum client
- [FastAPI](https://fastapi.tiangolo.com) — Async REST API framework

---

<div align="center">

<img src="https://img.shields.io/badge/built%20with-Python%20%2B%20Solidity-blueviolet?style=flat-square"/>
<img src="https://img.shields.io/badge/blockchain-Ethereum%20(Hardhat)-f7c948?style=flat-square&logo=ethereum"/>
<img src="https://img.shields.io/badge/AI-DeepFace%20ArcFace-FF6B6B?style=flat-square&logo=tensorflow"/>

**Face-Chain-Verifier** — Biometric truth, anchored forever on-chain.

</div>

> Facial verification and cryptographic blockchain evidence anchoring system powered by DeepFace ArcFace, SerpApi (Google Lens), Hardhat smart contract, CLI, and modern Vanilla HTML/CSS web dashboard.

---

## 📐 Architecture & Pipeline

```text
Input image
   ↓
Face detection + ArcFace embedding
   ↓
SerpApi → Google Lens
   ↓
Real candidate pages/images
   ↓
Download candidate images
   ↓
ArcFace face verification
   ↓
Best match (Cosine Similarity thresholding)
   ↓
Canonical evidence JSON
   ↓
SHA-256
   ↓
Hardhat blockchain (EvidenceRegistry.sol)
   ↓
Read hash back
   ↓
Recompute + compare
   ↓
VERIFIED
```

---

## 🛠️ Tech Stack

- **Python**: DeepFace, ArcFace, OpenCV, NumPy, Requests, Pillow, BeautifulSoup4, Web3.py, FastAPI, Uvicorn
- **Smart Contract**: Solidity `0.8.24`, Hardhat local JSON-RPC node
- **Search Provider**: SerpApi (Google Lens engine)
- **Frontend**: Vanilla HTML5, Vanilla CSS3 (Dark Theme, Glassmorphism), Vanilla JavaScript

---

## 🚀 Installation & Setup

### 1. Clone & Setup Python Virtual Environment

```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```env
SERPAPI_KEY=your_serpapi_key_here
WEB3_PROVIDER_URI=http://127.0.0.1:8545
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
SIMILARITY_THRESHOLD=0.72
```


---

## ⛓️ Blockchain Setup

> ⚠️ **Important Deployment Sequence**: Hardhat in-memory state resets whenever `npx hardhat node` is restarted. Always run step 1 then step 2 fresh in that order before executing verification tests.

### 1. Install Node Dependencies & Start Local Hardhat Node

```powershell
npm install
npx hardhat node
```

*Keep this terminal running.*

### 2. Deploy Smart Contract (`EvidenceRegistry.sol`)

In a second terminal:

```powershell
npx hardhat run scripts/deploy.js --network localhost
```

This compiles `contracts/EvidenceRegistry.sol` and saves `CONTRACT_ADDRESS` automatically to `.env` and `artifacts/deployment.json`.

---

## 🖥️ Usage

### CLI Execution

Run the complete pipeline from CLI:

```powershell
python -m app.main --image samples/input.jpg
```

---

## 🌐 Web Dashboard (HTML/CSS)

Launch the FastAPI dashboard:

```powershell
python -m uvicorn app.server:app --reload
```

Open `http://127.0.0.1:8000` in your browser to interact with the drag-and-drop face verification UI.

---

## 🧪 Automated Testing

Run the test suite via `pytest`:

```powershell
python -m pytest tests/
```

Test coverage includes:
- Face detection, alignment, quality gating, and single-face enforcement (`test_face.py`)
- SerpApi response normalization and social media domain prioritization (`test_search.py`)
- Cosine similarity & composite model ensemble math (`test_matcher.py`)
- Deterministic canonical JSON hashing (`test_hashing.py`)
- Hardhat smart contract anchoring, idempotency, and duplicate prevention (`test_blockchain.py`)

---

## 📂 Project Structure

```text
face-chain-verifier/
│
├── app/
│   ├── main.py                # CLI Entry Point
│   ├── server.py              # FastAPI Web Backend
│   ├── face/
│   │   ├── detector.py        # RetinaFace Alignment & EXIF Transposition
│   │   └── embedder.py        # ArcFace + Facenet512 L2-Normalized Dual Embedding
│   ├── search/
│   │   ├── serpapi.py         # SerpApi Google Lens Client with Retry & Social Filtering
│   │   └── resolver.py        # Candidate Image Scraper & Pillow Validator
│   ├── verification/
│   │   └── matcher.py         # Ensemble Composite Similarity & Ambiguity Check
│   ├── evidence/
│   │   ├── record.py          # Canonical Evidence Builder
│   │   └── hashing.py         # Deterministic SHA-256 Hashing
│   ├── blockchain/
│   │   └── client.py          # Web3.py Hardhat Integration & Idempotency Guard
│   ├── static/                # CSS & JS Frontend Assets
│   └── templates/             # HTML Dashboard Template
│
├── contracts/
│   └── EvidenceRegistry.sol   # Solidity Smart Contract
├── scripts/
│   └── deploy.js              # Hardhat Deployment Script
├── samples/                   # Input & Test Images
├── artifacts/                 # Saved Evidence & Receipts
├── tests/                     # Pytest Test Suite
│
├── .env                       # Environment Secret Config (Git-Ignored)
├── .env.example               # Example Configuration Template
├── .gitignore
├── requirements.txt           # Python Dependencies
├── package.json               # Hardhat Node Dependencies
├── hardhat.config.js          # Hardhat Configuration
└── README.md
```

---

## 🔐 Privacy, Security & Architectural Considerations

1. **No Raw Faces On-Chain**: Neither raw face images nor high-dimensional face embedding vectors are sent to the blockchain.
2. **Cryptographic Fingerprint Only**: Only the SHA-256 hash of the canonical evidence record is written to Solidity contract storage (`mapping(bytes32 => Record)`).
3. **Deterministic Hashing**: Keys are lexicographically sorted (`sort_keys=True`) and similarity numbers are rounded to 4 decimal places before SHA-256 calculation to eliminate serialization discrepancy across environments.
4. **Local File Public Host Disclosure**: SerpApi Google Lens engine requires a publicly accessible HTTP/HTTPS image URL (`params["url"]`). When local image paths (e.g. `samples/input.jpg`) are provided instead of direct web URLs, the file is uploaded to temporary public storage. For privacy-sensitive production deployments, pass a direct pre-signed URL or host a local media server/tunnel.
5. **Localnet Pre-Funded Account Assumption**: `BlockchainClient` uses `web3.eth.accounts[0]` for transaction signing, assuming a local Hardhat node with pre-unlocked funded accounts. Production testnet/mainnet deployment requires private key transaction signing via KMS or Web3 account wallets.
6. **Outbound SSRF Notice**: Candidate page image resolving fetches external URLs indexed by search engines. In production, outbound network requests should be routed through a restricted proxy to prevent SSRF against internal network ranges.
7. **Similarity Threshold & Ambiguity Margin**: Default threshold is set to `0.72` based on empirical evaluation of ArcFace + Facenet512 ensemble cosine similarity. If top candidate similarity is within `0.03` of runner-up candidate similarity, the pipeline flags the result as `ambiguous` and prevents automatic blockchain anchoring.

---

## 📜 License

MIT License.

#   h h g o a - t 2  
 