# Plane MCP Server

A Model Context Protocol (MCP) server for Plane integration. This server provides tools and resources for interacting with Plane through AI agents.

## Features

* 🔧 **Plane Integration**: Interact with Plane APIs and services
* 🔌 **Multiple Transports**: Supports stdio, SSE, and streamable HTTP transports
* 🌐 **Remote & Local**: Works both locally and as a remote service
* 🛠️ **Extensible**: Easy to add new tools and resources

## Usage

### Use this modified fork on another machine

The `community-pages` branch includes Community Edition Pages, virtual users,
custom job titles and multiple job titles. Install this source checkout with
[uv](https://docs.astral.sh/uv/):

```bash
git clone --branch community-pages --single-branch https://github.com/IndieMiao/plane-mcp-server.git
cd plane-mcp-server
uv sync --frozen --python 3.12
```

Configure your MCP client to run the checkout, replacing the directory and
environment values for your instance:

```json
{
  "mcpServers": {
    "plane": {
      "command": "uv",
      "args": [
        "--directory", "/ABSOLUTE/PATH/plane-mcp-server",
        "run", "--frozen", "plane-mcp-server", "stdio"
      ],
      "env": {
        "PLANE_BASE_URL": "https://plane.example.com",
        "PLANE_WORKSPACE_SLUG": "your-workspace",
        "PLANE_API_KEY": "<your-plane-api-key>"
      }
    }
  }
}
```

Connect to a Plane instance that already has this fork's backend extensions.
For Community Edition Pages, also set `PLANE_PAGE_PROJECT_ID` to the target
project UUID. Creating virtual users or job titles requires a workspace admin's
API key. After connecting, verify that `list_virtual_users`,
`create_virtual_user`, `list_virtual_user_job_titles`, and
`create_virtual_user_job_title` appear in the tool list.

To update this checkout, run `git pull --ff-only`, then `uv sync --frozen`, and
reconnect the MCP client. The upstream PyPI package and hosted Plane MCP below
do not include this fork's custom tools.

### Comment as a virtual user

With this fork's virtual-comment backend deployed, call `list_virtual_users()`
to find the identity's user UUID, then pass it to the existing comment tool:

```python
create_work_item_comment(
    project_id="PROJECT_UUID",
    work_item_id="WORK_ITEM_UUID",
    comment_html="<p>Implementation complete; ready for review.</p>",
    virtual_user_id="VIRTUAL_USER_UUID",
)
```

Both the caller and the virtual user must be active members or administrators
of the workspace and project. The comment's `actor` is the virtual user;
`created_by` and activity audit records identify the authenticated caller.
Virtual users still cannot log in or authenticate with their own API keys.
Omit `virtual_user_id` to comment as the API key owner. Invalid identities are
rejected, and the author cannot be changed when editing a comment.
Update the backend before reconnecting the MCP client; older backends do not
support this parameter. No new migration or frontend build is needed for this
comment extension if virtual users are already installed.

### Attribute work to a virtual employee

With this fork's attribution backend and migration `0126_virtual_user_attribution`
installed, these tools accept an optional `virtual_user_id`:

- `create_work_item`, `update_work_item` (including sub-tasks, content, status, priority, dates and estimates)
- `manage_work_item_assignee`, `manage_work_item_label`
- `upload_work_item_attachment_from_url`, `delete_work_item_attachment`
- `create_work_item_link`, `update_work_item_link`, `delete_work_item_link`
- `create_page`, `update_page`, `rename_page`

```python
create_work_item(
    project_id="PROJECT_UUID",
    name="Implement the scene",
    virtual_user_id="VIRTUAL_USER_UUID",
)
```

The identity is the visible author/operator; assignees are still set separately.
Created cards appear in the virtual employee's Created view. Activity records show
the virtual employee, while the backend retains the authenticated caller for audit
and creator permissions. Page ownership stays with the authenticated user. Pages
require a project ID or `PLANE_PAGE_PROJECT_ID` when using virtual attribution.

Both identities must be active workspace/project members or administrators.
Omitting the parameter retains the ordinary API-key behavior. Attachment uploads
carry the identity through initiation and confirmation without sending it or Plane
credentials to storage. DELETE attribution is sent as a JSON body. Archive/restore,
card deletion and Page deletion are outside this extension.

Deploy the matching API and worker builds, run the migration, update the frontend,
and reconnect the MCP client so its tool schemas are refreshed.

### Upstream transport examples

The server supports three transport methods. The following examples use the
upstream distribution; use the source configuration above for this fork.

**Requirements**:
- **Python 3.10+** (for stdio transport, via `uvx`)
- **Node.js 22+** (for remote transports, via `npx`)

### 1. Stdio Transport (for local use)

**MCP Client Configuration** (using uvx - recommended):

```json
{
  "mcpServers": {
    "plane": {
      "command": "uvx",
      "args": ["plane-mcp-server", "stdio"],
      "env": {
        "PLANE_API_KEY": "<your-api-key>",
        "PLANE_WORKSPACE_SLUG": "<your-workspace-slug>",
        "PLANE_BASE_URL": "https://api.plane.so"
      }
    }
  }
}
```

### 2. Remote HTTP Transport with OAuth

Connect to the hosted Plane MCP server using OAuth authentication.

**URL**: `https://mcp.plane.so/http/mcp`

**MCP Client Configuration** (for tools like Claude Desktop without native remote MCP support):

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["mcp-remote@latest", "https://mcp.plane.so/http/mcp"]
    }
  }
}
```

**Note**: OAuth authentication will be handled automatically when connecting to the remote server.

### 3. Remote HTTP Transport using PAT Token

Connect to the hosted Plane MCP server using a Personal Access Token (PAT).

**URL**: `https://mcp.plane.so/http/api-key/mcp`

**Headers**:
- `Authorization: Bearer <PAT_TOKEN>`
- `X-Workspace-slug: <SLUG>`

**MCP Client Configuration** (for tools like Claude Desktop without native remote MCP support):

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["mcp-remote@latest", "https://mcp.plane.so/http/api-key/mcp"],
      "headers": {
        "Authorization": "Bearer <PAT_TOKEN>",
        "X-Workspace-slug": "<SLUG>"
      }
    }
  }
}
```

### 4. SSE Transport (Legacy)

⚠️ **Legacy Transport**: SSE (Server-Sent Events) transport is maintained for backward compatibility. New implementations should use the HTTP transport (sections 2 or 3) instead.

Connect to the hosted Plane MCP server using OAuth authentication via Server-Sent Events.

**URL**: `https://mcp.plane.so/sse`

**MCP Client Configuration** (for tools that support SSE transport):

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["mcp-remote@latest", "https://mcp.plane.so/sse"]
    }
  }
}
```

**Note**: OAuth authentication will be handled automatically when connecting to the remote server. This transport is deprecated in favor of the HTTP transport.


## Configuration

### Authentication

The server requires authentication via environment variables:

- `PLANE_BASE_URL`: Base URL for Plane API (default: `https://api.plane.so`) - Optional
- `PLANE_API_KEY`: API key for authentication (required for stdio transport)
- `PLANE_WORKSPACE_SLUG`: Workspace slug identifier (required for stdio transport)
- `PLANE_ACCESS_TOKEN`: Access token for authentication (alternative to API key)
- `PLANE_PAGE_PROJECT_ID`: Optional default project UUID for Page tools. This is
  recommended for Community Edition, where Pages are project-scoped.

**Example** (for stdio transport):
```bash
export PLANE_BASE_URL="https://api.plane.so"
export PLANE_API_KEY="your-api-key"
export PLANE_WORKSPACE_SLUG="your-workspace-slug"
```

### Self-hosted Community Edition Pages

Community Edition exposes Pages in the product UI at project scope. Point
`PLANE_BASE_URL` at the instance root (do not append `/api/v1`) and configure a
default project so an agent can call `create_page` without repeating the project
UUID:

```bash
export PLANE_BASE_URL="https://plane.example.com"
export PLANE_API_KEY="your-api-key"
export PLANE_WORKSPACE_SLUG="your-workspace-slug"
export PLANE_PAGE_PROJECT_ID="your-project-uuid"
```

An explicit `project_id` passed to a Page tool overrides
`PLANE_PAGE_PROJECT_ID`. If the variable and argument are both omitted, the
tools retain their Plane Cloud workspace-page behavior.

Self-hosted instances must also expose the matching project Pages endpoint at
`/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/`. The sibling
Plane Community Edition changes in this workspace add that API-key endpoint.

**Note**: For remote HTTP transports (OAuth or PAT), authentication is handled via the connection method (OAuth flow or PAT headers) and does not require these environment variables.

### OAuth redirect URIs

For the OAuth HTTP/SSE transports, the server validates each client's redirect URI against an allowlist. Common MCP clients (Cursor, VS Code, Claude.ai, ChatGPT connectors, localhost) are allowed by default.

To onboard a new client without a code change or release, append extra patterns via an environment variable:

- `PLANE_OAUTH_ALLOWED_REDIRECT_URIS`: Comma-separated redirect URI patterns appended to the built-in allowlist.

```bash
export PLANE_OAUTH_ALLOWED_REDIRECT_URIS="https://newclient.com/cb,https://other.app/oauth/*"
```

Patterns support glob matching (`*` matches any port, path segment, or subdomain). For security, keep the host pinned and wildcard only the port/path.

### Logging

The server emits structured JSON logs. Each tool call is logged with its tool name, duration, status, and (when available) the opaque user id and workspace slug.

- `LOG_USER_INFO`: When `true`, include user info (PII such as the display name) in logs alongside the opaque user id. Defaults to `false` so PII is never logged unless explicitly opted in. Only the OAuth and PAT (header) HTTP transports carry a display name; stdio is unaffected.

```bash
export LOG_USER_INFO="true"
```

## Available Tools

The server provides comprehensive tools for interacting with Plane. All tools use Pydantic models from the Plane SDK for type safety and validation.

### Projects

| Tool Name | Description |
|-----------|-------------|
| `list_projects` | List all projects in a workspace with optional pagination and filtering |
| `create_project` | Create a new project with name, identifier, and optional configuration |
| `retrieve_project` | Retrieve a project by ID |
| `update_project` | Update a project with partial data |
| `delete_project` | Delete a project by ID |
| `get_project_worklog_summary` | Get work log summary for a project |
| `get_project_members` | Get all members of a project |
| `update_project_features` | Update features configuration of a project |

### Work Items

| Tool Name | Description |
|-----------|-------------|
| `list_work_items` | List all work items in a project with optional filtering and pagination |
| `create_work_item` | Create a new work item with name, assignees, labels, and other attributes |
| `retrieve_work_item` | Retrieve a work item by ID with optional field expansion |
| `retrieve_work_item_by_identifier` | Retrieve a work item by project identifier and issue sequence number |
| `update_work_item` | Update a work item with partial data |
| `delete_work_item` | Delete a work item by ID |
| `search_work_items` | Search work items across a workspace with query string |

### Cycles

| Tool Name | Description |
|-----------|-------------|
| `list_cycles` | List cycles in a project (set `archived=true` for archived) |
| `create_cycle` | Create a new cycle with name, dates, and owner |
| `retrieve_cycle` | Retrieve a cycle by ID |
| `update_cycle` | Update a cycle with partial data |
| `delete_cycle` | Delete a cycle by ID |
| `manage_cycle_work_items` | Add and/or remove work items on a cycle |
| `list_cycle_work_items` | List work items in a cycle |
| `transfer_cycle_work_items` | Transfer work items from one cycle to another |
| `manage_cycle_archive` | Archive or unarchive a cycle |

### Modules

| Tool Name | Description |
|-----------|-------------|
| `list_modules` | List modules in a project (set `archived=true` for archived) |
| `create_module` | Create a new module with name, dates, status, and members |
| `retrieve_module` | Retrieve a module by ID |
| `update_module` | Update a module with partial data |
| `delete_module` | Delete a module by ID |
| `manage_module_work_items` | Add and/or remove work items on a module |
| `list_module_work_items` | List work items in a module |
| `manage_module_archive` | Archive or unarchive a module |

### Initiatives

| Tool Name | Description |
|-----------|-------------|
| `list_initiatives` | List all initiatives in a workspace |
| `create_initiative` | Create a new initiative with name, dates, state, and lead |
| `retrieve_initiative` | Retrieve an initiative by ID |
| `update_initiative` | Update an initiative with partial data |
| `delete_initiative` | Delete an initiative by ID |

### Intake Work Items

| Tool Name | Description |
|-----------|-------------|
| `list_intake_work_items` | List all intake work items in a project with optional pagination |
| `create_intake_work_item` | Create a new intake work item in a project |
| `retrieve_intake_work_item` | Retrieve an intake work item by work item ID with optional field expansion |
| `update_intake_work_item` | Update an intake work item with partial data |
| `delete_intake_work_item` | Delete an intake work item by work item ID |

### Work Item Properties

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_properties` | List work item properties for a work item type |
| `create_work_item_property` | Create a new work item property with type, settings, and validation rules |
| `retrieve_work_item_property` | Retrieve a work item property by ID |
| `update_work_item_property` | Update a work item property with partial data |
| `delete_work_item_property` | Delete a work item property by ID |

### Milestones

| Tool Name | Description |
|-----------|-------------|
| `list_milestones` | List all milestones in a project |
| `create_milestone` | Create a new milestone |
| `retrieve_milestone` | Retrieve a milestone by ID |
| `update_milestone` | Update a milestone by ID |
| `delete_milestone` | Delete a milestone by ID |
| `manage_milestone_work_items` | Add and/or remove work items on a milestone |
| `list_milestone_work_items` | List work items in a milestone |

### Labels

| Tool Name | Description |
|-----------|-------------|
| `list_labels` | List all labels in a project |
| `create_label` | Create a new label |
| `retrieve_label` | Retrieve a label by ID |
| `update_label` | Update a label by ID |
| `delete_label` | Delete a label by ID |

### States

| Tool Name | Description |
|-----------|-------------|
| `list_states` | List all states in a project |
| `create_state` | Create a new state |
| `retrieve_state` | Retrieve a state by ID |
| `update_state` | Update a state by ID |
| `delete_state` | Delete a state by ID |

### Work Item Comments

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_comments` | List comments for a work item |
| `retrieve_work_item_comment` | Retrieve a specific comment for a work item |
| `create_work_item_comment` | Create a comment for a work item |
| `update_work_item_comment` | Update a comment for a work item |
| `delete_work_item_comment` | Delete a comment for a work item |

### Work Item Links

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_links` | List links for a work item |
| `retrieve_work_item_link` | Retrieve a specific link for a work item |
| `create_work_item_link` | Create a link for a work item |
| `update_work_item_link` | Update a link for a work item |
| `delete_work_item_link` | Delete a link for a work item |

### Work Item Types

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_types` | List all work item types in a project |
| `create_work_item_type` | Create a new work item type |
| `retrieve_work_item_type` | Retrieve a work item type by ID |
| `update_work_item_type` | Update a work item type by ID |
| `delete_work_item_type` | Delete a work item type by ID |
| `import_work_item_types_to_project` | Bulk-link workspace-level work item types to a project |
| `resolve_work_item_type` | Find or create a named type for a project, auto-handling workspace vs project scope and import |

### Work Item Relations

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_relations` | List relations for a work item |
| `create_work_item_relation` | Create relations for a work item |
| `remove_work_item_relation` | Remove a relation from a work item |

### Work Item Relation Definitions

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_relation_definitions` | List workspace custom relation definitions |
| `create_work_item_relation_definition` | Create a workspace relation definition |
| `update_work_item_relation_definition` | Update a relation definition |
| `delete_work_item_relation_definition` | Delete a relation definition |

### Work Item Activities

| Tool Name | Description |
|-----------|-------------|
| `list_work_item_activities` | List activities for a work item |
| `retrieve_work_item_activity` | Retrieve a specific activity for a work item |

### Work Logs

| Tool Name | Description |
|-----------|-------------|
| `list_work_logs` | List work logs for a work item |
| `create_work_log` | Create a work log for a work item |
| `update_work_log` | Update a work log for a work item |
| `delete_work_log` | Delete a work log for a work item |

### Pages

| Tool Name | Description |
|-----------|-------------|
| `list_pages` | List pages (workspace, or a project's if `project_id` given) |
| `retrieve_page` | Retrieve a page by ID (workspace, or project's if `project_id` given) |
| `create_page` | Create a workspace or project page (`PLANE_PAGE_PROJECT_ID` supplies the Community Edition default) |
| `update_page` | Partially update page fields or archive a page |
| `rename_page` | Rename a page |
| `delete_page` | Delete a page (Community Edition project pages must be archived first) |

### Workspaces

| Tool Name | Description |
|-----------|-------------|
| `get_workspace_members` | Get all members of the current workspace |
| `list_virtual_users` | List Community Edition virtual identities and their user IDs |
| `create_virtual_user` | Create a virtual identity and optionally join projects (workspace admin only) |
| `list_virtual_user_job_titles` | List default and custom job title names in the workspace |
| `create_virtual_user_job_title` | Add a reusable job title name (workspace admin only) |
| `update_workspace_member_job_titles` | Replace or clear a human or virtual member's job titles in the current workspace (admin only) |
| `get_features` | Get feature flags (workspace, or a project's if `project_id` given) |
| `update_workspace_features` | Update features of the current workspace |

### Users

On a Community Edition instance with the virtual-users extension, create an
identity with `create_virtual_user(display_name="Development Agent",
project_ids=["PROJECT_UUID"])`. Then use `list_virtual_users()` to find its `id`
and `manage_work_item_assignee(project_id=..., work_item_id=...,
add_user_id=...)` to assign a task while preserving other assignees. The identity
must belong to the task's project. Virtual users cannot log in: the agent uses
its existing API credentials and audit records retain the actual caller.

Pass `job_titles=["游戏主程", "架构师"]` to `create_virtual_user` to attach multiple
job titles. New names are saved as reusable workspace options. Use
`list_virtual_user_job_titles()` to list options or
`create_virtual_user_job_title(name="高级测试工程师")` to add one. Job titles do
not change member permissions; `list_virtual_users()` includes the full `job_titles`
array. The legacy `job_title` argument remains supported when `job_titles` is
omitted; responses keep `job_title` as the first selected title.

Use `update_workspace_member_job_titles(user_id="USER_UUID",
job_titles=["架构师", "IT运维"])` to replace an existing member's titles in the
current workspace; pass `[]` to clear them. The UUID identifies the user, not
the workspace membership record. This works for both human and virtual members,
requires a workspace administrator, and leaves other workspaces' titles unchanged.

| Tool Name | Description |
|-----------|-------------|
| `get_me` | Get current authenticated user information |

**Total Tools**: 100+ tools across 20 categories

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black plane_mcp/
ruff check plane_mcp/
```

## License

MIT License - see LICENSE for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Deprecation Notice

⚠️ **The Node.js-based `plane-mcp-server` is deprecated and no longer maintained.**

This repository represents the new Python+FastMCP based implementation of the Plane MCP server. If you were using the previous Node.js version, please migrate to this Python-based version for continued support and updates.

The new implementation offers:
- Better type safety with Pydantic models
- Improved performance with FastMCP
- Enhanced tool coverage
- Active maintenance and development

For migration assistance, please refer to the configuration examples in this README or open an issue for support.

**Old Node.js Configuration (Deprecated):**

If you were using the previous Node.js-based `@makeplane/plane-mcp-server`, your configuration looked like this:

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": [
        "-y",
        "@makeplane/plane-mcp-server"
      ],
      "env": {
        "PLANE_API_KEY": "<YOUR_API_KEY>",
        "PLANE_API_HOST_URL": "<HOST_URL_FOR_SELF_HOSTED>",
        "PLANE_WORKSPACE_SLUG": "<YOUR_WORKSPACE_SLUG>"
      }
    }
  }
}
```

**Please migrate to the new Python-based configuration shown in the Usage section above.**
