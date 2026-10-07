"""Workspace-related tools for Plane MCP Server."""

from typing import Any

from fastmcp import FastMCP
from plane.models.projects import ProjectFeature
from plane.models.query_params import MemberListQueryParams
from plane.models.workspaces import PaginatedWorkspaceMemberResponse, WorkspaceFeature

from plane_mcp.client import get_plane_client_context


def register_workspace_tools(mcp: FastMCP) -> None:
    """Register all workspace-related tools with the MCP server."""

    @mcp.tool()
    def list_virtual_users() -> list[dict[str, Any]]:
        """List active virtual identities in this Community Edition workspace.

        Returns user IDs, display names, job_titles and is_virtual. Use the returned id with
        manage_work_item_assignee(add_user_id=...) to assign a task to an agent's
        virtual identity. The identity must be a member of the task's project.
        Requests run with the caller's existing credentials; virtual users cannot
        log in. Requires the Community Edition virtual-users API extension.
        """
        client, workspace_slug = get_plane_client_context()
        return client.workspaces._get(f"{workspace_slug}/virtual-users")

    @mcp.tool()
    def create_virtual_user(
        display_name: str,
        project_ids: list[str] | None = None,
        job_title: str | None = None,
        job_titles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an assignment-only virtual user as a workspace administrator.

        Args:
            display_name: Name identifying the person or agent (required).
            project_ids: Projects to join as a member so tasks can be assigned
                immediately. Omit to add to the workspace only.
            job_title: Legacy single-title input, used when job_titles is omitted.
            job_titles: Optional list of job title names. New names are saved
                as reusable workspace options. An empty list means no job titles.

        Returns the user ID for manage_work_item_assignee(add_user_id=...).
        No email, password or invitation is needed. Requires the Community
        Edition virtual-users API extension.
        """
        client, workspace_slug = get_plane_client_context()
        data: dict[str, Any] = {"display_name": display_name, "project_ids": project_ids or []}
        if job_titles is not None:
            data["job_titles"] = job_titles
        elif job_title is not None:
            data["job_title"] = job_title
        return client.workspaces._post(
            f"{workspace_slug}/virtual-users",
            data,
        )

    @mcp.tool()
    def list_virtual_user_job_titles() -> list[str]:
        """List default and custom job title names in this workspace."""
        client, workspace_slug = get_plane_client_context()
        return client.workspaces._get(f"{workspace_slug}/virtual-user-job-titles")

    @mcp.tool()
    def create_virtual_user_job_title(name: str) -> dict[str, str]:
        """Add a reusable job title name as a workspace administrator.

        Existing names are returned without duplication. Job titles are plain
        text labels and do not change member permissions.
        """
        client, workspace_slug = get_plane_client_context()
        return client.workspaces._post(f"{workspace_slug}/virtual-user-job-titles", {"name": name})

    @mcp.tool()
    def update_workspace_member_job_titles(user_id: str, job_titles: list[str]) -> dict[str, Any]:
        """Replace a member's job title tags in the current workspace as an admin.

        Args:
            user_id: User UUID, not the workspace membership UUID. Supports
                active human and virtual members of the current workspace.
            job_titles: Complete list of names to keep; [] clears all titles.
                New names become reusable workspace options. Other workspaces
                and member permissions are unchanged.
        """
        client, workspace_slug = get_plane_client_context()
        return client.workspaces._patch(f"{workspace_slug}/members/{user_id}/job-titles", {"job_titles": job_titles})

    @mcp.tool()
    def get_workspace_members(
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        display_name: str | None = None,
        role_slug: str | None = None,
        is_active: bool | None = None,
        is_bot: bool | None = None,
        cursor: str | None = None,
        per_page: int | None = 100,
        order_by: str | None = None,
    ) -> PaginatedWorkspaceMemberResponse:
        """
        List members of the current workspace (filterable, paginated).

        Optional filters first_name/last_name/email/display_name (case-insensitive
        contains), role_slug (exact), is_active, is_bot — combined with AND.

        Args:
            cursor: Prior response's next_cursor; omit for first page.
            per_page: Results per page (1-1000, default 100).
            order_by: Sort field; prefix '-' for descending.

        Returns:
            Paginated envelope: results (members incl. role, role_slug,
            is_active, is_bot) + total_count, next_cursor, next_page_results.
        """
        client, workspace_slug = get_plane_client_context()
        params = MemberListQueryParams(
            first_name=first_name,
            last_name=last_name,
            email=email,
            display_name=display_name,
            role_slug=role_slug,
            is_active=is_active,
            is_bot=is_bot,
            cursor=cursor,
            per_page=per_page,
            order_by=order_by,
        )
        return client.workspaces.get_members_lite(workspace_slug=workspace_slug, params=params)

    @mcp.tool()
    def get_features(project_id: str | None = None) -> WorkspaceFeature | ProjectFeature:
        """
        Get feature flags.

        Returns a project's features if project_id is given, otherwise the
        workspace's features.

        Args:
            project_id: UUID of the project. Omit for workspace features.

        Returns:
            ProjectFeature when project_id is given, otherwise WorkspaceFeature.
        """
        client, workspace_slug = get_plane_client_context()
        if project_id is not None:
            return client.projects.get_features(workspace_slug=workspace_slug, project_id=project_id)
        return client.workspaces.get_features(workspace_slug=workspace_slug)

    @mcp.tool()
    def update_workspace_features(
        project_grouping: bool | None = None,
        initiatives: bool | None = None,
        teams: bool | None = None,
        customers: bool | None = None,
        wiki: bool | None = None,
        pi: bool | None = None,
    ) -> WorkspaceFeature:
        """
        Update features of the current workspace.

        Args:
            project_grouping: Enable/disable project grouping feature
            initiatives: Enable/disable initiatives feature
            teams: Enable/disable teams feature
            customers: Enable/disable customers feature
            wiki: Enable/disable wiki feature
            pi: Enable/disable PI (Program Increment) feature

        Returns:
            Updated WorkspaceFeature object
        """
        client, workspace_slug = get_plane_client_context()

        # Build data dict with only non-None values
        feature_data: dict[str, bool] = {}
        if project_grouping is not None:
            feature_data["project_grouping"] = project_grouping
        if initiatives is not None:
            feature_data["initiatives"] = initiatives
        if teams is not None:
            feature_data["teams"] = teams
        if customers is not None:
            feature_data["customers"] = customers
        if wiki is not None:
            feature_data["wiki"] = wiki
        if pi is not None:
            feature_data["pi"] = pi

        data = WorkspaceFeature(**feature_data)

        return client.workspaces.update_features(workspace_slug=workspace_slug, data=data)
