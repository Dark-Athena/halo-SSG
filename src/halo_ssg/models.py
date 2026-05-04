from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CategoryRef:
    name: str
    display_name: str
    slug: str
    permalink: str


@dataclass
class TagRef:
    name: str
    display_name: str
    slug: str
    permalink: str


@dataclass
class Post:
    name: str
    title: str
    slug: str
    permalink: str
    publish_time: datetime | None = None
    last_modify_time: datetime | None = None
    excerpt: str = ""
    cover: str = ""
    categories: list[CategoryRef] = field(default_factory=list)
    tags: list[TagRef] = field(default_factory=list)
    visit_count: int = 0
    content_hash: str = ""
    html_body: str = ""


@dataclass
class Category:
    name: str
    display_name: str
    slug: str
    description: str = ""
    post_count: int = 0
    children: list[str] = field(default_factory=list)
    permalink: str = ""


@dataclass
class Tag:
    name: str
    display_name: str
    slug: str
    color: str = ""
    post_count: int = 0
    permalink: str = ""


@dataclass
class SinglePage:
    name: str
    title: str
    slug: str
    permalink: str
    excerpt: str = ""
    content_hash: str = ""
    html_body: str = ""


@dataclass
class Moment:
    content: str = ""
    timestamp: str = ""


@dataclass
class FriendLink:
    name: str = ""
    url: str = ""
    description: str = ""
    logo: str = ""
    group: str = ""
