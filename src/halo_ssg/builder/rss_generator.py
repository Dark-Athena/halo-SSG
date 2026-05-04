from __future__ import annotations

import logging
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from halo_ssg.models import Post

logger = logging.getLogger("halo_ssg.builder")


def generate_rss(posts: list[Post], site_url: str, title: str, description: str, output_dir: Path) -> None:
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = title
    SubElement(channel, "link").text = site_url
    SubElement(channel, "description").text = description
    SubElement(channel, "language").text = "zh-CN"

    sorted_posts = sorted(posts, key=lambda p: p.publish_time or p.publish_time, reverse=True)
    for post in sorted_posts[:50]:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = post.title
        SubElement(item, "link").text = f"{site_url}{post.permalink}"
        SubElement(item, "description").text = post.excerpt or post.title
        if post.publish_time:
            SubElement(item, "pubDate").text = post.publish_time.strftime("%a, %d %b %Y %H:%M:%S +0000")
        for cat in post.categories:
            SubElement(item, "category").text = cat.display_name

    xml_str = parseString(tostring(rss, encoding="unicode")).toprettyxml(indent="  ", encoding="utf-8")
    out = output_dir / "rss.xml"
    out.write_bytes(xml_str)
    logger.info(f"Generated RSS: {out}")
