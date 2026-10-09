"""Verify delegated identities survive MCP schemas and real SDK HTTP serialization."""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastmcp import Client, FastMCP
from plane.api.pages import Pages
from plane.api.work_items import WorkItems
from plane.config import Configuration

from plane_mcp.tools import pages, work_item_attachments, work_item_links, work_items

MODULES = [work_items, work_item_links, pages, work_item_attachments]
CASES = [
    ("create_work_item", {"project_id": "p", "name": "Card", "parent": "parent"}, "post"),
    ("update_work_item", {"project_id": "p", "work_item_id": "i", "state": "done", "priority": "high"}, "patch"),
    ("manage_work_item_assignee", {"project_id": "p", "work_item_id": "i", "add_user_id": "assignee"}, "patch"),
    ("manage_work_item_label", {"project_id": "p", "work_item_id": "i", "remove_label_id": "old-label"}, "patch"),
    ("create_work_item_link", {"project_id": "p", "work_item_id": "i", "url": "https://example.com"}, "post"),
    (
        "update_work_item_link",
        {"project_id": "p", "work_item_id": "i", "link_id": "l", "url": "https://example.com/new"},
        "patch",
    ),
    ("delete_work_item_link", {"project_id": "p", "work_item_id": "i", "link_id": "l"}, "delete"),
    ("create_page", {"project_id": "p", "name": "Design", "description_html": "<p>Plan</p>"}, "post"),
    ("update_page", {"project_id": "p", "page_id": "d", "description_html": "<p>Final</p>"}, "patch"),
    ("rename_page", {"project_id": "p", "page_id": "d", "name": "Final design"}, "patch"),
    ("delete_work_item_attachment", {"project_id": "p", "work_item_id": "i", "attachment_id": "a"}, "delete"),
]


def _register(mcp):
    work_items.register_work_item_tools(mcp)
    work_item_links.register_work_item_link_tools(mcp)
    pages.register_page_tools(mcp)
    work_item_attachments.register_work_item_attachment_tools(mcp)


def _call(name, arguments):
    async def run():
        mcp = FastMCP("attribution-tests")
        _register(mcp)
        async with Client(mcp) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(run())


@pytest.fixture
def transport(monkeypatch):
    config = Configuration(base_path="https://plane.example.com", api_key="test-key")
    client = SimpleNamespace(work_items=WorkItems(config), pages=Pages(config))
    calls = []

    def request(verb, url, **kwargs):
        calls.append((verb, url, kwargs))
        data = {
            "id": "i",
            "name": "Card",
            "assignees": ["existing"],
            "labels": ["old-label"],
            "url": "https://example.com",
        }
        if verb == "post" and url.endswith("/attachments/"):
            data = {
                "asset_id": "a",
                "upload_data": {"url": "https://uploads.example.com", "fields": {"key": "upload-key"}},
                "attachment": {
                    "id": "a",
                    "asset": "workspace/report.txt",
                    "attributes": {"name": "report.txt", "type": "text/plain", "size": 6},
                },
            }
        response = Mock(
            status_code=204 if verb == "delete" else 200, content=b"{}", headers={"content-type": "application/json"}
        )
        response.json.return_value = data
        return response

    for resource in [client.work_items, client.work_items.links, client.work_items.attachments, client.pages]:
        for verb in ["get", "post", "patch", "delete"]:
            monkeypatch.setattr(resource.session, verb, lambda url, _verb=verb, **kw: request(_verb, url, **kw))
    for module in MODULES:
        monkeypatch.setattr(module, "get_plane_client_context", lambda: (client, "community"))
    return calls


@pytest.mark.parametrize("delegated", [False, True])
@pytest.mark.parametrize("name,arguments,verb", CASES)
def test_action_identity_reaches_api(monkeypatch, transport, name, arguments, verb, delegated):
    identity = {"virtual_user_id": "agent-identity"} if delegated else {}
    _call(name, {**arguments, **identity})
    writes = [call for call in transport if call[0] == verb]
    assert len(writes) == 1
    _, url, kwargs = writes[0]
    assert url.startswith("https://plane.example.com/api/v1/workspaces/community/projects/p/")
    payload = kwargs.get("json") or {}
    assert payload.get("virtual_user_id") == identity.get("virtual_user_id")
    if not delegated:
        assert "virtual_user_id" not in payload
    if name == "manage_work_item_assignee":
        assert payload["assignees"] == ["existing", "assignee"]
    if name == "manage_work_item_label":
        assert payload["labels"] == []


@pytest.mark.parametrize("delegated", [False, True])
def test_attachment_three_step_upload_keeps_identity_off_storage(monkeypatch, transport, delegated):
    monkeypatch.setattr(work_item_attachments, "_assert_public_url", lambda url: None)
    source = Mock(content=b"report", headers={"Content-Type": "text/plain"})
    monkeypatch.setattr(work_item_attachments._requests, "get", Mock(return_value=source))
    upload = Mock(return_value=Mock())
    monkeypatch.setattr(work_item_attachments._requests, "post", upload)
    identity = {"virtual_user_id": "agent-identity"} if delegated else {}
    _call(
        "upload_work_item_attachment_from_url",
        {"project_id": "p", "work_item_id": "i", "url": "https://source.example.com/report.txt", **identity},
    )
    writes = [call for call in transport if call[0] in ["post", "patch"]]
    assert [call[0] for call in writes] == ["post", "patch"]
    for _, _, kwargs in writes:
        assert kwargs["json"].get("virtual_user_id") == identity.get("virtual_user_id")
    assert upload.call_args.args == ("https://uploads.example.com",)
    assert upload.call_args.kwargs["data"] == {"key": "upload-key"}
    assert "headers" not in upload.call_args.kwargs
    assert "virtual_user_id" not in upload.call_args.kwargs["data"]


def test_only_selected_actions_expose_optional_identity():
    async def schemas():
        mcp = FastMCP("attribution-schema")
        _register(mcp)
        async with Client(mcp) as client:
            return {tool.name: tool.inputSchema for tool in await client.list_tools()}

    tools = asyncio.run(schemas())
    for name in [case[0] for case in CASES] + ["upload_work_item_attachment_from_url"]:
        assert "virtual_user_id" in tools[name]["properties"]
        assert "virtual_user_id" not in tools[name].get("required", [])
    for name in ["delete_work_item", "delete_page", "attach_page_to_work_item", "retrieve_work_item"]:
        assert "virtual_user_id" not in tools[name]["properties"]
