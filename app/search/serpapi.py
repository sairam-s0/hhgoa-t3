import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

import os
import sys
import json
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

SOCIAL_MEDIA_DOMAINS = {
    "instagram.com", "facebook.com", "fb.com", "twitter.com", "x.com",
    "linkedin.com", "tiktok.com", "pinterest.com", "reddit.com",
    "threads.net", "youtube.com", "tumblr.com", "bsky.app"
}


def is_social_media_url(url: str) -> bool:
    """Checks if a URL belongs to a known social media platform."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in SOCIAL_MEDIA_DOMAINS)


def search(image_path: str, max_candidates: int = 15) -> list[dict]:
    """
    Performs reverse image search using SerpApi Google Lens engine.
    Limits candidate evaluation to the top N search results for high performance.
    
    Args:
        image_path: Path to local image file or direct image URL.
        max_candidates: Cap on candidates to return (default: 15).
        
    Returns:
        List of normalized candidate dicts prioritized by social media domain relevance.
    """
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key:
        raise ValueError("SERPAPI_KEY is not set in environment or .env file.")

    params = {
        "engine": "google_lens",
        "api_key": api_key
    }

    if image_path.startswith("http://") or image_path.startswith("https://"):
        params["url"] = image_path
    else:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")
        
        # Upload local file to temporary public host for Google Lens
        public_url = _upload_local_image(image_path)
        if not public_url:
            raise RuntimeError("Failed to obtain public URL for local image file.")
        params["url"] = public_url

    # Execute search with exponential backoff retries for transient failures / rate limits
    data = _execute_serpapi_request(params)

    # Save raw search response to artifacts for auditing
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/raw_serpapi_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    with open("artifacts/search_results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    all_results = _normalize_serpapi_results(data)
    return all_results[:max_candidates]


def _execute_serpapi_request(params: dict, max_retries: int = 3) -> dict:
    """Executes SerpApi search with exponential backoff retry logic."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(SERPAPI_SEARCH_URL, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if "error" in data:
                    raise RuntimeError(f"SerpApi returned error response: {data.get('error')}")
                return data

            if response.status_code in [429, 500, 502, 503, 504]:
                sleep_time = 2 ** (attempt - 1)
                print(f"[SerpApi Retry {attempt}/{max_retries}] HTTP status {response.status_code}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            else:
                raise RuntimeError(f"SerpApi HTTP request failed ({response.status_code}): {response.text}")
        except (requests.RequestException, RuntimeError) as e:
            last_error = e
            if attempt < max_retries:
                sleep_time = 2 ** (attempt - 1)
                print(f"[SerpApi Retry {attempt}/{max_retries}] Exception: {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

    raise RuntimeError(f"SerpApi request failed after {max_retries} attempts: {last_error}")


def _normalize_serpapi_results(data: dict) -> list[dict]:
    """Extracts visual_matches or images_results, preferring original high-resolution URLs over thumbnails."""
    results = []
    
    visual_matches = data.get("visual_matches", [])
    for match in visual_matches:
        title = match.get("title", "Visual Match")
        page_url = match.get("link", match.get("source", ""))
        # Prefer original high-res image URL over thumbnail to avoid small crops
        img_url = match.get("original") or match.get("thumbnail", "")
        
        if page_url and img_url:
            is_social = is_social_media_url(page_url)
            results.append({
                "title": title,
                "page_url": page_url,
                "image_url": img_url,
                "source": match.get("source", "serpapi_google_lens"),
                "is_social_media": is_social
            })

    if not results and "images_results" in data:
        for match in data.get("images_results", []):
            title = match.get("title", "Image Result")
            page_url = match.get("link", "")
            img_url = match.get("original") or match.get("thumbnail", "")
            
            if page_url and img_url:
                is_social = is_social_media_url(page_url)
                results.append({
                    "title": title,
                    "page_url": page_url,
                    "image_url": img_url,
                    "source": "serpapi_google_lens",
                    "is_social_media": is_social
                })

    # Sort results to prioritize real social media posts at top
    results.sort(key=lambda x: x["is_social_media"], reverse=True)
    return results



def _upload_local_image(image_path: str) -> str | None:
    """Uploads local image to temporary public host to pass direct URL to SerpApi."""
    # Strategy 1: catbox.moe
    try:
        with open(image_path, "rb") as f:
            resp = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=15)
        if resp.status_code == 200 and resp.text.startswith("http"):
            return resp.text.strip()
    except Exception:
        pass

    # Strategy 2: tmpfiles.org
    try:
        with open(image_path, "rb") as f:
            resp = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}, timeout=15)
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url", "")
            if url:
                return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass

    return None




if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=600&q=80"
    candidates = search(target)
    print(f"\nDiscovered {len(candidates)} real candidates:")
    for idx, c in enumerate(candidates, 1):
        print(f"\n{idx:02d}. {c['title']}\n    Page: {c['page_url']}\n    Image: {c['image_url']}")
