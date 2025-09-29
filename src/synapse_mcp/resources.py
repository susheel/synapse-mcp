"""Static resource registrations for Synapse MCP."""

from textwrap import dedent
from datetime import datetime, timezone

import requests

from .app import mcp


BLOG_FEED_URL = "https://sagebionetworks.pubpub.org/rss.xml"


@mcp.resource(
    "synapse://guides/user-account-types",
    name="Synapse Account Types",
    title="Synapse User Account Types",
    description="Highlights the Synapse user account types and their capabilities.",
    mime_type="text/markdown",
)
def synapse_user_account_types() -> str:
    """Return guidance mirroring the Synapse help docs on account types."""

    return dedent(
        """
        # Synapse User Account Types

        Synapse governance distinguishes four account types. Each tier inherits the privileges of the preceding tier and unlocks additional capabilities.

        ## Anonymous User
        - Browse public projects, files, tables, and wiki pages without signing in.
        - Cannot create projects, download non-public data, upload content, or post in discussions.

        ## Registered User
        - Can create projects and wiki pages, collaborate with other registered users, and manage Synapse teams.
        - May download publicly available data and, when project-specific Conditions for Use are satisfied, access controlled data.
        - Sign up at https://accounts.synapse.org/register1?appId=synapse.org.

        ## Certified User
        - Gains full Synapse functionality: upload files and tables, create folders, add provenance, and upload Docker containers.
        - Certification requires passing the 15-question Synapse Commons Data Use Procedure quiz (https://www.synapse.org/#!Quiz:Certification).

        ## Validated User
        - Eligible to request access to controlled access tiers (for example mHealth or Bridge datasets).
        - Validation steps (performed from **Settings → Profile Validation**) include:
          1. Ensure the profile lists full name, current affiliation, and city/country.
          2. Link a public ORCID profile containing at least one additional data point.
          3. Submit the Synapse Pledge.
          4. Provide identity attestation (signing-official letter, notarized letter, or professional license copy dated within the last month).
        - A validation badge appears on the profile once the Governance team completes review.

        ### Key Capabilities by Account Type for Synapse.org
        | Capability | Anonymous | Registered | Certified | Validated |
        | --- | --- | --- | --- | --- |
        | View public wiki pages | Yes | Yes | Yes | Yes |
        | Browse public project catalog | Yes | Yes | Yes | Yes |
        | Browse public file catalog | Yes | Yes | Yes | Yes |
        | Create projects and wikis | No | Yes | Yes | Yes |
        | Download files or tables* | No | Yes | Yes | Yes |
        | Upload files, tables, folders, provenance, Docker | No | No | Yes | Yes |
        | Request controlled access data** | No | No | No | Yes |

        \* Download access also depends on local sharing settings and fulfilling any Conditions for Use attached to the asset.

        \** Click **Request Access** on the dataset to review whether certification and/or validation is required.

        ### Group Membership Notes
        - **Anonymous**: Default state; no group membership.
        - **Registered Synapse Users** group tracks registered accounts automatically after sign-up.
        - **Certified Users** group enrollment occurs automatically once the certification quiz is passed.
        - **Validated Users** group membership is granted by the Synapse Governance team after reviewing validation materials.

        Regardless of account type, every user must follow the Synapse Terms and Conditions of Use and broader governance policies. Questions can be directed to the Synapse Access and Compliance Team (act@synapse.org).

        _Source: Synapse Help Docs — "Synapse User Account Types" (retrieved {source_date})._
        """
    ).strip().format(source_date="2024-09-05")


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


__all__ = [
    "synapse_user_account_types",
    "synapse_blog_feed",
]
