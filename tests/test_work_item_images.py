"""Body-image transport tests: real SDK auth, MCP image content and bounded downloads."""

import asyncio
import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
import requests
from fastmcp import Client, FastMCP
from plane.api.work_items import WorkItems
from plane.config import Configuration

from plane_mcp.tools import work_item_images as images

PROJECT, ISSUE = str(uuid4()), str(uuid4())
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j6fQAAAAASUVORK5CYII=")
SIGNED_URL = "https://storage.example.com/private.png?signature=secret-signature"


@pytest.fixture
def transport(monkeypatch):
    resource = WorkItems(Configuration(base_path="https://plane.example.com", api_key="private-api-key"))
    metadata = {
        "image_index": 1,
        "asset_id": str(uuid4()),
        "name": "body.png",
        "available": True,
        "content_type": "image/jpeg",
        "download_url": SIGNED_URL,
        "expires_in": 3600,
    }
    response = MagicMock(status_code=200)
    response.__enter__.return_value = response
    response.json.return_value = metadata
    get = Mock(return_value=response)
    monkeypatch.setattr(resource.session, "get", get)
    monkeypatch.setattr(images, "get_plane_client_context", lambda: (SimpleNamespace(work_items=resource), "zili"))
    blob = MagicMock(status_code=200, headers={"Content-Type": "image/jpeg"})
    blob.__enter__.return_value = blob
    blob.iter_content.return_value = [PNG[:10], PNG[10:]]
    download = Mock(return_value=blob)
    monkeypatch.setattr(images.requests, "get", download)
    return SimpleNamespace(
        resource=resource, response=response, metadata=metadata, get=get, blob=blob, download=download
    )


def call_tool(name, **extra):
    async def run():
        mcp = FastMCP("body-image-test")
        images.register_work_item_image_tools(mcp)
        async with Client(mcp) as client:
            return await client.call_tool(name, {"project_id": PROJECT, "work_item_id": ISSUE, **extra})

    return asyncio.run(run())


def test_image_content_reaches_mcp_without_browser_auth(transport):
    result = call_tool("read_work_item_description_image", image_index=1)
    image = result.content[0]
    assert image.type == "image" and image.mimeType == "image/png"
    assert base64.b64decode(image.data) == PNG
    transport.get.assert_called_once_with(
        f"https://plane.example.com/api/v1/workspaces/zili/projects/{PROJECT}/work-items/{ISSUE}/description-images/1/",
        headers={"Content-Type": "application/json", "X-Api-Key": "private-api-key"},
        timeout=(10, 60),
        allow_redirects=False,
    )
    transport.download.assert_called_once_with(SIGNED_URL, timeout=(10, 60), stream=True, allow_redirects=False)
    transport.blob.__exit__.assert_called_once()


def test_list_images_uses_body_endpoint_not_attachments(transport):
    transport.response.json.return_value = [
        {k: v for k, v in transport.metadata.items() if k not in ["download_url", "expires_in"]}
    ]
    result = call_tool("list_work_item_description_images")
    assert result.structured_content["result"][0]["image_index"] == 1
    assert transport.get.call_args.args[0].endswith("/description-images/")
    transport.download.assert_not_called()


def test_download_url_tool_does_not_download_bytes(transport):
    result = call_tool("get_work_item_description_image_download_url", image_index=1)
    assert result.data["download_url"] == SIGNED_URL
    transport.download.assert_not_called()


@pytest.mark.parametrize("status", [302, 401, 403, 404, 500])
def test_api_failures_never_forward_credentials_or_download(transport, status):
    transport.response.status_code = status
    with pytest.raises(ValueError, match=f"HTTP {status}"):
        images._description_images_request(PROJECT, ISSUE, 1)
    assert transport.get.call_args.kwargs["allow_redirects"] is False
    transport.download.assert_not_called()


def test_declared_oversized_image_is_not_read(transport):
    transport.blob.headers["Content-Length"] = str(images._IMAGE_LIMIT + 1)
    with pytest.raises(ValueError, match="5 MB"):
        images._download_image(SIGNED_URL)
    transport.blob.iter_content.assert_not_called()
    transport.blob.__exit__.assert_called_once()


def test_streaming_limit_applies_when_content_length_is_missing(transport):
    transport.blob.iter_content.return_value = [b"x" * images._IMAGE_LIMIT, b"x"]
    with pytest.raises(ValueError, match="5 MB"):
        images._download_image(SIGNED_URL)
    transport.blob.__exit__.assert_called_once()


@pytest.mark.parametrize("payload", [b"<html>Sign in</html>", b"<svg></svg>", b""])
def test_html_or_unsupported_content_is_not_returned_as_image(transport, payload):
    transport.blob.iter_content.return_value = [payload]
    with pytest.raises(ValueError, match="not a supported"):
        images._download_image(SIGNED_URL)


def test_storage_redirect_is_not_followed(transport):
    transport.blob.status_code = 302
    with pytest.raises(ValueError, match="HTTP 302"):
        images._download_image(SIGNED_URL)
    transport.blob.iter_content.assert_not_called()


def test_network_error_does_not_expose_signed_url(transport):
    transport.download.side_effect = requests.ConnectionError(SIGNED_URL)
    with pytest.raises(ValueError) as error:
        images._download_image(SIGNED_URL)
    assert "secret-signature" not in str(error.value)
    assert SIGNED_URL not in str(error.value)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "https://user:password@example.com/image", "/relative.png"])
def test_invalid_storage_urls_are_not_requested(transport, url):
    with pytest.raises(ValueError, match="invalid image download URL"):
        images._download_image(url)
    transport.download.assert_not_called()


def test_invalid_index_or_ids_do_not_make_api_requests(transport):
    for project, item, index in [(PROJECT, ISSUE, 0), ("not-uuid", ISSUE, 1), (PROJECT, "../../users", 1)]:
        with pytest.raises(ValueError):
            images._description_images_request(project, item, index)
    transport.get.assert_not_called()


def test_all_three_tools_are_registered():
    async def run():
        mcp = FastMCP("body-image-schema")
        images.register_work_item_image_tools(mcp)
        async with Client(mcp) as client:
            return await client.list_tools()

    tools = {tool.name: tool.inputSchema for tool in asyncio.run(run())}
    assert set(tools) == {
        "list_work_item_description_images",
        "read_work_item_description_image",
        "get_work_item_description_image_download_url",
    }
    assert "image_index" in tools["read_work_item_description_image"]["required"]
    assert "image_index" not in tools["list_work_item_description_images"]["properties"]
