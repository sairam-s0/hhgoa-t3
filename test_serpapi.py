import os
import sys
import json
import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

def test_serpapi_search(image_input: str):
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key:
        print("ERROR: SERPAPI_KEY is not set in .env file.")
        sys.exit(1)

    print("==================================================")
    print("SERPAPI REAL GOOGLE LENS REVERSE SEARCH")
    print("==================================================")
    print(f"Target Image Input: {image_input}")

    if image_input.startswith("http://") or image_input.startswith("https://"):
        image_url = image_input
    else:
        if not os.path.exists(image_input):
            print(f"ERROR: Local image file not found: {image_input}")
            sys.exit(1)
        
        print("Uploading local file to temporary public host for Google Lens...")
        image_url = upload_local_file(image_input)
        if not image_url:
            print("ERROR: Failed to obtain public URL for image.")
            sys.exit(1)
        print(f"✓ Public Image URL: {image_url}")

    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": api_key
    }

    print("\nSending live request to SerpApi...")
    resp = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    print(f"SerpApi HTTP Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"ERROR: SerpApi request failed: {resp.text}")
        sys.exit(1)

    data = resp.json()

    # Save raw API response to artifacts
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/raw_serpapi_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    visual_matches = data.get("visual_matches", [])
    images_results = data.get("images_results", [])

    candidates = []
    for match in visual_matches:
        title = match.get("title", "No Title")
        page_url = match.get("link", match.get("source", ""))
        img_url = match.get("thumbnail") or match.get("original", "")
        source = match.get("source", "google_lens")
        
        if page_url and img_url:
            candidates.append({
                "title": title,
                "page_url": page_url,
                "image_url": img_url,
                "source": source
            })

    if not candidates and images_results:
        for match in images_results:
            title = match.get("title", "No Title")
            page_url = match.get("link", "")
            img_url = match.get("original") or match.get("thumbnail", "")
            
            if page_url and img_url:
                candidates.append({
                    "title": title,
                    "page_url": page_url,
                    "image_url": img_url,
                    "source": "google_lens"
                })

    print(f"\nDiscovered {len(candidates)} real visual match candidates from SerpApi:\n")
    for idx, c in enumerate(candidates, 1):
        print(f"[{idx:02d}] {c['title']}")
        print(f"     Source:   {c['source']}")
        print(f"     Page URL: {c['page_url']}")
        print(f"     Img URL:  {c['image_url']}\n")

    return candidates


def upload_local_file(filepath: str) -> str | None:
    # Strategy 1: catbox.moe
    try:
        with open(filepath, "rb") as f:
            resp = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=15)
        if resp.status_code == 200 and resp.text.startswith("http"):
            return resp.text.strip()
    except Exception:
        pass

    # Strategy 2: tmpfiles.org
    try:
        with open(filepath, "rb") as f:
            resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=15)
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url", "")
            if url:
                return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass

    return None



if __name__ == "__main__":
    target_img = sys.argv[1] if len(sys.argv) > 1 else "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80"
    test_serpapi_search(target_img)
