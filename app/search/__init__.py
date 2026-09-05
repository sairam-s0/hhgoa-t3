"""
Search package initialization.
"""
from app.search.serpapi import search
from app.search.resolver import resolve_image

__all__ = ["search", "resolve_image"]
