"""MCP transport and real SDK serialization tests for virtual comment authors."""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

from fastmcp import Client, FastMCP
from plane.api.work_items.comments import WorkItemComments
from plane.config import Configuration

from plane_mcp.tools import work_item_comments


def _call(monkeypatch, name, arguments):
    resource = WorkItemComments(Configuration(base_path="https://plane.example.com", api_key="test-api-key"))
    response = Mock(status_code=201, content=b"{}", headers={"content-type": "application/json"})
    response.json.return_value = {
        "id": "comment-1",
        "actor": arguments.get("virtual_user_id", "real-user"),
        "created_by": "real-user",
        "comment_html": arguments.get("comment_html"),
    }
    post = Mock(return_value=response)
    monkeypatch.setattr(resource.session, "post", post)
    client = SimpleNamespace(work_items=SimpleNamespace(comments=resource))
    monkeypatch.setattr(work_item_comments, "get_plane_client_context", lambda: (client, "community"))

    async def run():
        mcp = FastMCP("test")
        work_item_comments.register_work_item_comment_tools(mcp)
        async with Client(mcp) as mcp_client:
            return await mcp_client.call_tool(name, arguments)

    return asyncio.run(run()), post


def test_virtual_identity_survives_mcp_and_sdk_serialization(monkeypatch):
    result, post = _call(
        monkeypatch,
        "create_work_item_comment",
        {
            "project_id": "project-1",
            "work_item_id": "issue-1",
            "virtual_user_id": "virtual-user-1",
            "comment_html": "<p>开发完成</p>",
            "comment_json": {"type": "doc"},
            "access": "INTERNAL",
            "external_source": "agent",
            "external_id": "run-1",
        },
    )
    post.assert_called_once_with(
        "https://plane.example.com/api/v1/workspaces/community/projects/project-1/work-items/issue-1/comments/",
        headers={"Content-Type": "application/json", "X-Api-Key": "test-api-key"},
        json={
            "virtual_user_id": "virtual-user-1",
            "comment_html": "<p>开发完成</p>",
            "comment_json": {"type": "doc"},
            "access": "INTERNAL",
            "external_source": "agent",
            "external_id": "run-1",
        },
        params=None,
        timeout=30.0,
    )
    assert result.data.actor == "virtual-user-1"
    assert result.data.created_by == "real-user"


def test_existing_calls_omit_virtual_identity(monkeypatch):
    result, post = _call(
        monkeypatch,
        "create_work_item_comment",
        {"project_id": "project-1", "work_item_id": "issue-1", "comment_html": "<p>Human comment</p>"},
    )
    assert post.call_args.kwargs["json"] == {"comment_html": "<p>Human comment</p>"}
    assert result.data.actor == "real-user"


def test_tool_schema_exposes_optional_virtual_user_id():
    async def run():
        mcp = FastMCP("test")
        work_item_comments.register_work_item_comment_tools(mcp)
        async with Client(mcp) as client:
            return await client.list_tools()

    tools = {tool.name: tool for tool in asyncio.run(run())}
    schema = tools["create_work_item_comment"].inputSchema
    assert "virtual_user_id" in schema["properties"]
    assert "virtual_user_id" not in schema["required"]
    assert "virtual_user_id" not in tools["update_work_item_comment"].inputSchema["properties"]
