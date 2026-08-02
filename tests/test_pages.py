"""Offline tests for Community Edition project Page tools."""

import asyncio
from types import SimpleNamespace

from fastmcp import Client, FastMCP
from plane.models.pages import Page

from plane_mcp.tools import pages as page_tools


class FakePages:
    def __init__(self):
        self.calls = []

    def list_project_pages(self, **kwargs):
        self.calls.append(("list_project_pages", kwargs))
        return SimpleNamespace(results=[Page(id="page-1", name="Project page")])

    def list_workspace_pages(self, **kwargs):
        self.calls.append(("list_workspace_pages", kwargs))
        return SimpleNamespace(results=[Page(id="page-1", name="Workspace page")])

    def retrieve_project_page(self, **kwargs):
        self.calls.append(("retrieve_project_page", kwargs))
        return Page(id=kwargs["page_id"], name="Project page")

    def retrieve_workspace_page(self, **kwargs):
        self.calls.append(("retrieve_workspace_page", kwargs))
        return Page(id=kwargs["page_id"], name="Workspace page")

    def create_project_page(self, **kwargs):
        self.calls.append(("create_project_page", kwargs))
        return Page(
            id="created-page",
            name=kwargs["data"].name,
            description_html=kwargs["data"].description_html,
        )

    def create_workspace_page(self, **kwargs):
        self.calls.append(("create_workspace_page", kwargs))
        return Page(
            id="created-page",
            name=kwargs["data"].name,
            description_html=kwargs["data"].description_html,
        )


class FakeClient:
    def __init__(self):
        self.pages = FakePages()


def _call(monkeypatch, client, tool, args):
    monkeypatch.setattr(page_tools, "get_plane_client_context", lambda: (client, "community"))

    async def run():
        mcp = FastMCP("test")
        page_tools.register_page_tools(mcp)
        async with Client(mcp) as mcp_client:
            return await mcp_client.call_tool(tool, args)

    return asyncio.run(run())


def test_create_page_uses_community_default_project(monkeypatch):
    monkeypatch.setenv("PLANE_PAGE_PROJECT_ID", "project-default")
    client = FakeClient()

    _call(
        monkeypatch,
        client,
        "create_page",
        {"name": "Runbook", "description_html": "<h1>Runbook</h1>"},
    )

    method, kwargs = client.pages.calls[-1]
    assert method == "create_project_page"
    assert kwargs["workspace_slug"] == "community"
    assert kwargs["project_id"] == "project-default"
    assert kwargs["data"].description_html == "<h1>Runbook</h1>"


def test_explicit_project_overrides_community_default(monkeypatch):
    monkeypatch.setenv("PLANE_PAGE_PROJECT_ID", "project-default")
    client = FakeClient()

    _call(
        monkeypatch,
        client,
        "create_page",
        {
            "name": "Architecture",
            "description_html": "<p>Details</p>",
            "project_id": "project-explicit",
        },
    )

    method, kwargs = client.pages.calls[-1]
    assert method == "create_project_page"
    assert kwargs["project_id"] == "project-explicit"


def test_workspace_page_behavior_is_preserved_without_default(monkeypatch):
    monkeypatch.delenv("PLANE_PAGE_PROJECT_ID", raising=False)
    client = FakeClient()

    _call(
        monkeypatch,
        client,
        "create_page",
        {"name": "Workspace page", "description_html": "<p>Cloud wiki</p>"},
    )

    method, _ = client.pages.calls[-1]
    assert method == "create_workspace_page"


def test_list_pages_converts_dict_query_params_for_plane_sdk(monkeypatch):
    monkeypatch.setenv("PLANE_PAGE_PROJECT_ID", "project-default")
    client = FakeClient()

    _call(
        monkeypatch,
        client,
        "list_pages",
        {"params": {"per_page": 25, "cursor": "25:1:0"}},
    )

    method, kwargs = client.pages.calls[-1]
    assert method == "list_project_pages"
    assert kwargs["params"].per_page == 25
    assert kwargs["params"].cursor == "25:1:0"
