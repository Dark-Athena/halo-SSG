from __future__ import annotations

from urllib.parse import urlparse, urljoin


def is_same_domain(url: str, base_url: str) -> bool:
    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    if not parsed.netloc:
        return True
    return parsed.netloc == base_parsed.netloc


def normalize_url(url: str, base_url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return base_url.rstrip("/") + url
    if not url.startswith("http"):
        return base_url.rstrip("/") + "/" + url
    return url


def to_relative_path(url: str, base_url: str) -> str:
    if url.startswith(base_url):
        return url[len(base_url.rstrip("/")):]
    parsed = urlparse(url)
    if not parsed.netloc:
        return url
    return url


def permalink_to_filepath(permalink: str) -> str:
    path = permalink.strip("/")
    if not path:
        return "index.html"
    return f"{path}/index.html"
