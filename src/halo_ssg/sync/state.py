from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("halo_ssg.sync")


class SyncState:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.data = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        return {"last_sync": None, "posts": {}, "pages": {}, "assets": {}}

    def save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.data["last_sync"] = datetime.now(timezone.utc).isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_post_hash(self, slug: str) -> str | None:
        return self.data.get("posts", {}).get(slug, {}).get("content_hash")

    def set_post_hash(self, slug: str, content_hash: str, last_modified: str = "") -> None:
        if "posts" not in self.data:
            self.data["posts"] = {}
        self.data["posts"][slug] = {
            "content_hash": content_hash,
            "last_modified": last_modified,
            "last_fetched": datetime.now(timezone.utc).isoformat(),
        }

    def get_page_hash(self, slug: str) -> str | None:
        return self.data.get("pages", {}).get(slug, {}).get("content_hash")

    def set_page_hash(self, slug: str, content_hash: str, last_modified: str = "") -> None:
        if "pages" not in self.data:
            self.data["pages"] = {}
        self.data["pages"][slug] = {
            "content_hash": content_hash,
            "last_modified": last_modified,
            "last_fetched": datetime.now(timezone.utc).isoformat(),
        }

    def get_post_slugs(self) -> set[str]:
        return set(self.data.get("posts", {}).keys())

    def get_page_slugs(self) -> set[str]:
        return set(self.data.get("pages", {}).keys())

    def remove_post(self, slug: str) -> None:
        self.data.get("posts", {}).pop(slug, None)

    def remove_page(self, slug: str) -> None:
        self.data.get("pages", {}).pop(slug, None)

    def needs_update(self, slug: str, current_modified: str, content_type: str = "post") -> bool:
        store = self.data.get(f"{content_type}s", {})
        entry = store.get(slug)
        if not entry:
            return True
        stored_modified = entry.get("last_modified", "")
        # If we don't have stored_modified, need to re-fetch
        if not stored_modified:
            return True
        if current_modified and current_modified != stored_modified:
            return True
        return False
