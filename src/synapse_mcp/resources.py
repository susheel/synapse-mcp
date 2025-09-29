"""Resource registrations for Synapse MCP."""

from datetime import datetime, timezone

import requests

from .app import mcp


BLOG_FEED_URL = "https://sagebionetworks.pubpub.org/rss.xml"


@mcp.resource(
    "synapse://feeds/blog",
    name="Sage Blog RSS",
    title="Latest Sage Bionetworks Blog Posts",
    description="Returns the live RSS XML from the Sage Bionetworks publication feed.",
    mime_type="application/rss+xml",
)
def synapse_blog_feed() -> str:
    """Fetch the latest Sage Bionetworks publication feed as raw XML."""

    try:
        response = requests.get(BLOG_FEED_URL, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:  # pragma: no cover - network failure fallback
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        detail = str(exc).replace("<", "&lt;").replace(">", "&gt;")
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<feed-error>\n"
            f"  <fetched-at>{timestamp}</fetched-at>\n"
            "  <message>Unable to fetch Sage Bionetworks RSS feed.</message>\n"
            f"  <detail>{detail}</detail>\n"
            "</feed-error>"
        )


__all__ = ["synapse_blog_feed"]
