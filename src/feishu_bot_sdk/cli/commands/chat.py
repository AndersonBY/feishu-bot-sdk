from __future__ import annotations

import argparse
from typing import Any, Callable, Mapping

from ...chat import ChatService
from ..runtime import _build_client, _parse_json_array, _parse_json_object


def _normalize_page_size(value: Any, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return default


def _next_page_token(data: Mapping[str, Any]) -> str | None:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _parse_bool_choice(value: Any, *, name: str) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return text == "true"


def _parse_object_source(
    args: argparse.Namespace,
    *,
    prefix: str,
    name: str,
    required: bool,
) -> dict[str, Any]:
    return _parse_json_object(
        json_text=getattr(args, f"{prefix}_json", None),
        file_path=getattr(args, f"{prefix}_file", None),
        stdin_enabled=bool(getattr(args, f"{prefix}_stdin", False)),
        name=name,
        required=required,
    )


def _parse_array_source(
    args: argparse.Namespace,
    *,
    prefix: str,
    name: str,
    required: bool,
) -> list[Any]:
    return _parse_json_array(
        json_text=getattr(args, f"{prefix}_json", None),
        file_path=getattr(args, f"{prefix}_file", None),
        stdin_enabled=bool(getattr(args, f"{prefix}_stdin", False)),
        name=name,
        required=required,
    )


def _require_object_array(values: list[Any], *, name: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} must be a JSON array of objects")
        normalized.append({str(key): item for key, item in value.items()})
    return normalized


def _parse_string_list_source(
    args: argparse.Namespace,
    *,
    values_attr: str,
    prefix: str,
    name: str,
    required: bool,
) -> list[str]:
    values = [str(value).strip() for value in list(getattr(args, values_attr, []) or []) if str(value).strip()]
    json_values = _parse_array_source(args, prefix=prefix, name=name, required=False)
    for value in json_values:
        text = str(value).strip()
        if text:
            values.append(text)
    if required and not values:
        raise ValueError(
            f"at least one {name} is required "
            f"(use --{name} repeatedly or --{name}s-json/--{name}s-file/--{name}s-stdin)"
        )
    return values


def _collect_all_pages(
    fetch_page: Callable[..., Mapping[str, Any]],
    *,
    page_size: int | None,
    page_token: str | None,
    default_page_size: int,
    key: str = "items",
) -> Mapping[str, Any]:
    collected: list[Any] = []
    current_token = page_token
    current_page_size = page_size
    while True:
        data = fetch_page(page_size=current_page_size, page_token=current_token)
        items = data.get(key)
        if isinstance(items, list):
            collected.extend(items)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
        current_page_size = _normalize_page_size(current_page_size, default=default_page_size)
    return {"all": True, "has_more": False, "count": len(collected), key: collected}


def _cmd_chat_create(args: argparse.Namespace) -> Mapping[str, Any]:
    chat = _parse_object_source(args, prefix="chat", name="chat", required=True)
    service = ChatService(_build_client(args))
    return service.create_chat(
        chat,
        user_id_type=getattr(args, "user_id_type", None),
        set_bot_manager=_parse_bool_choice(getattr(args, "set_bot_manager", None), name="set_bot_manager"),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_chat_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.get_chat(str(args.chat_id), user_id_type=getattr(args, "user_id_type", None))


def _cmd_chat_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    user_id_type = getattr(args, "user_id_type", None)
    sort_type = getattr(args, "sort_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_chats(
            user_id_type=user_id_type,
            sort_type=sort_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_chats(
            user_id_type=user_id_type,
            sort_type=sort_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=20,
    )


def _cmd_chat_search(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    query = str(args.query)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.search_chats(
            query,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.search_chats(
            query,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=20,
    )


def _cmd_chat_update(args: argparse.Namespace) -> Mapping[str, Any]:
    chat = _parse_object_source(args, prefix="chat", name="chat", required=True)
    service = ChatService(_build_client(args))
    return service.update_chat(
        str(args.chat_id),
        chat,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_chat_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.delete_chat(str(args.chat_id))


def _cmd_chat_get_link(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.get_share_link(
        str(args.chat_id),
        validity_period=getattr(args, "validity_period", None),
    )


def _cmd_chat_moderation_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    user_id_type = getattr(args, "user_id_type", None)
    chat_id = str(args.chat_id)
    if not bool(getattr(args, "all", False)):
        return service.get_moderation(
            chat_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.get_moderation(
            chat_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_chat_moderation_update(args: argparse.Namespace) -> Mapping[str, Any]:
    moderation = _parse_object_source(args, prefix="moderation", name="moderation", required=False)
    if not moderation:
        added = _parse_string_list_source(
            args,
            values_attr="moderator_added_ids",
            prefix="moderator_added_ids",
            name="moderator-added-id",
            required=False,
        )
        removed = _parse_string_list_source(
            args,
            values_attr="moderator_removed_ids",
            prefix="moderator_removed_ids",
            name="moderator-removed-id",
            required=False,
        )
        moderation_setting = getattr(args, "moderation_setting", None)
        if moderation_setting is None and not added and not removed:
            raise ValueError(
                "provide moderation payload via --moderation-json/--moderation-file/--moderation-stdin "
                "or use --moderation-setting with optional moderator add/remove ids"
            )
        if moderation_setting is not None:
            moderation["moderation_setting"] = str(moderation_setting)
        if added:
            moderation["moderator_added_list"] = added
        if removed:
            moderation["moderator_removed_list"] = removed
    service = ChatService(_build_client(args))
    return service.update_moderation(
        str(args.chat_id),
        moderation,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_chat_top_notice_put(args: argparse.Namespace) -> Mapping[str, Any]:
    notice = _parse_object_source(args, prefix="top_notice", name="top-notice", required=False)
    if not notice:
        message_id = getattr(args, "message_id", None)
        announcement = bool(getattr(args, "announcement", False))
        action_type = getattr(args, "action_type", None)
        if announcement:
            if message_id:
                raise ValueError("--announcement cannot be combined with --message-id")
            action_type = "2"
        if action_type is None:
            action_type = "1" if message_id else None
        if action_type is None:
            raise ValueError(
                "provide top notice payload via --top-notice-json/--top-notice-file/--top-notice-stdin "
                "or use --announcement or --message-id"
            )
        item: dict[str, Any] = {"action_type": str(action_type)}
        if str(action_type) == "1":
            if not message_id:
                raise ValueError("--message-id is required when --action-type=1")
            item["message_id"] = str(message_id)
        elif message_id:
            item["message_id"] = str(message_id)
        notice = {"chat_top_notice": [item]}
    service = ChatService(_build_client(args))
    return service.put_top_notice(str(args.chat_id), notice)


def _cmd_chat_top_notice_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.delete_top_notice(str(args.chat_id))


def _cmd_chat_member_add(args: argparse.Namespace) -> Mapping[str, Any]:
    member_ids = _parse_string_list_source(
        args,
        values_attr="member_ids",
        prefix="member_ids",
        name="member-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.add_members(
        str(args.chat_id),
        member_ids,
        member_id_type=getattr(args, "member_id_type", None),
        succeed_type=getattr(args, "succeed_type", None),
    )


def _cmd_chat_member_remove(args: argparse.Namespace) -> Mapping[str, Any]:
    member_ids = _parse_string_list_source(
        args,
        values_attr="member_ids",
        prefix="member_ids",
        name="member-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.remove_members(
        str(args.chat_id),
        member_ids,
        member_id_type=getattr(args, "member_id_type", None),
    )


def _cmd_chat_member_join(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.join_chat(str(args.chat_id))


def _cmd_chat_member_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    member_id_type = getattr(args, "member_id_type", None)
    chat_id = str(args.chat_id)
    if not bool(getattr(args, "all", False)):
        return service.list_members(
            chat_id,
            member_id_type=member_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_members(
            chat_id,
            member_id_type=member_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_chat_member_check(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.check_in_chat(str(args.chat_id))


def _cmd_chat_manager_add(args: argparse.Namespace) -> Mapping[str, Any]:
    manager_ids = _parse_string_list_source(
        args,
        values_attr="manager_ids",
        prefix="manager_ids",
        name="manager-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.add_managers(
        str(args.chat_id),
        manager_ids,
        member_id_type=getattr(args, "member_id_type", None),
    )


def _cmd_chat_manager_remove(args: argparse.Namespace) -> Mapping[str, Any]:
    manager_ids = _parse_string_list_source(
        args,
        values_attr="manager_ids",
        prefix="manager_ids",
        name="manager-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.remove_managers(
        str(args.chat_id),
        manager_ids,
        member_id_type=getattr(args, "member_id_type", None),
    )


def _cmd_chat_announcement_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.get_announcement(
        str(args.chat_id),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_chat_announcement_list_blocks(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    chat_id = str(args.chat_id)
    revision_id = getattr(args, "revision_id", None)
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_announcement_blocks(
            chat_id,
            revision_id=revision_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_announcement_blocks(
            chat_id,
            revision_id=revision_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=200,
    )


def _cmd_chat_announcement_get_block(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.get_announcement_block(
        str(args.chat_id),
        str(args.block_id),
        revision_id=getattr(args, "revision_id", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_chat_announcement_list_children(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    chat_id = str(args.chat_id)
    block_id = str(args.block_id)
    revision_id = getattr(args, "revision_id", None)
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_announcement_children(
            chat_id,
            block_id,
            revision_id=revision_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_announcement_children(
            chat_id,
            block_id,
            revision_id=revision_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=200,
    )


def _cmd_chat_announcement_create_children(args: argparse.Namespace) -> Mapping[str, Any]:
    children = _require_object_array(
        _parse_array_source(args, prefix="children", name="children", required=True),
        name="children",
    )
    service = ChatService(_build_client(args))
    return service.create_announcement_children(
        str(args.chat_id),
        str(args.block_id),
        children,
        revision_id=getattr(args, "revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_chat_announcement_batch_update(args: argparse.Namespace) -> Mapping[str, Any]:
    update_request = _parse_object_source(args, prefix="update", name="update", required=False)
    if not update_request:
        requests = _require_object_array(
            _parse_array_source(args, prefix="requests", name="requests", required=True),
            name="requests",
        )
        update_request = {"requests": requests}
    service = ChatService(_build_client(args))
    return service.batch_update_announcement_blocks(
        str(args.chat_id),
        update_request,
        revision_id=getattr(args, "revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_chat_announcement_delete_children(args: argparse.Namespace) -> Mapping[str, Any]:
    delete_range = _parse_object_source(args, prefix="delete_range", name="delete-range", required=False)
    if not delete_range:
        start_index = getattr(args, "start_index", None)
        end_index = getattr(args, "end_index", None)
        if start_index is None or end_index is None:
            raise ValueError(
                "provide delete range via --delete-range-json/--delete-range-file/--delete-range-stdin "
                "or use both --start-index and --end-index"
            )
        delete_range = {
            "start_index": start_index,
            "end_index": end_index,
        }
    service = ChatService(_build_client(args))
    return service.delete_announcement_children(
        str(args.chat_id),
        str(args.block_id),
        delete_range,
        revision_id=getattr(args, "revision_id", None),
        client_token=getattr(args, "client_token", None),
    )


def _cmd_chat_tab_create(args: argparse.Namespace) -> Mapping[str, Any]:
    tabs = _require_object_array(
        _parse_array_source(args, prefix="chat_tabs", name="chat-tabs", required=True),
        name="chat-tabs",
    )
    service = ChatService(_build_client(args))
    return service.create_tabs(str(args.chat_id), tabs)


def _cmd_chat_tab_update(args: argparse.Namespace) -> Mapping[str, Any]:
    tabs = _require_object_array(
        _parse_array_source(args, prefix="chat_tabs", name="chat-tabs", required=True),
        name="chat-tabs",
    )
    service = ChatService(_build_client(args))
    return service.update_tabs(str(args.chat_id), tabs)


def _cmd_chat_tab_sort(args: argparse.Namespace) -> Mapping[str, Any]:
    tab_ids = _parse_string_list_source(
        args,
        values_attr="tab_ids",
        prefix="tab_ids",
        name="tab-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.sort_tabs(str(args.chat_id), tab_ids)


def _cmd_chat_tab_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.list_tabs(str(args.chat_id))


def _cmd_chat_tab_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    tab_ids = _parse_string_list_source(
        args,
        values_attr="tab_ids",
        prefix="tab_ids",
        name="tab-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.delete_tabs(str(args.chat_id), tab_ids)


def _cmd_chat_menu_create(args: argparse.Namespace) -> Mapping[str, Any]:
    menu_tree = _parse_object_source(args, prefix="menu_tree", name="menu-tree", required=True)
    service = ChatService(_build_client(args))
    return service.create_menu(str(args.chat_id), menu_tree)


def _cmd_chat_menu_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ChatService(_build_client(args))
    return service.get_menu(str(args.chat_id))


def _cmd_chat_menu_update_item(args: argparse.Namespace) -> Mapping[str, Any]:
    menu_item_update = _parse_object_source(args, prefix="menu_update", name="menu-update", required=False)
    if not menu_item_update:
        chat_menu_item = _parse_object_source(args, prefix="menu_item", name="menu-item", required=True)
        update_fields = list(getattr(args, "update_fields", []) or [])
        if not update_fields:
            raise ValueError(
                "menu item update requires at least one --update-field when not using --menu-update-json"
            )
        menu_item_update = {
            "chat_menu_item": chat_menu_item,
            "update_fields": [str(value) for value in update_fields],
        }
    service = ChatService(_build_client(args))
    return service.update_menu_item(
        str(args.chat_id),
        str(args.menu_item_id),
        menu_item_update,
    )


def _cmd_chat_menu_sort(args: argparse.Namespace) -> Mapping[str, Any]:
    top_level_ids = _parse_string_list_source(
        args,
        values_attr="top_level_ids",
        prefix="top_level_ids",
        name="top-level-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.sort_menu(str(args.chat_id), top_level_ids)


def _cmd_chat_menu_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    top_level_ids = _parse_string_list_source(
        args,
        values_attr="top_level_ids",
        prefix="top_level_ids",
        name="top-level-id",
        required=True,
    )
    service = ChatService(_build_client(args))
    return service.delete_menu(str(args.chat_id), top_level_ids)


__all__ = [name for name in globals() if name.startswith("_cmd_")]
