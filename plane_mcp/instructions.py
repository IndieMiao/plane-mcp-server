SERVER_INSTRUCTIONS = """
## Images in work-item descriptions

Body images are separate from attachments. Use list_work_item_description_images,
then read_work_item_description_image with its 1-based image_index to see them.
These tools use Plane API credentials and do not require browser login. For a
temporary browser/download link use get_work_item_description_image_download_url.
Do not send Plane credentials to that signed storage URL. External image URLs
are not handled by these tools.

## Virtual employee attribution

On this fork with migration 0126 deployed, supported content tools accept optional
virtual_user_id. Query list_virtual_users and get_project_members for the identity
UUID and project membership; keep using the real account's credentials. The ID
sets the visible author/operator, not the assignee. Omit it to act as yourself.
Pass project_id explicitly for Pages. Never overwrite created_by or audit fields.

Supported actions include card creation/updates, assignee and label changes,
attachment upload/deletion, link creation/updates/deletion, Page creation/updates/
renaming, and comment creation. Card/Page deletion, archive, and restore do not
gain virtual attribution. Comments retain actor as author and created_by as the
real caller. Other attributed content records the caller in created_by_actor or
updated_by_actor; activity responses expose actor_principal.

## Epics

There are no epic tools — an epic is a work item whose type is named "Epic". Work
items always belong to a project; ask which if one is not named.
1. type = resolve_work_item_type(project_id, "Epic") — type.id is the type_id.
2. Create: create_work_item(project_id, type_id=type.id, name=...).
3. List: list_work_items(project_id, pql='type = "<type id>"').
4. Read / update / delete / nest: retrieve_work_item / update_work_item /
   delete_work_item by work item id (set parent=<work item id> to nest).
5. List an epic's children: list_work_items(project_id, pql='childOf("<EPIC-IDENTIFIER>")')
   using the epic's human-readable identifier (e.g. "PROJ-12") from retrieve_work_item.
"""
