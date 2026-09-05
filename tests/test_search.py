import pytest
from app.search.serpapi import _normalize_serpapi_results

def test_serpapi_normalization():
    """Verifies SerpApi raw response data normalizes into candidate dictionary schema."""
    raw_response = {
        "visual_matches": [
            {
                "title": "Sample Match 1",
                "link": "https://instagram.com/p/123",
                "thumbnail": "https://example.com/thumb1.jpg",
                "source": "Instagram"
            },
            {
                "title": "Sample Match 2",
                "source": "https://facebook.com/photo/456",
                "original": "https://example.com/orig2.jpg"
            }
        ]
    }

    candidates = _normalize_serpapi_results(raw_response)

    assert len(candidates) == 2
    assert candidates[0]["title"] == "Sample Match 1"
    assert candidates[0]["page_url"] == "https://instagram.com/p/123"
    assert candidates[0]["image_url"] == "https://example.com/thumb1.jpg"
    assert candidates[0]["is_social_media"] is True
    assert candidates[1]["is_social_media"] is True

    assert candidates[1]["page_url"] == "https://facebook.com/photo/456"
    assert candidates[1]["image_url"] == "https://example.com/orig2.jpg"
