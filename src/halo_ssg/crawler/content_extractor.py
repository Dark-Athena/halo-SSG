from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup, Tag

from halo_ssg.models import FriendLink, Moment
from halo_ssg.exceptions import ExtractionError

logger = logging.getLogger("halo_ssg.crawler")


def _get_text(el: Tag | None) -> str:
    if el is None:
        return ""
    return el.get_text(strip=True)


class ContentExtractor:
    def extract_post_body(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        content = soup.select_one(".joe_detail__article")
        if not content:
            content = soup.select_one("article")
        if not content:
            content = soup.select_one(".joe_detail")
        if not content:
            logger.warning("Could not find post content with known selectors, trying fallback")
            main = soup.select_one("main") or soup.select_one(".joe_main")
            if main:
                return str(main)
            return ""

        # Remove unwanted elements
        for tag in content.select(".joe_detail__overdue, .joe_comment, .joe_post__pagination, .joe_detail__count, script, style"):
            tag.decompose()

        # Remove plugin link/style tags (vditor CSS, etc.)
        for link in content.select("link[href*='plugins/'], link[href*='vditor']"):
            link.decompose()

        # Remove vditor-specific divs
        for div in content.select("[data-type='sign'], [data-type='var']"):
            div.decompose()

        return str(content)

    def extract_post_title(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.select_one(".joe_detail__title")
        if title:
            return _get_text(title)
        h1 = soup.select_one("h1")
        return _get_text(h1)

    def extract_post_images(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.select("img"):
            src = img.get("data-src") or img.get("src") or ""
            if src and not src.startswith("data:") and "avatar" not in src.lower():
                images.append(src)
        return images

    def extract_moments(self, html: str) -> list[Moment]:
        soup = BeautifulSoup(html, "html.parser")
        moments = []
        for item in soup.select(".joe_journal__item"):
            content_el = item.select_one(".content-wrp") or item.select_one(".joe_journal_body")
            time_el = item.select_one(".joe_journal-posttime")
            content = str(content_el) if content_el else ""
            timestamp = _get_text(time_el) if time_el else ""
            moments.append(Moment(content=content, timestamp=timestamp))
        return moments

    def extract_links(self, html: str) -> list[FriendLink]:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for group in soup.select(".links-group"):
            group_title = group.select_one("h3") or group.select_one(".links-group-title")
            group_name = _get_text(group_title)
            for item in group.select(".joe_detail__friends-item"):
                anchor = item.select_one("a")
                if not anchor:
                    continue
                href = anchor.get("href", "")
                name_el = item.select_one(".sub-text") or item.select_one(".title")
                desc_el = item.select_one(".desc") or item.select_one(".content")
                avatar_el = item.select_one("img")
                links.append(FriendLink(
                    name=_get_text(name_el),
                    url=href,
                    description=_get_text(desc_el),
                    logo=avatar_el.get("data-src") or avatar_el.get("src", "") if avatar_el else "",
                    group=group_name,
                ))
        return links

    def extract_images_from_content(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        images = set()
        for img in soup.find_all("img"):
            src = img.get("data-src") or img.get("src") or ""
            if src and not src.startswith("data:"):
                images.add(src)
        return list(images)

    def extract_max_page(self, html: str) -> int:
        import re
        pages = re.findall(r'/page/(\d+)', html)
        if pages:
            return max(int(p) for p in pages)
        return 1
