from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable, Mapping

from ...mail import (
    MailAddressService,
    MailContactService,
    MailEventService,
    MailFolderService,
    MailGroupAliasService,
    MailGroupManagerService,
    MailGroupMemberService,
    MailGroupPermissionMemberService,
    MailGroupService,
    MailMailboxService,
    MailMessageService,
    MailRuleService,
    PublicMailboxAliasService,
    PublicMailboxMemberService,
    PublicMailboxService,
)
from ..runtime import _build_client, _parse_json_array, _parse_json_object, _resolve_text_input


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


def _parse_email_alias_source(
    args: argparse.Namespace,
    *,
    direct_attr: str = "email_alias",
    prefix: str = "alias",
) -> str:
    direct_value = getattr(args, direct_attr, None)
    if isinstance(direct_value, str) and direct_value.strip():
        return direct_value.strip()
    payload = _parse_object_source(args, prefix=prefix, name="alias", required=True)
    value = payload.get("email_alias")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError("alias body must include non-empty field email_alias")


def _parse_optional_object_source(
    args: argparse.Namespace,
    *,
    prefix: str,
    name: str,
) -> dict[str, Any] | None:
    payload = _parse_json_object(
        json_text=getattr(args, f"{prefix}_json", None),
        file_path=getattr(args, f"{prefix}_file", None),
        stdin_enabled=bool(getattr(args, f"{prefix}_stdin", False)),
        name=name,
        required=False,
    )
    return payload or None


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


def _parse_recipient_list_source(
    args: argparse.Namespace,
    *,
    values_attr: str,
    prefix: str,
    name: str,
) -> list[dict[str, Any]]:
    recipients: list[dict[str, Any]] = []

    direct_values = list(getattr(args, values_attr, []) or [])
    for value in direct_values:
        text = str(value).strip()
        if text:
            recipients.append({"mail_address": text})

    json_values = _parse_array_source(args, prefix=prefix, name=name, required=False)
    for value in json_values:
        if isinstance(value, str):
            text = value.strip()
            if text:
                recipients.append({"mail_address": text})
            continue
        if isinstance(value, Mapping):
            recipients.append({str(key): item for key, item in value.items()})
            continue
        raise ValueError(f"{name} must be a JSON array of strings or objects")

    return recipients


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


def _cmd_mailbox_alias_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailMailboxService(_build_client(args))
    return service.list_aliases(str(args.user_mailbox_id))


def _cmd_mailbox_alias_create(args: argparse.Namespace) -> Mapping[str, Any]:
    email_alias = _parse_email_alias_source(args)
    service = MailMailboxService(_build_client(args))
    return service.create_alias(str(args.user_mailbox_id), email_alias)


def _cmd_mailbox_alias_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailMailboxService(_build_client(args))
    return service.delete_alias(str(args.user_mailbox_id), str(args.alias_id))


def _cmd_mailbox_delete_from_recycle_bin(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailMailboxService(_build_client(args))
    return service.delete_from_recycle_bin(
        str(args.user_mailbox_id),
        transfer_mailbox=getattr(args, "transfer_mailbox", None),
    )


def _cmd_message_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailMessageService(_build_client(args))
    user_mailbox_id = str(args.user_mailbox_id)
    folder_id = str(args.folder_id)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    only_unread = True if bool(getattr(args, "only_unread", False)) else None
    if not bool(getattr(args, "all", False)):
        return service.list_messages(
            user_mailbox_id,
            folder_id=folder_id,
            page_size=page_size or 20,
            page_token=page_token,
            only_unread=only_unread,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_messages(
            user_mailbox_id,
            folder_id=folder_id,
            page_size=page_size,
            page_token=page_token,
            only_unread=only_unread,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=20,
    )


def _cmd_message_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailMessageService(_build_client(args))
    return service.get_message(str(args.user_mailbox_id), str(args.message_id))


def _cmd_message_get_by_card(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailMessageService(_build_client(args))
    return service.get_by_card(
        str(args.user_mailbox_id),
        card_id=str(args.card_id),
        owner_id=str(args.owner_id),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_message_send(args: argparse.Namespace) -> Mapping[str, Any]:
    message = _parse_object_source(args, prefix="message", name="message", required=True)
    service = MailMessageService(_build_client(args))
    return service.send_message(str(args.user_mailbox_id), message)


def _cmd_message_send_markdown(args: argparse.Namespace) -> Mapping[str, Any]:
    markdown_file = getattr(args, "markdown_file", None)
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=markdown_file,
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    base_dir_raw = getattr(args, "base_dir", None)
    if isinstance(base_dir_raw, str) and base_dir_raw.strip():
        base_dir: str | Path | None = base_dir_raw.strip()
    elif isinstance(markdown_file, str) and markdown_file.strip():
        base_dir = Path(markdown_file).resolve().parent
    else:
        base_dir = None

    to = _parse_recipient_list_source(args, values_attr="to_emails", prefix="to", name="to")
    cc = _parse_recipient_list_source(args, values_attr="cc_emails", prefix="cc", name="cc")
    bcc = _parse_recipient_list_source(args, values_attr="bcc_emails", prefix="bcc", name="bcc")
    if not to and not cc and not bcc:
        raise ValueError("at least one recipient is required across --to-email/--to-json, --cc-email/--cc-json or --bcc-email/--bcc-json")

    head_from_name = getattr(args, "head_from_name", None)
    head_from = {"name": head_from_name.strip()} if isinstance(head_from_name, str) and head_from_name.strip() else None

    service = MailMessageService(_build_client(args))
    return service.send_markdown(
        str(args.user_mailbox_id),
        markdown=markdown,
        to=to,
        cc=cc,
        bcc=bcc,
        subject=getattr(args, "subject", None),
        dedupe_key=getattr(args, "dedupe_key", None),
        head_from=head_from,
        base_dir=base_dir,
        latex_mode=getattr(args, "latex_mode", "auto"),  # type: ignore[arg-type]
    )


def _cmd_message_attachment_download_url(args: argparse.Namespace) -> Mapping[str, Any]:
    attachment_ids = _parse_string_list_source(
        args,
        values_attr="attachment_ids",
        prefix="attachment_ids",
        name="attachment-id",
        required=True,
    )
    service = MailMessageService(_build_client(args))
    return service.get_attachment_download_urls(
        str(args.user_mailbox_id),
        str(args.message_id),
        attachment_ids,
    )


def _cmd_folder_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailFolderService(_build_client(args))
    return service.list_folders(
        str(args.user_mailbox_id),
        folder_type=getattr(args, "folder_type", None),
    )


def _cmd_folder_create(args: argparse.Namespace) -> Mapping[str, Any]:
    folder = _parse_object_source(args, prefix="folder", name="folder", required=True)
    service = MailFolderService(_build_client(args))
    return service.create_folder(str(args.user_mailbox_id), folder)


def _cmd_folder_update(args: argparse.Namespace) -> Mapping[str, Any]:
    folder = _parse_object_source(args, prefix="folder", name="folder", required=True)
    service = MailFolderService(_build_client(args))
    return service.update_folder(str(args.user_mailbox_id), str(args.folder_id), folder)


def _cmd_folder_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailFolderService(_build_client(args))
    return service.delete_folder(str(args.user_mailbox_id), str(args.folder_id))


def _cmd_contact_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailContactService(_build_client(args))
    user_mailbox_id = str(args.user_mailbox_id)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_contacts(user_mailbox_id, page_size=page_size or 20, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_contacts(
            user_mailbox_id,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_contact_create(args: argparse.Namespace) -> Mapping[str, Any]:
    contact = _parse_object_source(args, prefix="contact", name="contact", required=True)
    service = MailContactService(_build_client(args))
    return service.create_contact(str(args.user_mailbox_id), contact)


def _cmd_contact_update(args: argparse.Namespace) -> Mapping[str, Any]:
    contact = _parse_object_source(args, prefix="contact", name="contact", required=True)
    service = MailContactService(_build_client(args))
    return service.update_contact(str(args.user_mailbox_id), str(args.mail_contact_id), contact)


def _cmd_contact_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailContactService(_build_client(args))
    return service.delete_contact(str(args.user_mailbox_id), str(args.mail_contact_id))


def _cmd_rule_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailRuleService(_build_client(args))
    user_mailbox_id = str(args.user_mailbox_id)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_rules(user_mailbox_id, page_size=page_size or 20, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_rules(
            user_mailbox_id,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_rule_create(args: argparse.Namespace) -> Mapping[str, Any]:
    rule = _parse_object_source(args, prefix="rule", name="rule", required=True)
    service = MailRuleService(_build_client(args))
    return service.create_rule(str(args.user_mailbox_id), rule)


def _cmd_rule_update(args: argparse.Namespace) -> Mapping[str, Any]:
    rule = _parse_object_source(args, prefix="rule", name="rule", required=True)
    service = MailRuleService(_build_client(args))
    return service.update_rule(str(args.user_mailbox_id), str(args.rule_id), rule)


def _cmd_rule_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailRuleService(_build_client(args))
    return service.delete_rule(str(args.user_mailbox_id), str(args.rule_id))


def _cmd_rule_reorder(args: argparse.Namespace) -> Mapping[str, Any]:
    rule_ids = _parse_string_list_source(
        args,
        values_attr="rule_ids",
        prefix="rule_ids",
        name="rule-id",
        required=True,
    )
    service = MailRuleService(_build_client(args))
    return service.reorder_rules(str(args.user_mailbox_id), rule_ids)


def _cmd_event_get_subscription(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailEventService(_build_client(args))
    return service.get_subscription(str(args.user_mailbox_id))


def _cmd_event_subscribe(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailEventService(_build_client(args))
    return service.subscribe(str(args.user_mailbox_id), event_type=int(args.event_type))


def _cmd_event_unsubscribe(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailEventService(_build_client(args))
    return service.unsubscribe(str(args.user_mailbox_id), event_type=int(args.event_type))


def _cmd_address_query_status(args: argparse.Namespace) -> Mapping[str, Any]:
    email_list = _parse_string_list_source(
        args,
        values_attr="email_list",
        prefix="email_list",
        name="email",
        required=True,
    )
    service = MailAddressService(_build_client(args))
    return service.query_status(email_list)


def _cmd_group_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_mailgroups(page_size=page_size, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_mailgroups(page_size=page_size, page_token=page_token),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_group_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupService(_build_client(args))
    return service.get_mailgroup(str(args.mailgroup_id))


def _cmd_group_create(args: argparse.Namespace) -> Mapping[str, Any]:
    mailgroup = _parse_object_source(args, prefix="mailgroup", name="mailgroup", required=True)
    service = MailGroupService(_build_client(args))
    return service.create_mailgroup(mailgroup)


def _cmd_group_update(args: argparse.Namespace) -> Mapping[str, Any]:
    mailgroup = _parse_object_source(args, prefix="mailgroup", name="mailgroup", required=True)
    service = MailGroupService(_build_client(args))
    return service.update_mailgroup(str(args.mailgroup_id), mailgroup)


def _cmd_group_replace(args: argparse.Namespace) -> Mapping[str, Any]:
    mailgroup = _parse_object_source(args, prefix="mailgroup", name="mailgroup", required=True)
    service = MailGroupService(_build_client(args))
    return service.replace_mailgroup(str(args.mailgroup_id), mailgroup)


def _cmd_group_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupService(_build_client(args))
    return service.delete_mailgroup(str(args.mailgroup_id))


def _cmd_group_alias_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupAliasService(_build_client(args))
    return service.list_aliases(str(args.mailgroup_id))


def _cmd_group_alias_create(args: argparse.Namespace) -> Mapping[str, Any]:
    alias = {"email_alias": _parse_email_alias_source(args)}
    service = MailGroupAliasService(_build_client(args))
    return service.create_alias(str(args.mailgroup_id), alias)


def _cmd_group_alias_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupAliasService(_build_client(args))
    return service.delete_alias(str(args.mailgroup_id), str(args.alias_id))


def _cmd_group_member_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupMemberService(_build_client(args))
    mailgroup_id = str(args.mailgroup_id)
    user_id_type = getattr(args, "user_id_type", None)
    department_id_type = getattr(args, "department_id_type", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_members(
            mailgroup_id,
            user_id_type=user_id_type,
            department_id_type=department_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_members(
            mailgroup_id,
            user_id_type=user_id_type,
            department_id_type=department_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_group_member_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupMemberService(_build_client(args))
    return service.get_member(
        str(args.mailgroup_id),
        str(args.member_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_member_create(args: argparse.Namespace) -> Mapping[str, Any]:
    member = _parse_object_source(args, prefix="member", name="member", required=True)
    service = MailGroupMemberService(_build_client(args))
    return service.create_member(
        str(args.mailgroup_id),
        member,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_member_batch_create(args: argparse.Namespace) -> Mapping[str, Any]:
    items = _require_object_array(
        _parse_array_source(args, prefix="items", name="items", required=True),
        name="items",
    )
    service = MailGroupMemberService(_build_client(args))
    return service.batch_create_members(
        str(args.mailgroup_id),
        items,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_member_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupMemberService(_build_client(args))
    return service.delete_member(
        str(args.mailgroup_id),
        str(args.member_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_member_batch_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    member_id_list = _parse_string_list_source(
        args,
        values_attr="member_ids",
        prefix="member_ids",
        name="member-id",
        required=True,
    )
    service = MailGroupMemberService(_build_client(args))
    return service.batch_delete_members(
        str(args.mailgroup_id),
        member_id_list,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_permission_member_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupPermissionMemberService(_build_client(args))
    mailgroup_id = str(args.mailgroup_id)
    user_id_type = getattr(args, "user_id_type", None)
    department_id_type = getattr(args, "department_id_type", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_permission_members(
            mailgroup_id,
            user_id_type=user_id_type,
            department_id_type=department_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_permission_members(
            mailgroup_id,
            user_id_type=user_id_type,
            department_id_type=department_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_group_permission_member_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupPermissionMemberService(_build_client(args))
    return service.get_permission_member(
        str(args.mailgroup_id),
        str(args.member_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_permission_member_create(args: argparse.Namespace) -> Mapping[str, Any]:
    member = _parse_object_source(args, prefix="member", name="member", required=True)
    service = MailGroupPermissionMemberService(_build_client(args))
    return service.create_permission_member(
        str(args.mailgroup_id),
        member,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_permission_member_batch_create(args: argparse.Namespace) -> Mapping[str, Any]:
    items = _require_object_array(
        _parse_array_source(args, prefix="items", name="items", required=True),
        name="items",
    )
    service = MailGroupPermissionMemberService(_build_client(args))
    return service.batch_create_permission_members(
        str(args.mailgroup_id),
        items,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_permission_member_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupPermissionMemberService(_build_client(args))
    return service.delete_permission_member(
        str(args.mailgroup_id),
        str(args.member_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_permission_member_batch_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    member_id_list = _parse_string_list_source(
        args,
        values_attr="member_ids",
        prefix="member_ids",
        name="member-id",
        required=True,
    )
    service = MailGroupPermissionMemberService(_build_client(args))
    return service.batch_delete_permission_members(
        str(args.mailgroup_id),
        member_id_list,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_group_manager_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailGroupManagerService(_build_client(args))
    mailgroup_id = str(args.mailgroup_id)
    user_id_type = getattr(args, "user_id_type", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_managers(
            mailgroup_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_managers(
            mailgroup_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_group_manager_batch_create(args: argparse.Namespace) -> Mapping[str, Any]:
    managers = _require_object_array(
        _parse_array_source(args, prefix="managers", name="managers", required=True),
        name="managers",
    )
    service = MailGroupManagerService(_build_client(args))
    return service.batch_create_managers(
        str(args.mailgroup_id),
        managers,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_group_manager_batch_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    managers = _require_object_array(
        _parse_array_source(args, prefix="managers", name="managers", required=True),
        name="managers",
    )
    service = MailGroupManagerService(_build_client(args))
    return service.batch_delete_managers(
        str(args.mailgroup_id),
        managers,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_public_mailbox_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_public_mailboxes(page_size=page_size, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_public_mailboxes(page_size=page_size, page_token=page_token),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_public_mailbox_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxService(_build_client(args))
    return service.get_public_mailbox(str(args.public_mailbox_id))


def _cmd_public_mailbox_create(args: argparse.Namespace) -> Mapping[str, Any]:
    public_mailbox = _parse_object_source(args, prefix="public_mailbox", name="public-mailbox", required=True)
    service = PublicMailboxService(_build_client(args))
    return service.create_public_mailbox(public_mailbox)


def _cmd_public_mailbox_update(args: argparse.Namespace) -> Mapping[str, Any]:
    public_mailbox = _parse_object_source(args, prefix="public_mailbox", name="public-mailbox", required=True)
    service = PublicMailboxService(_build_client(args))
    return service.update_public_mailbox(str(args.public_mailbox_id), public_mailbox)


def _cmd_public_mailbox_replace(args: argparse.Namespace) -> Mapping[str, Any]:
    public_mailbox = _parse_object_source(args, prefix="public_mailbox", name="public-mailbox", required=True)
    service = PublicMailboxService(_build_client(args))
    return service.replace_public_mailbox(str(args.public_mailbox_id), public_mailbox)


def _cmd_public_mailbox_remove_to_recycle_bin(args: argparse.Namespace) -> Mapping[str, Any]:
    options = _parse_optional_object_source(args, prefix="options", name="options")
    to_mail_address = getattr(args, "to_mail_address", None)
    if isinstance(to_mail_address, str) and to_mail_address.strip():
        options = {**(options or {}), "to_mail_address": to_mail_address.strip()}
    service = PublicMailboxService(_build_client(args))
    return service.remove_to_recycle_bin(str(args.public_mailbox_id), options)


def _cmd_public_mailbox_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxService(_build_client(args))
    return service.delete_public_mailbox(str(args.public_mailbox_id))


def _cmd_public_mailbox_alias_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxAliasService(_build_client(args))
    return service.list_aliases(str(args.public_mailbox_id))


def _cmd_public_mailbox_alias_create(args: argparse.Namespace) -> Mapping[str, Any]:
    alias = {"email_alias": _parse_email_alias_source(args)}
    service = PublicMailboxAliasService(_build_client(args))
    return service.create_alias(str(args.public_mailbox_id), alias)


def _cmd_public_mailbox_alias_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxAliasService(_build_client(args))
    return service.delete_alias(str(args.public_mailbox_id), str(args.alias_id))


def _cmd_public_mailbox_member_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxMemberService(_build_client(args))
    public_mailbox_id = str(args.public_mailbox_id)
    user_id_type = getattr(args, "user_id_type", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_members(
            public_mailbox_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_members(
            public_mailbox_id,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_public_mailbox_member_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxMemberService(_build_client(args))
    return service.get_member(
        str(args.public_mailbox_id),
        str(args.member_id),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_public_mailbox_member_create(args: argparse.Namespace) -> Mapping[str, Any]:
    member = _parse_object_source(args, prefix="member", name="member", required=True)
    service = PublicMailboxMemberService(_build_client(args))
    return service.create_member(
        str(args.public_mailbox_id),
        member,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_public_mailbox_member_batch_create(args: argparse.Namespace) -> Mapping[str, Any]:
    items = _require_object_array(
        _parse_array_source(args, prefix="items", name="items", required=True),
        name="items",
    )
    service = PublicMailboxMemberService(_build_client(args))
    return service.batch_create_members(
        str(args.public_mailbox_id),
        items,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_public_mailbox_member_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxMemberService(_build_client(args))
    return service.delete_member(
        str(args.public_mailbox_id),
        str(args.member_id),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_public_mailbox_member_batch_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    member_id_list = _parse_string_list_source(
        args,
        values_attr="member_ids",
        prefix="member_ids",
        name="member-id",
        required=True,
    )
    service = PublicMailboxMemberService(_build_client(args))
    return service.batch_delete_members(
        str(args.public_mailbox_id),
        member_id_list,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_public_mailbox_member_clear(args: argparse.Namespace) -> Mapping[str, Any]:
    service = PublicMailboxMemberService(_build_client(args))
    return service.clear_members(str(args.public_mailbox_id))


__all__ = [name for name in globals() if name.startswith("_cmd_")]
