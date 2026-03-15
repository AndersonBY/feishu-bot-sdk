from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Mapping, Optional, Sequence

from ..feishu import AsyncFeishuClient, FeishuClient
from ._common import (
    _drop_none,
    _has_more,
    _iter_items,
    _next_page_token,
    _normalize_mapping,
    _normalize_mappings,
    _normalize_strings,
    _unwrap_data,
)
from .rendering import LatexMode, render_markdown_email


MailRecipient = str | Mapping[str, object]


def _normalize_mail_recipient(value: MailRecipient, *, name: str) -> dict[str, object]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{name} must contain non-empty email addresses")
        return {"mail_address": text}

    payload = _normalize_mapping(value)
    if "mail_address" not in payload and "email" in payload:
        payload["mail_address"] = payload.pop("email")
    mail_address = payload.get("mail_address")
    if not isinstance(mail_address, str) or not mail_address.strip():
        raise ValueError(f"{name} items must include non-empty field mail_address")
    payload["mail_address"] = mail_address.strip()
    return payload


def _normalize_mail_recipients(
    values: Sequence[MailRecipient] | None,
    *,
    name: str,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for value in values or []:
        normalized.append(_normalize_mail_recipient(value, name=name))
    return normalized


def _encode_attachment_body(content: bytes) -> str:
    return base64.urlsafe_b64encode(content).decode("ascii")


def _build_inline_image_attachments(markdown: str, *, base_dir: str | Path | None, latex_mode: LatexMode) -> tuple[str, str, list[dict[str, object]]]:
    rendered = render_markdown_email(markdown, base_dir=base_dir, latex_mode=latex_mode)
    attachments = [
        {
            "body": _encode_attachment_body(image.content),
            "filename": image.filename,
            "is_inline": True,
            "cid": image.cid,
        }
        for image in rendered.inline_images
    ]
    return rendered.html, rendered.plain_text, attachments


def _build_markdown_message_payload(
    *,
    markdown: str,
    to: Sequence[MailRecipient] | None = None,
    cc: Sequence[MailRecipient] | None = None,
    bcc: Sequence[MailRecipient] | None = None,
    subject: str | None = None,
    attachments: Sequence[Mapping[str, object]] | None = None,
    dedupe_key: str | None = None,
    head_from: Mapping[str, object] | None = None,
    base_dir: str | Path | None = None,
    latex_mode: LatexMode = "auto",
) -> dict[str, object]:
    to_items = _normalize_mail_recipients(to, name="to")
    cc_items = _normalize_mail_recipients(cc, name="cc")
    bcc_items = _normalize_mail_recipients(bcc, name="bcc")
    if not to_items and not cc_items and not bcc_items:
        raise ValueError("at least one recipient is required across to, cc or bcc")

    body_html, body_plain_text, inline_attachments = _build_inline_image_attachments(
        markdown,
        base_dir=base_dir,
        latex_mode=latex_mode,
    )
    merged_attachments = [*_normalize_mappings(attachments, name="attachments")] if attachments else []
    merged_attachments.extend(inline_attachments)

    payload = _drop_none(
        {
            "subject": subject,
            "to": to_items or None,
            "cc": cc_items or None,
            "bcc": bcc_items or None,
            "body_html": body_html,
            "body_plain_text": body_plain_text,
            "attachments": merged_attachments or None,
            "dedupe_key": dedupe_key,
            "head_from": _normalize_mapping(head_from) if head_from is not None else None,
        }
    )
    return payload


class MailMailboxService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_aliases(self, user_mailbox_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/aliases",
        )
        return _unwrap_data(response)

    def create_alias(self, user_mailbox_id: str, email_alias: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/aliases",
            payload={"email_alias": _normalize_strings([email_alias], name="email_alias")[0]},
        )
        return _unwrap_data(response)

    def delete_alias(self, user_mailbox_id: str, alias_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/aliases/{alias_id}",
        )
        return _unwrap_data(response)

    def delete_from_recycle_bin(
        self,
        user_mailbox_id: str,
        *,
        transfer_mailbox: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}",
            params=_drop_none({"transfer_mailbox": transfer_mailbox}),
        )
        return _unwrap_data(response)


class MailMessageService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_messages(
        self,
        user_mailbox_id: str,
        *,
        folder_id: str,
        page_size: int = 20,
        page_token: Optional[str] = None,
        only_unread: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "folder_id": folder_id,
                "page_size": page_size,
                "page_token": page_token,
                "only_unread": only_unread,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages",
            params=params,
        )
        return _unwrap_data(response)

    def iter_messages(
        self,
        user_mailbox_id: str,
        *,
        folder_id: str,
        page_size: int = 20,
        only_unread: Optional[bool] = None,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_messages(
                user_mailbox_id,
                folder_id=folder_id,
                page_size=page_size,
                page_token=page_token,
                only_unread=only_unread,
            )
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_message(self, user_mailbox_id: str, message_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/{message_id}",
        )
        return _unwrap_data(response)

    def get_by_card(
        self,
        user_mailbox_id: str,
        *,
        card_id: str,
        owner_id: str,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "card_id": card_id,
                "owner_id": owner_id,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/get_by_card",
            params=params,
        )
        return _unwrap_data(response)

    def send_message(self, user_mailbox_id: str, message: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/send",
            payload=_normalize_mapping(message),
        )
        return _unwrap_data(response)

    def send_markdown(
        self,
        user_mailbox_id: str,
        *,
        markdown: str,
        to: Sequence[MailRecipient] | None = None,
        cc: Sequence[MailRecipient] | None = None,
        bcc: Sequence[MailRecipient] | None = None,
        subject: str | None = None,
        attachments: Sequence[Mapping[str, object]] | None = None,
        dedupe_key: str | None = None,
        head_from: Mapping[str, object] | None = None,
        base_dir: str | Path | None = None,
        latex_mode: LatexMode = "auto",
    ) -> Mapping[str, Any]:
        message = _build_markdown_message_payload(
            markdown=markdown,
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            attachments=attachments,
            dedupe_key=dedupe_key,
            head_from=head_from,
            base_dir=base_dir,
            latex_mode=latex_mode,
        )
        return self.send_message(user_mailbox_id, message)

    def get_attachment_download_urls(
        self,
        user_mailbox_id: str,
        message_id: str,
        attachment_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/{message_id}/attachments/download_url",
            params={"attachment_ids": _normalize_strings(attachment_ids, name="attachment_ids")},
        )
        return _unwrap_data(response)


class MailFolderService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_folders(
        self,
        user_mailbox_id: str,
        *,
        folder_type: Optional[int] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders",
            params=_drop_none({"folder_type": folder_type}),
        )
        return _unwrap_data(response)

    def iter_folders(
        self,
        user_mailbox_id: str,
        *,
        folder_type: Optional[int] = None,
    ) -> Iterator[Any]:
        data = self.list_folders(user_mailbox_id, folder_type=folder_type)
        yield from _iter_items(data)

    def create_folder(self, user_mailbox_id: str, folder: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders",
            payload=_normalize_mapping(folder),
        )
        return _unwrap_data(response)

    def update_folder(
        self,
        user_mailbox_id: str,
        folder_id: str,
        folder: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders/{folder_id}",
            payload=_normalize_mapping(folder),
        )
        return _unwrap_data(response)

    def delete_folder(self, user_mailbox_id: str, folder_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders/{folder_id}",
        )
        return _unwrap_data(response)


class MailContactService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_contacts(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    def iter_contacts(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_contacts(user_mailbox_id, page_size=page_size, page_token=page_token)
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_contact(self, user_mailbox_id: str, contact: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts",
            payload=_normalize_mapping(contact),
        )
        return _unwrap_data(response)

    def update_contact(
        self,
        user_mailbox_id: str,
        mail_contact_id: str,
        contact: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts/{mail_contact_id}",
            payload=_normalize_mapping(contact),
        )
        return _unwrap_data(response)

    def delete_contact(self, user_mailbox_id: str, mail_contact_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts/{mail_contact_id}",
        )
        return _unwrap_data(response)


class MailRuleService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_rules(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    def iter_rules(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_rules(user_mailbox_id, page_size=page_size, page_token=page_token)
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_rule(self, user_mailbox_id: str, rule: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules",
            payload=_normalize_mapping(rule),
        )
        return _unwrap_data(response)

    def update_rule(
        self,
        user_mailbox_id: str,
        rule_id: str,
        rule: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules/{rule_id}",
            payload=_normalize_mapping(rule),
        )
        return _unwrap_data(response)

    def delete_rule(self, user_mailbox_id: str, rule_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules/{rule_id}",
        )
        return _unwrap_data(response)

    def reorder_rules(self, user_mailbox_id: str, rule_ids: Sequence[str]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules/reorder",
            payload={"rule_ids": _normalize_strings(rule_ids, name="rule_ids")},
        )
        return _unwrap_data(response)


class MailEventService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_subscription(self, user_mailbox_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/event/subscription",
        )
        return _unwrap_data(response)

    def subscribe(self, user_mailbox_id: str, *, event_type: int = 1) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/event/subscribe",
            payload={"event_type": event_type},
        )
        return _unwrap_data(response)

    def unsubscribe(self, user_mailbox_id: str, *, event_type: int = 1) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/event/unsubscribe",
            payload={"event_type": event_type},
        )
        return _unwrap_data(response)


class MailAddressService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def query_status(self, email_list: Sequence[str]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/mail/v1/users/query",
            payload={"email_list": _normalize_strings(email_list, name="email_list")},
        )
        return _unwrap_data(response)


class AsyncMailMailboxService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_aliases(self, user_mailbox_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/aliases",
        )
        return _unwrap_data(response)

    async def create_alias(self, user_mailbox_id: str, email_alias: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/aliases",
            payload={"email_alias": _normalize_strings([email_alias], name="email_alias")[0]},
        )
        return _unwrap_data(response)

    async def delete_alias(self, user_mailbox_id: str, alias_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/aliases/{alias_id}",
        )
        return _unwrap_data(response)

    async def delete_from_recycle_bin(
        self,
        user_mailbox_id: str,
        *,
        transfer_mailbox: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}",
            params=_drop_none({"transfer_mailbox": transfer_mailbox}),
        )
        return _unwrap_data(response)


class AsyncMailMessageService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_messages(
        self,
        user_mailbox_id: str,
        *,
        folder_id: str,
        page_size: int = 20,
        page_token: Optional[str] = None,
        only_unread: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "folder_id": folder_id,
                "page_size": page_size,
                "page_token": page_token,
                "only_unread": only_unread,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_messages(
        self,
        user_mailbox_id: str,
        *,
        folder_id: str,
        page_size: int = 20,
        only_unread: Optional[bool] = None,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_messages(
                user_mailbox_id,
                folder_id=folder_id,
                page_size=page_size,
                page_token=page_token,
                only_unread=only_unread,
            )
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_message(self, user_mailbox_id: str, message_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/{message_id}",
        )
        return _unwrap_data(response)

    async def get_by_card(
        self,
        user_mailbox_id: str,
        *,
        card_id: str,
        owner_id: str,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "card_id": card_id,
                "owner_id": owner_id,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/get_by_card",
            params=params,
        )
        return _unwrap_data(response)

    async def send_message(self, user_mailbox_id: str, message: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/send",
            payload=_normalize_mapping(message),
        )
        return _unwrap_data(response)

    async def send_markdown(
        self,
        user_mailbox_id: str,
        *,
        markdown: str,
        to: Sequence[MailRecipient] | None = None,
        cc: Sequence[MailRecipient] | None = None,
        bcc: Sequence[MailRecipient] | None = None,
        subject: str | None = None,
        attachments: Sequence[Mapping[str, object]] | None = None,
        dedupe_key: str | None = None,
        head_from: Mapping[str, object] | None = None,
        base_dir: str | Path | None = None,
        latex_mode: LatexMode = "auto",
    ) -> Mapping[str, Any]:
        message = _build_markdown_message_payload(
            markdown=markdown,
            to=to,
            cc=cc,
            bcc=bcc,
            subject=subject,
            attachments=attachments,
            dedupe_key=dedupe_key,
            head_from=head_from,
            base_dir=base_dir,
            latex_mode=latex_mode,
        )
        return await self.send_message(user_mailbox_id, message)

    async def get_attachment_download_urls(
        self,
        user_mailbox_id: str,
        message_id: str,
        attachment_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/messages/{message_id}/attachments/download_url",
            params={"attachment_ids": _normalize_strings(attachment_ids, name="attachment_ids")},
        )
        return _unwrap_data(response)


class AsyncMailFolderService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_folders(
        self,
        user_mailbox_id: str,
        *,
        folder_type: Optional[int] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders",
            params=_drop_none({"folder_type": folder_type}),
        )
        return _unwrap_data(response)

    async def iter_folders(
        self,
        user_mailbox_id: str,
        *,
        folder_type: Optional[int] = None,
    ) -> AsyncIterator[Any]:
        data = await self.list_folders(user_mailbox_id, folder_type=folder_type)
        for item in _iter_items(data):
            yield item

    async def create_folder(self, user_mailbox_id: str, folder: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders",
            payload=_normalize_mapping(folder),
        )
        return _unwrap_data(response)

    async def update_folder(
        self,
        user_mailbox_id: str,
        folder_id: str,
        folder: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders/{folder_id}",
            payload=_normalize_mapping(folder),
        )
        return _unwrap_data(response)

    async def delete_folder(self, user_mailbox_id: str, folder_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/folders/{folder_id}",
        )
        return _unwrap_data(response)


class AsyncMailContactService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_contacts(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    async def iter_contacts(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_contacts(user_mailbox_id, page_size=page_size, page_token=page_token)
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def create_contact(self, user_mailbox_id: str, contact: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts",
            payload=_normalize_mapping(contact),
        )
        return _unwrap_data(response)

    async def update_contact(
        self,
        user_mailbox_id: str,
        mail_contact_id: str,
        contact: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts/{mail_contact_id}",
            payload=_normalize_mapping(contact),
        )
        return _unwrap_data(response)

    async def delete_contact(self, user_mailbox_id: str, mail_contact_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/mail_contacts/{mail_contact_id}",
        )
        return _unwrap_data(response)


class AsyncMailRuleService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_rules(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    async def iter_rules(
        self,
        user_mailbox_id: str,
        *,
        page_size: int = 20,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_rules(user_mailbox_id, page_size=page_size, page_token=page_token)
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def create_rule(self, user_mailbox_id: str, rule: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules",
            payload=_normalize_mapping(rule),
        )
        return _unwrap_data(response)

    async def update_rule(
        self,
        user_mailbox_id: str,
        rule_id: str,
        rule: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules/{rule_id}",
            payload=_normalize_mapping(rule),
        )
        return _unwrap_data(response)

    async def delete_rule(self, user_mailbox_id: str, rule_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules/{rule_id}",
        )
        return _unwrap_data(response)

    async def reorder_rules(self, user_mailbox_id: str, rule_ids: Sequence[str]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/rules/reorder",
            payload={"rule_ids": _normalize_strings(rule_ids, name="rule_ids")},
        )
        return _unwrap_data(response)


class AsyncMailEventService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_subscription(self, user_mailbox_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/event/subscription",
        )
        return _unwrap_data(response)

    async def subscribe(self, user_mailbox_id: str, *, event_type: int = 1) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/event/subscribe",
            payload={"event_type": event_type},
        )
        return _unwrap_data(response)

    async def unsubscribe(self, user_mailbox_id: str, *, event_type: int = 1) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{user_mailbox_id}/event/unsubscribe",
            payload={"event_type": event_type},
        )
        return _unwrap_data(response)


class AsyncMailAddressService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def query_status(self, email_list: Sequence[str]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/mail/v1/users/query",
            payload={"email_list": _normalize_strings(email_list, name="email_list")},
        )
        return _unwrap_data(response)


__all__ = [
    "AsyncMailAddressService",
    "AsyncMailContactService",
    "AsyncMailEventService",
    "AsyncMailFolderService",
    "AsyncMailMailboxService",
    "AsyncMailMessageService",
    "AsyncMailRuleService",
    "MailAddressService",
    "MailContactService",
    "MailEventService",
    "MailFolderService",
    "MailMailboxService",
    "MailMessageService",
    "MailRuleService",
]
