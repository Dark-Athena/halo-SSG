from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from halo_ssg.models import Post, Category, Tag, SinglePage, CategoryRef, TagRef
from halo_ssg.exceptions import APIError

logger = logging.getLogger("halo_ssg.api")

API_BASE = "/apis/api.content.halo.run/v1alpha1"


class HaloClient:
    def __init__(self, base_url: str, timeout: int = 30, user_agent: str = "Halo-SSG/1.0"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> HaloClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(3):
            try:
                resp = self.client.get(path, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = int(e.response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise APIError(f"HTTP {e.response.status_code} for {path}") from e
            except httpx.RequestError as e:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise APIError(f"Request failed for {path}: {e}") from e
        raise APIError(f"Failed after retries: {path}")

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def _parse_post(self, item: dict) -> Post:
        spec = item.get("spec", {})
        status = item.get("status", {})
        stats = item.get("stats", {})

        categories = []
        for cat in item.get("categories", []):
            cat_spec = cat.get("spec", {})
            cat_status = cat.get("status", {})
            categories.append(CategoryRef(
                name=cat.get("metadata", {}).get("name", ""),
                display_name=cat_spec.get("displayName", ""),
                slug=cat_spec.get("slug", ""),
                permalink=cat_status.get("permalink", ""),
            ))

        tags = []
        for tag in item.get("tags", []):
            tag_spec = tag.get("spec", {})
            tag_status = tag.get("status", {})
            tags.append(TagRef(
                name=tag.get("metadata", {}).get("name", ""),
                display_name=tag_spec.get("displayName", ""),
                slug=tag_spec.get("slug", ""),
                permalink=tag_status.get("permalink", ""),
            ))

        return Post(
            name=item.get("metadata", {}).get("name", ""),
            title=spec.get("title", ""),
            slug=spec.get("slug", ""),
            permalink=status.get("permalink", ""),
            publish_time=self._parse_datetime(spec.get("publishTime")),
            last_modify_time=self._parse_datetime(status.get("lastModifyTime")),
            excerpt=status.get("excerpt", ""),
            cover=spec.get("cover", ""),
            categories=categories,
            tags=tags,
            visit_count=stats.get("visit", 0),
        )

    def fetch_posts(self, page_size: int = 100) -> list[Post]:
        all_posts = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            logger.info(f"Fetching posts page {page}/{total_pages}...")
            data = self._get(
                f"{API_BASE}/posts",
                params={"page": page, "size": page_size},
            )
            total_pages = data.get("totalPages", 1)
            for item in data.get("items", []):
                all_posts.append(self._parse_post(item))
            page += 1

        logger.info(f"Fetched {len(all_posts)} posts total.")
        return all_posts

    def fetch_categories(self) -> list[Category]:
        data = self._get(f"{API_BASE}/categories", params={"page": 0, "size": 100})
        categories = []
        for item in data.get("items", []):
            spec = item.get("spec", {})
            status = item.get("status", {})
            categories.append(Category(
                name=item.get("metadata", {}).get("name", ""),
                display_name=spec.get("displayName", ""),
                slug=spec.get("slug", ""),
                description=spec.get("description", ""),
                post_count=status.get("visiblePostCount", 0),
                children=spec.get("children", []),
                permalink=status.get("permalink", ""),
            ))
        logger.info(f"Fetched {len(categories)} categories.")
        return categories

    def fetch_tags(self) -> list[Tag]:
        data = self._get(f"{API_BASE}/tags", params={"page": 0, "size": 100})
        tags = []
        for item in data.get("items", []):
            spec = item.get("spec", {})
            status = item.get("status", {})
            tags.append(Tag(
                name=item.get("metadata", {}).get("name", ""),
                display_name=spec.get("displayName", ""),
                slug=spec.get("slug", ""),
                color=spec.get("color", ""),
                post_count=status.get("visiblePostCount", 0),
                permalink=status.get("permalink", ""),
            ))
        logger.info(f"Fetched {len(tags)} tags.")
        return tags

    def fetch_single_pages(self) -> list[SinglePage]:
        data = self._get(f"{API_BASE}/singlepages", params={"page": 0, "size": 100})
        pages = []
        for item in data.get("items", []):
            spec = item.get("spec", {})
            status = item.get("status", {})
            pages.append(SinglePage(
                name=item.get("metadata", {}).get("name", ""),
                title=spec.get("title", ""),
                slug=spec.get("slug", ""),
                permalink=status.get("permalink", ""),
                excerpt=status.get("excerpt", ""),
            ))
        logger.info(f"Fetched {len(pages)} single pages.")
        return pages
