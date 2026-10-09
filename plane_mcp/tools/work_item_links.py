"""Work item link-related tools for Plane MCP Server."""

from typing import Any

from fastmcp import FastMCP
from plane.models.work_items import (
    CreateWorkItemLink,
    PaginatedWorkItemLinkResponse,
    UpdateWorkItemLink,
    WorkItemLink,
)

from plane_mcp.client import get_plane_client_context


class CreateAttributedLink(CreateWorkItemLink):
    """Preserve the optional Community Edition attribution field through the SDK."""

    virtual_user_id: str | None = None


class UpdateAttributedLink(UpdateWorkItemLink):
    """Preserve the optional Community Edition attribution field through the SDK."""

    virtual_user_id: str | None = None


def register_work_item_link_tools(mcp: FastMCP) -> None:
    """Register all work item link-related tools with the MCP server."""

    @mcp.tool()
    def list_work_item_links(
        project_id: str,
        work_item_id: str,
        params: dict[str, Any] | None = None,
    ) -> list[WorkItemLink]:
        """
        List links for a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            params: Optional query parameters as a dictionary

        Returns:
            List of WorkItemLink objects
        """
        client, workspace_slug = get_plane_client_context()
        response: PaginatedWorkItemLinkResponse = client.work_items.links.list(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            params=params,
        )
        return response.results

    @mcp.tool()
    def retrieve_work_item_link(
        project_id: str,
        work_item_id: str,
        link_id: str,
    ) -> WorkItemLink:
        """
        Retrieve a specific link for a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            link_id: UUID of the link

        Returns:
            WorkItemLink object
        """
        client, workspace_slug = get_plane_client_context()
        return client.work_items.links.retrieve(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            link_id=link_id,
        )

    @mcp.tool()
    def create_work_item_link(
        project_id: str,
        work_item_id: str,
        url: str,
        virtual_user_id: str | None = None,
    ) -> WorkItemLink:
        """
        Create a link for a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            url: URL of the link

            virtual_user_id: Optional project virtual user UUID for attribution; the API caller is retained for audit.

        Returns:
            Created WorkItemLink object
        """
        client, workspace_slug = get_plane_client_context()

        data = CreateAttributedLink(virtual_user_id=virtual_user_id, url=url)

        return client.work_items.links.create(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            data=data,
        )

    @mcp.tool()
    def update_work_item_link(
        project_id: str,
        work_item_id: str,
        link_id: str,
        url: str | None = None,
        virtual_user_id: str | None = None,
    ) -> WorkItemLink:
        """
        Update a link for a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            link_id: UUID of the link
            url: Updated URL of the link

            virtual_user_id: Optional project virtual user UUID for attribution; the API caller is retained for audit.

        Returns:
            Updated WorkItemLink object
        """
        client, workspace_slug = get_plane_client_context()

        data = UpdateAttributedLink(virtual_user_id=virtual_user_id, url=url)

        return client.work_items.links.update(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            link_id=link_id,
            data=data,
        )

    @mcp.tool()
    def delete_work_item_link(
        project_id: str,
        work_item_id: str,
        link_id: str,
        virtual_user_id: str | None = None,
    ) -> None:
        """
        Delete a link for a work item.

        Args:
            project_id: UUID of the project
            work_item_id: UUID of the work item
            link_id: UUID of the link
            virtual_user_id: Optional project virtual user UUID for the deletion activity.
        """
        client, workspace_slug = get_plane_client_context()
        if virtual_user_id is not None:
            return client.work_items.links._delete(
                f"{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/links/{link_id}",
                data={"virtual_user_id": virtual_user_id},
            )
        client.work_items.links.delete(
            workspace_slug=workspace_slug,
            project_id=project_id,
            work_item_id=work_item_id,
            link_id=link_id,
        )
