"""Offline MCP transport tests for Community Edition virtual identities."""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

from fastmcp import Client, FastMCP

from plane_mcp.tools import workspaces


def _call(monkeypatch, resource, name, arguments):
    monkeypatch.setattr(
        workspaces, "get_plane_client_context", lambda: (SimpleNamespace(workspaces=resource), "community")
    )

    async def run():
        mcp = FastMCP("test")
        workspaces.register_workspace_tools(mcp)
        async with Client(mcp) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(run())


def test_list_preserves_virtual_identity_and_user_id(monkeypatch):
    user = {
        "id": "virtual-user-id",
        "display_name": "开发 Agent",
        "is_virtual": True,
        "job_title": "架构师",
        "job_titles": ["架构师", "IT运维"],
    }
    resource = Mock()
    resource._get.return_value = [user]

    result = _call(monkeypatch, resource, "list_virtual_users", {})

    resource._get.assert_called_once_with("community/virtual-users")
    assert result.structured_content == {"result": [user]}


def test_create_passes_name_and_projects(monkeypatch):
    resource = Mock()
    resource._post.return_value = {"id": "virtual-user-id", "is_virtual": True}

    result = _call(
        monkeypatch, resource, "create_virtual_user", {"display_name": "开发 Agent", "project_ids": ["project-1"]}
    )

    resource._post.assert_called_once_with(
        "community/virtual-users", {"display_name": "开发 Agent", "project_ids": ["project-1"]}
    )
    assert result.data["id"] == "virtual-user-id"


def test_create_workspace_only(monkeypatch):
    resource = Mock()
    resource._post.return_value = {"id": "virtual-user-id"}

    _call(monkeypatch, resource, "create_virtual_user", {"display_name": "Reviewer"})

    resource._post.assert_called_once_with("community/virtual-users", {"display_name": "Reviewer", "project_ids": []})


def test_create_with_job_title(monkeypatch):
    resource = Mock()
    resource._post.return_value = {"id": "virtual-user-id", "job_title": "架构师"}
    result = _call(monkeypatch, resource, "create_virtual_user", {"display_name": "Architect", "job_title": "架构师"})
    resource._post.assert_called_once_with(
        "community/virtual-users", {"display_name": "Architect", "project_ids": [], "job_title": "架构师"}
    )
    assert result.data["job_title"] == "架构师"


def test_list_job_title_names(monkeypatch):
    resource = Mock()
    resource._get.return_value = ["架构师", "自定义岗位"]
    result = _call(monkeypatch, resource, "list_virtual_user_job_titles", {})
    resource._get.assert_called_once_with("community/virtual-user-job-titles")
    assert result.structured_content == {"result": ["架构师", "自定义岗位"]}


def test_create_job_title_name(monkeypatch):
    resource = Mock()
    resource._post.return_value = {"name": "高级测试工程师"}
    result = _call(monkeypatch, resource, "create_virtual_user_job_title", {"name": "高级测试工程师"})
    resource._post.assert_called_once_with("community/virtual-user-job-titles", {"name": "高级测试工程师"})
    assert result.data["name"] == "高级测试工程师"


def test_create_with_multiple_job_titles(monkeypatch):
    resource = Mock()
    resource._post.return_value = {"id": "virtual-user-id", "job_titles": ["架构师", "IT运维"]}
    result = _call(
        monkeypatch,
        resource,
        "create_virtual_user",
        {"display_name": "Versatile agent", "job_title": "ignored", "job_titles": ["架构师", "IT运维"]},
    )
    resource._post.assert_called_once_with(
        "community/virtual-users",
        {"display_name": "Versatile agent", "project_ids": [], "job_titles": ["架构师", "IT运维"]},
    )
    assert result.data["job_titles"] == ["架构师", "IT运维"]


def test_explicit_empty_job_titles_override_legacy(monkeypatch):
    resource = Mock()
    resource._post.return_value = {"id": "virtual-user-id", "job_titles": []}
    _call(
        monkeypatch,
        resource,
        "create_virtual_user",
        {"display_name": "Agent", "job_title": "ignored", "job_titles": []},
    )
    resource._post.assert_called_once_with(
        "community/virtual-users", {"display_name": "Agent", "project_ids": [], "job_titles": []}
    )


def test_update_member_job_titles(monkeypatch):
    resource = Mock()
    resource._patch.return_value = {"id": "member-user", "job_titles": ["架构师", "IT运维"]}
    result = _call(
        monkeypatch,
        resource,
        "update_workspace_member_job_titles",
        {"user_id": "member-user", "job_titles": ["架构师", "IT运维"]},
    )
    resource._patch.assert_called_once_with(
        "community/members/member-user/job-titles", {"job_titles": ["架构师", "IT运维"]}
    )
    assert result.data["job_titles"] == ["架构师", "IT运维"]


def test_clear_member_job_titles(monkeypatch):
    resource = Mock()
    resource._patch.return_value = {"id": "member-user", "job_titles": []}
    _call(monkeypatch, resource, "update_workspace_member_job_titles", {"user_id": "member-user", "job_titles": []})
    resource._patch.assert_called_once_with("community/members/member-user/job-titles", {"job_titles": []})
