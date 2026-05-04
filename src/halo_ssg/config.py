from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from halo_ssg.exceptions import ConfigError

DEFAULTS = {
    "site": {
        "base_url": "https://www.darkathena.top",
        "title": "DA-技术分享",
        "description": "Database & Tech Blog",
        "author": "DarkAthena",
        "language": "zh-CN",
    },
    "output": {
        "dir": "./output",
        "clean_before_build": True,
    },
    "crawl": {
        "rate_limit": 2.0,
        "timeout": 30,
        "max_retries": 3,
        "user_agent": "Halo-SSG/1.0",
        "concurrency": 5,
    },
    "assets": {
        "download_images": True,
        "max_image_size_mb": 10,
    },
    "sync": {
        "state_file": "./state/sync_state.json",
    },
    "deploy": {
        "method": "gh-pages",
        "branch": "gh-pages",
        "cname": "",
        "base_path": "",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class SiteConfig:
    base_url: str
    title: str
    description: str
    author: str
    language: str


@dataclass
class OutputConfig:
    dir: Path
    clean_before_build: bool


@dataclass
class CrawlConfig:
    rate_limit: float
    timeout: int
    max_retries: int
    user_agent: str
    concurrency: int = 5


@dataclass
class AssetConfig:
    download_images: bool
    max_image_size_mb: int


@dataclass
class SyncConfig:
    state_file: Path


@dataclass
class DeployConfig:
    method: str
    branch: str
    cname: str
    base_path: str


@dataclass
class Config:
    site: SiteConfig
    output: OutputConfig
    crawl: CrawlConfig
    assets: AssetConfig
    sync: SyncConfig
    deploy: DeployConfig


def load_config(path: str | Path = "config.yaml") -> Config:
    path = Path(path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
    else:
        user_cfg = {}

    cfg = _deep_merge(DEFAULTS, user_cfg)

    try:
        return Config(
            site=SiteConfig(**cfg["site"]),
            output=OutputConfig(
                dir=Path(cfg["output"]["dir"]),
                clean_before_build=cfg["output"]["clean_before_build"],
            ),
            crawl=CrawlConfig(**cfg["crawl"]),
            assets=AssetConfig(**cfg["assets"]),
            sync=SyncConfig(state_file=Path(cfg["sync"]["state_file"])),
            deploy=DeployConfig(**cfg["deploy"]),
        )
    except (KeyError, TypeError) as e:
        raise ConfigError(f"Invalid configuration: {e}") from e
