"""Page-related tools for Plane MCP Server."""

import os
from typing import Any

from fastmcp import FastMCP
from plane.models.pages import CreatePage, Page, UpdatePage
from plane.models.query_params import PaginatedQueryParams
from plane.models.work_item_pages import CreateWorkItemPage, WorkItemPage

from plane_mcp.client import get_plane_client_context


def _resolve_page_project_id(project_id: str | None) -> str | None:
    """Resolve an explicit project or the Community Edition Pages default."""
    resolved_project_id = project_id or os.getenv("PLANE_PAGE_PROJECT_ID")
    return resolved_project_id.strip() if resolved_project_id and resolved_project_id.strip() else None


def _update_page(
    client: Any,
    workspace_slug: str,
    page_id: str,
    project_id: str | None,
    data: UpdatePage,
) -> Page:
    """Update a page while plane-sdk has models but no public update methods."""
    if project_id is not None:
        update_project_page = getattr(client.pages, "update_project_page", None)
        if update_project_page is not None:
            return update_project_page(
                workspace_slug=workspace_slug,
                project_id=project_id,
                page_id=page_id,
                data=data,
            )
        endpoint = f"{workspace_slug}/projects/{project_id}/pages/{page_id}"
    else:
        update_workspace_page = getattr(client.pages, "update_workspace_page", None)
        if update_workspace_page is not None:
            return update_workspace_page(
                workspace_slug=workspace_slug,
                page_id=page_id,
                data=data,
            )
        endpoint = f"{workspace_slug}/pages/{page_id}"

    response = client.pages._patch(endpoint, data.model_dump(exclude_none=True))
    return Page.model_validate(response)


def register_page_tools(mcp: FastMCP) -> None:
    """Register all page-related tools with the MCP server."""

    @mcp.tool()
    def list_pages(
        project_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[Page]:
        """
        List pages.

        Lists a project's pages if project_id or PLANE_PAGE_PROJECT_ID is set,
        otherwise workspace-level pages.

        Args:
            project_id: UUID of the project. Omit to use PLANE_PAGE_PROJECT_ID,
                or to list workspace pages if no default is configured.
            params: Optional query parameters as a dictionary (e.g., per_page, cursor)

        Returns:
            List of Page objects
        """
        client, workspace_slug = get_plane_client_context()
        project_id = _resolve_page_project_id(project_id)
        query_params = PaginatedQueryParams(**params) if params else None
        if project_id is not None:
            response = client.pages.list_project_pages(
                workspace_slug=workspace_slug,
                project_id=project_id,
                params=query_params,
            )
        else:
            response = client.pages.list_workspace_pages(
                workspace_slug=workspace_slug,
                params=query_params,
            )
        return response.results

    @mcp.tool()
    def attach_page_to_work_item(
        project_id: str,
        work_item_id: str,
        page_id: str,
    ) -> WorkItemPage:
        """
        Link a page to a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            page_id: UUID of the page to link

        Returns:
            WorkItemPage link object
        """
        client, workspace_slug = get_plane_client_context()
        return client.work_items.pages.create(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            data=CreateWorkItemPage(page_id=page_id),
        )

    @mcp.tool()
    def list_work_item_pages(
        project_id: str,
        work_item_id: str,
    ) -> list[WorkItemPage]:
        """
        List all pages linked to a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item

        Returns:
            List of WorkItemPage link objects
        """
        client, workspace_slug = get_plane_client_context()
        response = client.work_items.pages.list(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
        )
        return response.results

    @mcp.tool()
    def detach_page_from_work_item(
        project_id: str,
        work_item_id: str,
        work_item_page_id: str,
    ) -> None:
        """
        Remove a page link from a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            work_item_page_id: UUID of the work item page link (not the page ID)
        """
        client, workspace_slug = get_plane_client_context()
        client.work_items.pages.delete(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            work_item_page_id=work_item_page_id,
        )

    @mcp.tool()
    def retrieve_page(
        page_id: str,
        project_id: str | None = None,
    ) -> Page:
        """
        Retrieve a page by ID.

        Retrieves a project page if project_id or PLANE_PAGE_PROJECT_ID is set,
        otherwise a workspace page.

        Args:
            page_id: UUID of the page
            project_id: UUID of the project. Omit to use PLANE_PAGE_PROJECT_ID,
                or for a workspace page if no default is configured.

        Returns:
            Page object
        """
        client, workspace_slug = get_plane_client_context()
        project_id = _resolve_page_project_id(project_id)

        if project_id is not None:
            return client.pages.retrieve_project_page(
                workspace_slug=workspace_slug,
                project_id=project_id,
                page_id=page_id,
            )
        return client.pages.retrieve_workspace_page(
            workspace_slug=workspace_slug,
            page_id=page_id,
        )

    @mcp.tool()
    def create_page(
        name: str,
        description_html: str,
        project_id: str | None = None,
        access: int | None = None,
        color: str | None = None,
        is_locked: bool | None = None,
        archived_at: str | None = None,
        view_props: dict[str, Any] | None = None,
        logo_props: dict[str, Any] | None = None,
        external_id: str | None = None,
        external_source: str | None = None,
    ) -> Page:
        """
        Create a page.

        Creates a project page if project_id or PLANE_PAGE_PROJECT_ID is set,
        otherwise a workspace-level page.

        Args:
            name: Page name
            description_html: Page content in HTML format
            project_id: UUID of the project. Omit to use PLANE_PAGE_PROJECT_ID,
                or to create a workspace page if no default is configured.
            access: Access level for the page (integer)
            color: Page color
            is_locked: Whether the page is locked
            archived_at: Archive timestamp (ISO 8601 format)
            view_props: View properties dictionary
            logo_props: Logo properties dictionary
            external_id: External system identifier
            external_source: External system source name

        Returns:
            Created Page object
        """
        client, workspace_slug = get_plane_client_context()
        project_id = _resolve_page_project_id(project_id)

        data = CreatePage(
            name=name,
            description_html=description_html,
            access=access,
            color=color,
            is_locked=is_locked,
            archived_at=archived_at,
            view_props=view_props,
            logo_props=logo_props,
            external_id=external_id,
            external_source=external_source,
        )

        if project_id is not None:
            return client.pages.create_project_page(
                workspace_slug=workspace_slug,
                project_id=project_id,
                data=data,
            )
        return client.pages.create_workspace_page(
            workspace_slug=workspace_slug,
            data=data,
        )

    @mcp.tool()
    def update_page(
        page_id: str,
        project_id: str | None = None,
        name: str | None = None,
        description_html: str | None = None,
        access: int | None = None,
        color: str | None = None,
        is_locked: bool | None = None,
        archived_at: str | None = None,
        view_props: dict[str, Any] | None = None,
        logo_props: dict[str, Any] | None = None,
        external_id: str | None = None,
        external_source: str | None = None,
    ) -> Page:
        """
        Partially update a page.

        Updates a project page if project_id or PLANE_PAGE_PROJECT_ID is set,
        otherwise a workspace-level page. Pass only fields that should change.

        Args:
            page_id: UUID of the page
            project_id: UUID of the project. Omit to use PLANE_PAGE_PROJECT_ID,
                or for a workspace page if no default is configured.
            name: New page name; setting this renames the page
            description_html: New page content in HTML format
            access: New access level for the page (integer)
            color: New page color
            is_locked: Whether the page is locked
            archived_at: Archive date in YYYY-MM-DD format
            view_props: New view properties dictionary
            logo_props: New logo properties dictionary
            external_id: New external system identifier
            external_source: New external system source name

        Returns:
            Updated Page object
        """
        client, workspace_slug = get_plane_client_context()
        project_id = _resolve_page_project_id(project_id)
        data = UpdatePage(
            name=name,
            description_html=description_html,
            access=access,
            color=color,
            is_locked=is_locked,
            archived_at=archived_at,
            view_props=view_props,
            logo_props=logo_props,
            external_id=external_id,
            external_source=external_source,
        )
        return _update_page(client, workspace_slug, page_id, project_id, data)

    @mcp.tool()
    def rename_page(
        page_id: str,
        name: str,
        project_id: str | None = None,
    ) -> Page:
        """
        Rename a page.

        Args:
            page_id: UUID of the page
            name: New page name
            project_id: UUID of the project. Omit to use PLANE_PAGE_PROJECT_ID,
                or for a workspace page if no default is configured.

        Returns:
            Renamed Page object
        """
        client, workspace_slug = get_plane_client_context()
        project_id = _resolve_page_project_id(project_id)
        return _update_page(client, workspace_slug, page_id, project_id, UpdatePage(name=name))

    @mcp.tool()
    def delete_page(
        page_id: str,
        project_id: str | None = None,
    ) -> None:
        """
        Delete a page.

        For Community Edition project pages, archive the page first with
        update_page(archived_at="YYYY-MM-DD"). Only the owner or a project
        administrator can delete an archived page.

        Args:
            page_id: UUID of the page
            project_id: UUID of the project. Omit to use PLANE_PAGE_PROJECT_ID,
                or for a workspace page if no default is configured.
        """
        client, workspace_slug = get_plane_client_context()
        project_id = _resolve_page_project_id(project_id)

        if project_id is not None:
            client.pages.delete_project_page(
                workspace_slug=workspace_slug,
                project_id=project_id,
                page_id=page_id,
            )
        else:
            client.pages.delete_workspace_page(
                workspace_slug=workspace_slug,
                page_id=page_id,
            )
