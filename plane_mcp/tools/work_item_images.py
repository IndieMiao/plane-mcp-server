"""Read images embedded in work-item descriptions without a browser session."""

from typing import Any
from urllib.parse import quote, urlsplit
from uuid import UUID

import requests
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from plane_mcp.client import get_plane_client_context

_IMAGE_LIMIT = 5 * 1024 * 1024
_TIMEOUT = (10, 60)


def _description_images_request(project_id: str, work_item_id: str, image_index: int | None = None) -> Any:
    project_id, work_item_id = str(UUID(project_id)), str(UUID(work_item_id))
    if image_index is not None and image_index < 1:
        raise ValueError("image_index starts at 1; use list_work_item_description_images first.")
    client, workspace_slug = get_plane_client_context()
    resource = client.work_items
    endpoint = f"{quote(workspace_slug, safe='')}/projects/{project_id}/work-items/{work_item_id}/description-images"
    if image_index is not None:
        endpoint += f"/{image_index}"
    try:
        # This API returns JSON, not a redirect. Never forward its auth headers to storage.
        with resource.session.get(
            resource._build_url(endpoint), headers=resource._headers(), timeout=_TIMEOUT, allow_redirects=False
        ) as response:
            if response.status_code != 200:
                raise ValueError(
                    f"Plane description-image API returned HTTP {response.status_code}. "
                    "Check task access, the image index, and that the updated backend is deployed."
                )
            data = response.json()
    except requests.RequestException:
        raise ValueError("Unable to query the Plane description-image API.") from None
    if image_index is None and not isinstance(data, list):
        raise ValueError("The backend returned an invalid description-image list.")
    if image_index is not None and (not isinstance(data, dict) or not data.get("download_url")):
        raise ValueError("The backend did not return a description-image download URL.")
    return data


def _download_image(url: str) -> Image:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("The backend returned an invalid image download URL.")
    try:
        # A new request has neither the SDK's API key nor browser session cookies.
        with requests.get(url, timeout=_TIMEOUT, stream=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError(f"Image storage returned HTTP {response.status_code}; request a fresh image URL.")
            try:
                size = int(response.headers.get("Content-Length", "0"))
            except ValueError:
                size = 0
            if size > _IMAGE_LIMIT:
                raise ValueError("The image exceeds the 5 MB reading limit; use the image download URL tool.")
            data = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if len(data) + len(chunk) > _IMAGE_LIMIT:
                    raise ValueError("The image exceeds the 5 MB reading limit; use the image download URL tool.")
                data.extend(chunk)
    except requests.RequestException:
        # Exception text may contain the signed URL; do not leak it into error logs.
        raise ValueError("Unable to download the image from storage.") from None

    image = bytes(data)
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        format_name = "png"
    elif image.startswith(b"\xff\xd8\xff"):
        format_name = "jpeg"
    elif image.startswith((b"GIF87a", b"GIF89a")):
        format_name = "gif"
    elif image.startswith(b"RIFF") and image[8:12] == b"WEBP":
        format_name = "webp"
    else:
        raise ValueError("The resource is not a supported PNG, JPEG, GIF or WebP image.")
    return Image(data=image, format=format_name)


def register_work_item_image_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def list_work_item_description_images(project_id: str, work_item_id: str) -> list[dict[str, Any]]:
        """List images embedded in a work item's body, in document order.

        These images are separate from work-item attachments. Supports Plane's
        image-component UUIDs and img elements referencing this task's Plane assets.
        Returns image_index (starts at 1), asset_id, name, alt, content_type, size,
        and available. External, missing, deleted or out-of-scope assets are unavailable.
        Uses the configured Plane credentials; browser login is unnecessary.
        """
        return _description_images_request(project_id, work_item_id)

    @mcp.tool()
    def get_work_item_description_image_download_url(
        project_id: str, work_item_id: str, image_index: int
    ) -> dict[str, Any]:
        """Get a temporary signed URL for a body image, after checking task access.

        Use list_work_item_description_images to choose its 1-based image_index.
        Returns image metadata, download_url and expires_in (seconds). The signed
        URL works without a browser login until expiry; it is not a permanent link.
        Never send Plane API credentials when downloading from that URL.
        """
        return _description_images_request(project_id, work_item_id, image_index)

    @mcp.tool()
    def read_work_item_description_image(project_id: str, work_item_id: str, image_index: int) -> Image:
        """Return a body image as MCP image content so the agent can see it.

        First list_work_item_description_images, then pass its 1-based image_index.
        Supports PNG/JPEG/GIF/WebP up to 5 MB. The server authenticates with the
        configured Plane credentials; no browser login or manual asset URL is needed.
        Read the image soon after listing because editing the body can change indices.
        """
        metadata = _description_images_request(project_id, work_item_id, image_index)
        return _download_image(metadata["download_url"])
