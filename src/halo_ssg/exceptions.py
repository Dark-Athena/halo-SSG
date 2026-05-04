class HaloSSGError(Exception):
    """Base exception for halo-ssg."""

class ConfigError(HaloSSGError):
    """Configuration error."""

class APIError(HaloSSGError):
    """Halo API communication error."""

class CrawlError(HaloSSGError):
    """Page crawling error."""

class ExtractionError(HaloSSGError):
    """Content extraction error."""
