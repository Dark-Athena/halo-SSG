from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment

from halo_ssg.models import Post, Category, Tag, Moment, FriendLink

logger = logging.getLogger("halo_ssg.builder")


class IndexGenerator:
    def __init__(self, env: Environment, output_dir: Path):
        self.env = env
        self.output_dir = output_dir

    def generate_home(self, posts: list[Post], site_context: dict) -> None:
        ctx = {"posts": posts, **site_context}
        html = self.env.get_template("home.html").render(ctx)
        self._write("/index.html", html)

    def generate_archives(self, posts: list[Post], site_context: dict) -> None:
        grouped: dict[int, list[Post]] = defaultdict(list)
        for post in posts:
            year = post.publish_time.year if post.publish_time else 0
            grouped[year].append(post)

        sorted_grouped = dict(sorted(grouped.items(), reverse=True))
        for year in sorted_grouped:
            sorted_grouped[year].sort(
                key=lambda p: p.publish_time or p.publish_time,
                reverse=True,
            )

        ctx = {"posts": posts, "grouped_posts": sorted_grouped, **site_context}
        html = self.env.get_template("archives.html").render(ctx)
        self._write("/archives/index.html", html)

    def generate_categories(self, categories: list[Category], site_context: dict) -> None:
        ctx = {"categories": categories, **site_context}
        html = self.env.get_template("categories.html").render(ctx)
        self._write("/categories/index.html", html)

    def generate_category(self, category: Category, posts: list[Post], site_context: dict) -> None:
        ctx = {"category": category, "posts": posts, **site_context}
        html = self.env.get_template("category.html").render(ctx)
        self._write(f"{category.permalink}/index.html", html)

    def generate_tags(self, tags: list[Tag], site_context: dict) -> None:
        ctx = {"tags": tags, **site_context}
        html = self.env.get_template("tags.html").render(ctx)
        self._write("/tags/index.html", html)

    def generate_tag(self, tag: Tag, posts: list[Post], site_context: dict) -> None:
        ctx = {"tag": tag, "posts": posts, **site_context}
        html = self.env.get_template("tag.html").render(ctx)
        self._write(f"{tag.permalink}/index.html", html)

    def generate_links(self, links: list[FriendLink], site_context: dict) -> None:
        grouped: dict[str, list[FriendLink]] = defaultdict(list)
        for link in links:
            grouped[link.group or "默认"].append(link)
        ctx = {"grouped_links": dict(grouped), **site_context}
        html = self.env.get_template("links.html").render(ctx)
        self._write("/links/index.html", html)

    def generate_moments(self, moments: list[Moment], site_context: dict) -> None:
        ctx = {"moments": moments, **site_context}
        html = self.env.get_template("moments.html").render(ctx)
        self._write("/moments/index.html", html)

    def _write(self, path: str, html: str) -> None:
        if path.startswith("/"):
            path = path[1:]
        out = self.output_dir / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        logger.debug(f"Generated: {out}")
