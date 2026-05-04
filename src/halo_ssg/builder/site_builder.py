from __future__ import annotations

import logging
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from halo_ssg.config import Config
from halo_ssg.api.halo_client import HaloClient
from halo_ssg.crawler.page_fetcher import PageFetcher
from halo_ssg.crawler.content_extractor import ContentExtractor
from halo_ssg.crawler.asset_downloader import AssetDownloader
from halo_ssg.sync.state import SyncState
from halo_ssg.utils.hash import content_hash
from halo_ssg.builder.page_generator import PageGenerator
from halo_ssg.builder.index_generator import IndexGenerator
from halo_ssg.builder.rss_generator import generate_rss
from halo_ssg.builder.sitemap_generator import generate_sitemap

logger = logging.getLogger("halo_ssg")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class SiteBuilder:
    def __init__(self, config: Config):
        self.cfg = config
        self.output_dir = config.output.dir.resolve()
        self.state = SyncState(config.sync.state_file)
        self.extractor = ContentExtractor()
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=False,
        )
        self.site_context = {
            "title": config.site.title,
            "description": config.site.description,
            "author": config.site.author,
            "language": config.site.language,
            "base": config.deploy.base_path.rstrip("/"),
        }

    def run(self, force: bool = False) -> None:
        logger.info("Starting sync...")
        if force:
            logger.info("Force mode: will re-crawl everything.")

        if self.output_dir.exists() and self.cfg.output.clean_before_build:
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        with HaloClient(self.cfg.site.base_url, self.cfg.crawl.timeout, self.cfg.crawl.user_agent) as api:
            posts = api.fetch_posts()
            categories = api.fetch_categories()
            tags = api.fetch_tags()
            single_pages = api.fetch_single_pages()

        # Filter out skipped pages
        single_pages = [p for p in single_pages if p.slug not in self.SKIP_SLUGS]

        with PageFetcher(
            self.cfg.site.base_url,
            rate_limit=self.cfg.crawl.rate_limit,
            timeout=self.cfg.crawl.timeout,
            max_retries=self.cfg.crawl.max_retries,
            user_agent=self.cfg.crawl.user_agent,
            concurrency=self.cfg.crawl.concurrency,
        ) as fetcher:
            self._crawl_posts(posts, fetcher, force)
            self._crawl_single_pages(single_pages, fetcher, force)
            moments = self._crawl_moments(fetcher)

        self._download_assets(posts, single_pages, moments)
        self._build(posts, categories, tags, single_pages, [], moments)
        self.state.save()
        logger.info("Sync complete!")

    def build_only(self) -> None:
        logger.info("Building from cached data...")
        if not self.output_dir.exists():
            logger.error("Output directory does not exist. Run 'sync' first.")
            return
        # TODO: load cached data from state and rebuild templates
        logger.info("Build complete!")

    def _crawl_posts(self, posts, fetcher: PageFetcher, force: bool) -> None:
        # Determine which posts need crawling
        to_crawl = []
        for post in posts:
            last_mod = post.last_modify_time.isoformat() if post.last_modify_time else ""
            if not force and not self.state.needs_update(post.slug, last_mod, "post"):
                cached_hash = self.state.get_post_hash(post.slug)
                if cached_hash:
                    post.content_hash = cached_hash
                    continue
            to_crawl.append(post)

        if not to_crawl:
            logger.info("All posts up to date.")
            return

        logger.info(f"Crawling {len(to_crawl)} posts with concurrency={fetcher.concurrency}...")
        paths = [p.permalink for p in to_crawl]
        path_to_post = {p.permalink: p for p in to_crawl}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("Crawling posts...", total=len(to_crawl))
            results = fetcher.fetch_many(paths, progress_callback=lambda: progress.advance(task))

        for path, html in results.items():
            post = path_to_post[path]
            last_mod = post.last_modify_time.isoformat() if post.last_modify_time else ""
            if html:
                post.html_body = self.extractor.extract_post_body(html)
                post.content_hash = content_hash(post.html_body)
                self.state.set_post_hash(post.slug, post.content_hash, last_mod)
            else:
                logger.warning(f"Empty response for post: {post.slug}")

    def _crawl_single_pages(self, pages, fetcher: PageFetcher, force: bool) -> None:
        for page in pages:
            if not force and self.state.get_page_hash(page.slug):
                page.content_hash = self.state.get_page_hash(page.slug)
                continue
            html = fetcher.fetch(page.permalink)
            if html:
                page.html_body = self.extractor.extract_post_body(html)
                page.content_hash = content_hash(page.html_body)
                self.state.set_page_hash(page.slug, page.content_hash)

    def _crawl_links(self, fetcher: PageFetcher) -> list:
        from halo_ssg.models import FriendLink
        html = fetcher.fetch("/links")
        if html:
            return self.extractor.extract_links(html)
        return []

    def _crawl_moments(self, fetcher: PageFetcher) -> list:
        from halo_ssg.models import Moment
        html = fetcher.fetch("/moments")
        if not html:
            return []

        all_moments = self.extractor.extract_moments(html)
        max_page = self.extractor.extract_max_page(html)
        if max_page > 1:
            logger.info(f"Crawling {max_page} pages of moments...")
            for page_num in range(2, max_page + 1):
                page_html = fetcher.fetch(f"/moments/page/{page_num}")
                if page_html:
                    all_moments.extend(self.extractor.extract_moments(page_html))

        logger.info(f"Fetched {len(all_moments)} moments from {max_page} pages.")
        return all_moments

    def _download_assets(self, posts, pages, moments=None, links=None) -> None:
        all_images = set()
        for post in posts:
            if post.html_body:
                for img in self.extractor.extract_images_from_content(post.html_body):
                    all_images.add(img)
        for page in pages:
            if page.html_body:
                for img in self.extractor.extract_images_from_content(page.html_body):
                    all_images.add(img)
        if moments:
            for moment in moments:
                if moment.content:
                    for img in self.extractor.extract_images_from_content(moment.content):
                        all_images.add(img)
        if links:
            for link in links:
                if link.logo and not link.logo.startswith("data:"):
                    all_images.add(link.logo)

        if not all_images:
            return

        logger.info(f"Downloading {len(all_images)} assets...")
        with AssetDownloader(
            self.cfg.site.base_url,
            self.output_dir,
            timeout=self.cfg.crawl.timeout,
            max_size_mb=self.cfg.assets.max_image_size_mb,
            user_agent=self.cfg.crawl.user_agent,
        ) as downloader:
            mapping = downloader.download_assets(list(all_images))

        base = self.cfg.site.base_url.rstrip("/")
        for post in posts:
            if post.html_body:
                post.html_body = self._rewrite_urls(post.html_body, mapping, base)
        for page in pages:
            if page.html_body:
                page.html_body = self._rewrite_urls(page.html_body, mapping, base)
        if moments:
            for moment in moments:
                if moment.content:
                    moment.content = self._rewrite_urls(moment.content, mapping, base)

    def _rewrite_urls(self, html: str, mapping: dict, base_url: str) -> str:
        base_path = self.site_context.get("base", "")
        for original, local in mapping.items():
            local_with_base = f"{base_path}{local}" if base_path else local
            if original.startswith(base_url):
                html = html.replace(original, local_with_base)
            elif original.startswith("/"):
                # Also replace the relative path itself (not just the full URL)
                html = html.replace(original, local_with_base)
                full = f"{base_url}{original}"
                html = html.replace(full, local_with_base)
        return html

    # Pages to skip (user disabled)
    SKIP_SLUGS = {"about", "DBeaver-doc-zh", "classicqa"}

    def _build(self, posts, categories, tags, single_pages, links, moments) -> None:
        page_gen = PageGenerator(self.env, self.output_dir)
        index_gen = IndexGenerator(self.env, self.output_dir)

        sorted_posts = sorted(posts, key=lambda p: p.publish_time or p.publish_time, reverse=True)

        index_gen.generate_home(sorted_posts, self.site_context)
        index_gen.generate_archives(sorted_posts, self.site_context)
        index_gen.generate_tags(tags, self.site_context)

        posts_by_tag = {}
        for post in posts:
            for tag in post.tags:
                posts_by_tag.setdefault(tag.slug, []).append(post)
        for tag in tags:
            tag_posts = sorted(
                posts_by_tag.get(tag.slug, []),
                key=lambda p: p.publish_time or p.publish_time,
                reverse=True,
            )
            index_gen.generate_tag(tag, tag_posts, self.site_context)

        for i, post in enumerate(sorted_posts):
            prev_post = sorted_posts[i - 1] if i > 0 else None
            next_post = sorted_posts[i + 1] if i < len(sorted_posts) - 1 else None
            page_gen.generate_post(post, prev_post, next_post, self.site_context)

        for page in single_pages:
            if page.slug not in self.SKIP_SLUGS:
                page_gen.generate_single_page(page, self.site_context)

        if moments:
            index_gen.generate_moments(moments, self.site_context)

        page_gen.generate_error(self.site_context)

        generate_rss(
            sorted_posts,
            self.cfg.site.base_url,
            self.cfg.site.title,
            self.cfg.site.description,
            self.output_dir,
        )
        generate_sitemap(posts, single_pages, categories, tags, self.cfg.site.base_url, self.output_dir)

        logger.info(f"Generated {len(sorted_posts)} posts, {len(single_pages)} pages, "
                    f"{len(categories)} categories, {len(tags)} tags")
