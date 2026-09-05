import io
import os
import requests
from PIL import Image
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DEFAULT_TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def resolve_image(candidate: dict) -> bytes | None:
    """
    Downloads image bytes from candidate dict.
    Tries image_url first. If missing or invalid, scrapes page_url for og:image, twitter:image, or img tags.
    Validates returned bytes with Pillow.
    
    Args:
        candidate: Candidate dictionary containing 'image_url' and/or 'page_url'.
        
    Returns:
        bytes of verified image or None if unresolvable.
    """
    image_url = candidate.get("image_url", "").strip()
    page_url = candidate.get("page_url", "").strip()

    # Step 1: Try local filepath if image_url points to a local file
    if image_url and os.path.exists(image_url):
        try:
            with open(image_url, "rb") as f:
                data = f.read()
            if _validate_image_bytes(data):
                return data
        except Exception:
            pass

    # Step 2: Try direct download from image_url if HTTP
    if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
        data = _fetch_bytes(image_url)
        if data and _validate_image_bytes(data):
            return data

    # Step 3: Fallback to page_url HTML parsing if image_url failed or is missing
    if page_url and (page_url.startswith("http://") or page_url.startswith("https://")):
        extracted_url = _scrape_image_url_from_page(page_url)
        if extracted_url:
            data = _fetch_bytes(extracted_url)
            if data and _validate_image_bytes(data):
                return data

    return None


def _fetch_bytes(url: str) -> bytes | None:
    """Helper to fetch raw bytes from URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"[Resolver Warning] Failed to fetch {url}: {e}")
    return None


def _scrape_image_url_from_page(page_url: str) -> str | None:
    """Scrapes meta og:image, twitter:image, or first img src from HTML page."""
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Check OpenGraph og:image
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        if og_img and og_img.get("content"):
            return urljoin(page_url, og_img["content"])

        # Check Twitter twitter:image
        tw_img = soup.find("meta", property="twitter:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if tw_img and tw_img.get("content"):
            return urljoin(page_url, tw_img["content"])

        # Check first img tag with src
        first_img = soup.find("img", src=True)
        if first_img:
            return urljoin(page_url, first_img["src"])

    except Exception as e:
        print(f"[Resolver Scraper Warning] Failed scraping page {page_url}: {e}")

    return None


def _validate_image_bytes(data: bytes) -> bool:
    """Validates if data is a valid image using Pillow."""
    if not data or len(data) < 100:
        return False
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        return True
    except Exception:
        return False
