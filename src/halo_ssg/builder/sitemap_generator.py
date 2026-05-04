from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from halo_ssg.models import Post, SinglePage, Category, Tag

logger = logging.getLogger("halo_ssg.builder")


def generate_sitemap(
    posts: list[Post],
    pages: list[SinglePage],
    categories: list[Category],
    tags: list[Tag],
    site_url: str,
    output_dir: Path,
) -> None:
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    _add_url(urlset, site_url, "/", priority="1.0")

    for post in posts:
        lastmod = post.last_modify_time.strftime("%Y-%m-%d") if post.last_modify_time else ""
        _add_url(urlset, site_url, post.permalink, lastmod=lastmod, priority="0.8")

    for page in pages:
        _add_url(urlset, site_url, page.permalink, priority="0.6")

    for cat in categories:
        _add_url(urlset, site_url, cat.permalink, priority="0.5")

    for tag in tags:
        _add_url(urlset, site_url, tag.permalink, priority="0.4")

    for extra in ["/archives/", "/tags/", "/moments/"]:
        _add_url(urlset, site_url, extra, priority="0.5")

    xml_str = parseString(tostring(urlset, encoding="unicode")).toprettyxml(indent="  ", encoding="utf-8")
    out = output_dir / "sitemap.xml"
    out.write_bytes(xml_str)
    logger.info(f"Generated sitemap: {out}")


def _add_url(urlset: Element, site_url: str, path: str, lastmod: str = "", priority: str = "0.5") -> None:
    url_el = SubElement(urlset, "url")
    SubElement(url_el, "loc").text = f"{site_url.rstrip('/')}{path}"
    if lastmod:
        SubElement(url_el, "lastmod").text = lastmod
    SubElement(url_el, "priority").text = priority
