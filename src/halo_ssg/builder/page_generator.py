from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from halo_ssg.models import Post, SinglePage

logger = logging.getLogger("halo_ssg.builder")


class PageGenerator:
    def __init__(self, env: Environment, output_dir: Path):
        self.env = env
        self.output_dir = output_dir

    def generate_post(self, post: Post, prev_post: Post | None = None, next_post: Post | None = None,
                      site_context: dict | None = None) -> None:
        ctx = {
            "post": post,
            "prev_post": prev_post,
            "next_post": next_post,
            **(site_context or {}),
        }
        html = self.env.get_template("post.html").render(ctx)
        self._write(post.permalink, html)

    def generate_single_page(self, page: SinglePage, site_context: dict | None = None) -> None:
        ctx = {"page": page, **(site_context or {})}
        html = self.env.get_template("page.html").render(ctx)
        self._write(page.permalink, html)

    def generate_error(self, site_context: dict | None = None) -> None:
        html = self.env.get_template("error.html").render(site_context or {})
        out = self.output_dir / "404.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    def _write(self, permalink: str, html: str) -> None:
        path = permalink.strip("/")
        if not path:
            out = self.output_dir / "index.html"
        else:
            out = self.output_dir / path / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        logger.debug(f"Generated: {out}")
