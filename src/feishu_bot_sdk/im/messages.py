import json
from typing import Any, Mapping, Optional, Sequence

from ..feishu import AsyncFeishuClient, FeishuClient
from .content import MessageContent


class MessageService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def reply_text(self, message_id: str, text: str) -> Mapping[str, Any]:
        return self.reply(
            message_id,
            msg_type="text",
            content={"text": text},
        )

    def send_text(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        text: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="text",
            content={"text": text},
            uuid=uuid,
        )

    def send_post(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        post: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="post",
            content=post,
            uuid=uuid,
        )

    def send_markdown(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        markdown: str,
        locale: str = "zh_cn",
        title: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        post = MessageContent.post_locale(
            locale=locale,
            title=title,
            content=[[MessageContent.post_md(markdown)]],
        )
        return self.send_post(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            post=post,
            uuid=uuid,
        )

    def send_image(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        image_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="image",
            content=MessageContent.image(image_key),
            uuid=uuid,
        )

    def send_interactive(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        interactive: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="interactive",
            content=interactive,
            uuid=uuid,
        )

    def send_share_chat(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        chat_id: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="share_chat",
            content=MessageContent.share_chat(chat_id),
            uuid=uuid,
        )

    def send_share_user(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        user_open_id: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="share_user",
            content=MessageContent.share_user(user_open_id),
            uuid=uuid,
        )

    def send_audio(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="audio",
            content=MessageContent.audio(file_key),
            uuid=uuid,
        )

    def send_media(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        image_key: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="media",
            content=MessageContent.media(file_key, image_key=image_key),
            uuid=uuid,
        )

    def send_file(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="file",
            content=MessageContent.file(file_key),
            uuid=uuid,
        )

    def send_sticker(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="sticker",
            content=MessageContent.sticker(file_key),
            uuid=uuid,
        )

    def send_system(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        system: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="system",
            content=system,
            uuid=uuid,
        )

    def send_system_divider(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        text: str,
        i18n_text: Optional[Mapping[str, str]] = None,
        need_rollup: Optional[bool] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="system",
            content=MessageContent.system_divider(
                text=text,
                i18n_text=i18n_text,
                need_rollup=need_rollup,
            ),
            uuid=uuid,
        )

    def send(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": _serialize_content(content),
        }
        if uuid:
            payload["uuid"] = uuid
        response = self._client.request_json(
            "POST",
            "/im/v1/messages",
            payload=payload,
            params={"receive_id_type": receive_id_type},
        )
        return _unwrap_data(response)

    def reply(
        self,
        message_id: str,
        *,
        msg_type: str,
        content: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "msg_type": msg_type,
            "content": _serialize_content(content),
        }
        if uuid:
            payload["uuid"] = uuid
        response = self._client.request_json(
            "POST",
            f"/im/v1/messages/{message_id}/reply",
            payload=payload,
        )
        return _unwrap_data(response)

    def edit(
        self,
        message_id: str,
        *,
        msg_type: str = "text",
        content: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/im/v1/messages/{message_id}",
            payload={
                "msg_type": msg_type,
                "content": _serialize_content(content),
            },
        )
        return _unwrap_data(response)

    def recall(self, message_id: str) -> None:
        self._client.request_json("DELETE", f"/im/v1/messages/{message_id}")

    def get(self, message_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/im/v1/messages/{message_id}",
        )
        return _unwrap_single_item(response)

    def list_history(
        self,
        *,
        container_id_type: str,
        container_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sort_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params: dict[str, Any] = {
            "container_id_type": container_id_type,
            "container_id": container_id,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if sort_type:
            params["sort_type"] = sort_type
        if page_size is not None:
            params["page_size"] = page_size
        if page_token:
            params["page_token"] = page_token
        response = self._client.request_json("GET", "/im/v1/messages", params=params)
        return _unwrap_data(response)

    def query_read_users(
        self,
        message_id: str,
        *,
        user_id_type: str = "open_id",
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params: dict[str, Any] = {"user_id_type": user_id_type}
        if page_size is not None:
            params["page_size"] = page_size
        if page_token:
            params["page_token"] = page_token
        response = self._client.request_json(
            "GET",
            f"/im/v1/messages/{message_id}/read_users",
            params=params,
        )
        return _unwrap_data(response)

    def forward(
        self,
        message_id: str,
        *,
        receive_id_type: str,
        receive_id: str,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/im/v1/messages/{message_id}/forward",
            payload={"receive_id": receive_id},
            params={"receive_id_type": receive_id_type},
        )
        return _unwrap_data(response)

    def merge_forward(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        message_id_list: list[str],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "receive_id": receive_id,
            "message_id_list": list(message_id_list),
        }
        params: dict[str, Any] = {"receive_id_type": receive_id_type}
        if uuid:
            params["uuid"] = uuid
        response = self._client.request_json(
            "POST",
            "/im/v1/messages/merge_forward",
            payload=payload,
            params=params,
        )
        return _unwrap_data(response)

    def add_reaction(self, message_id: str, emoji_type: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/im/v1/messages/{message_id}/reactions",
            payload={"reaction_type": {"emoji_type": emoji_type}},
        )
        return _unwrap_data(response)

    def list_reactions(
        self,
        message_id: str,
        *,
        reaction_type: Optional[str] = None,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "reaction_type": reaction_type,
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/im/v1/messages/{message_id}/reactions",
            params=params,
        )
        return _unwrap_data(response)

    def delete_reaction(self, message_id: str, reaction_id: str) -> None:
        self._client.request_json(
            "DELETE",
            f"/im/v1/messages/{message_id}/reactions/{reaction_id}",
        )

    def pin_message(self, message_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/im/v1/pins",
            payload={"message_id": message_id},
        )
        return _unwrap_data(response)

    def unpin_message(self, message_id: str) -> None:
        self._client.request_json("DELETE", f"/im/v1/pins/{message_id}")

    def list_pins(
        self,
        *,
        chat_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "chat_id": chat_id,
                "start_time": start_time,
                "end_time": end_time,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json("GET", "/im/v1/pins", params=params)
        return _unwrap_data(response)

    def send_batch(self, payload: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/message/v4/batch_send/",
            payload=dict(payload),
        )
        return _unwrap_data(response)

    def send_batch_message(
        self,
        *,
        msg_type: str,
        content: Optional[Mapping[str, object]] = None,
        card: Optional[Mapping[str, object]] = None,
        department_ids: Optional[Sequence[str]] = None,
        open_ids: Optional[Sequence[str]] = None,
        user_ids: Optional[Sequence[str]] = None,
        union_ids: Optional[Sequence[str]] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {"msg_type": msg_type}
        if content is not None:
            payload["content"] = dict(content)
        if card is not None:
            payload["card"] = dict(card)
        if department_ids is not None:
            payload["department_ids"] = list(department_ids)
        if open_ids is not None:
            payload["open_ids"] = list(open_ids)
        if user_ids is not None:
            payload["user_ids"] = list(user_ids)
        if union_ids is not None:
            payload["union_ids"] = list(union_ids)
        return self.send_batch(payload)

    def delete_batch_message(self, batch_message_id: str) -> None:
        self._client.request_json(
            "DELETE",
            f"/im/v1/batch_messages/{batch_message_id}",
        )

    def get_batch_message_progress(self, batch_message_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/im/v1/batch_messages/{batch_message_id}/get_progress",
        )
        return _unwrap_data(response)

    def get_batch_message_read_users(self, batch_message_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/im/v1/batch_messages/{batch_message_id}/read_user",
        )
        return _unwrap_data(response)

    def send_urgent_app(
        self,
        message_id: str,
        *,
        user_id_list: Sequence[str],
        user_id_type: str = "open_id",
    ) -> Mapping[str, Any]:
        return self._send_urgent(
            message_id,
            urgent_type="urgent_app",
            user_id_list=user_id_list,
            user_id_type=user_id_type,
        )

    def send_urgent_sms(
        self,
        message_id: str,
        *,
        user_id_list: Sequence[str],
        user_id_type: str = "open_id",
    ) -> Mapping[str, Any]:
        return self._send_urgent(
            message_id,
            urgent_type="urgent_sms",
            user_id_list=user_id_list,
            user_id_type=user_id_type,
        )

    def send_urgent_phone(
        self,
        message_id: str,
        *,
        user_id_list: Sequence[str],
        user_id_type: str = "open_id",
    ) -> Mapping[str, Any]:
        return self._send_urgent(
            message_id,
            urgent_type="urgent_phone",
            user_id_list=user_id_list,
            user_id_type=user_id_type,
        )

    def patch_card(self, message_id: str, *, card: Mapping[str, Any]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/im/v1/messages/{message_id}",
            payload={"content": _serialize_content(card)},
        )
        return _unwrap_data(response)

    def send_ephemeral_card(
        self,
        *,
        chat_id: str,
        card: Mapping[str, Any],
        open_id: Optional[str] = None,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "msg_type": "interactive",
            "card": dict(card),
        }
        if open_id is not None:
            payload["open_id"] = open_id
        if user_id is not None:
            payload["user_id"] = user_id
        if email is not None:
            payload["email"] = email
        response = self._client.request_json("POST", "/ephemeral/v1/send", payload=payload)
        return _unwrap_data(response)

    def delete_ephemeral_card(self, message_id: str) -> None:
        self._client.request_json(
            "POST",
            "/ephemeral/v1/delete",
            payload={"message_id": message_id},
        )

    def delay_update_card(self, token: str, *, card: Mapping[str, Any]) -> None:
        self._client.request_json(
            "POST",
            "/interactive/v1/card/update",
            payload={"token": token, "card": dict(card)},
        )

    def _send_urgent(
        self,
        message_id: str,
        *,
        urgent_type: str,
        user_id_list: Sequence[str],
        user_id_type: str,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/im/v1/messages/{message_id}/{urgent_type}",
            params={"user_id_type": user_id_type},
            payload={"user_id_list": list(user_id_list)},
        )
        return _unwrap_data(response)


class AsyncMessageService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def reply_text(self, message_id: str, text: str) -> Mapping[str, Any]:
        return await self.reply(
            message_id,
            msg_type="text",
            content={"text": text},
        )

    async def send_text(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        text: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="text",
            content={"text": text},
            uuid=uuid,
        )

    async def send_post(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        post: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="post",
            content=post,
            uuid=uuid,
        )

    async def send_markdown(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        markdown: str,
        locale: str = "zh_cn",
        title: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        post = MessageContent.post_locale(
            locale=locale,
            title=title,
            content=[[MessageContent.post_md(markdown)]],
        )
        return await self.send_post(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            post=post,
            uuid=uuid,
        )

    async def send_image(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        image_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="image",
            content=MessageContent.image(image_key),
            uuid=uuid,
        )

    async def send_interactive(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        interactive: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="interactive",
            content=interactive,
            uuid=uuid,
        )

    async def send_share_chat(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        chat_id: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="share_chat",
            content=MessageContent.share_chat(chat_id),
            uuid=uuid,
        )

    async def send_share_user(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        user_open_id: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="share_user",
            content=MessageContent.share_user(user_open_id),
            uuid=uuid,
        )

    async def send_audio(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="audio",
            content=MessageContent.audio(file_key),
            uuid=uuid,
        )

    async def send_media(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        image_key: Optional[str] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="media",
            content=MessageContent.media(file_key, image_key=image_key),
            uuid=uuid,
        )

    async def send_file(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="file",
            content=MessageContent.file(file_key),
            uuid=uuid,
        )

    async def send_sticker(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        file_key: str,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="sticker",
            content=MessageContent.sticker(file_key),
            uuid=uuid,
        )

    async def send_system(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        system: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="system",
            content=system,
            uuid=uuid,
        )

    async def send_system_divider(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        text: str,
        i18n_text: Optional[Mapping[str, str]] = None,
        need_rollup: Optional[bool] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.send(
            receive_id_type=receive_id_type,
            receive_id=receive_id,
            msg_type="system",
            content=MessageContent.system_divider(
                text=text,
                i18n_text=i18n_text,
                need_rollup=need_rollup,
            ),
            uuid=uuid,
        )

    async def send(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        msg_type: str,
        content: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": _serialize_content(content),
        }
        if uuid:
            payload["uuid"] = uuid
        response = await self._client.request_json(
            "POST",
            "/im/v1/messages",
            payload=payload,
            params={"receive_id_type": receive_id_type},
        )
        return _unwrap_data(response)

    async def reply(
        self,
        message_id: str,
        *,
        msg_type: str,
        content: Mapping[str, Any],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "msg_type": msg_type,
            "content": _serialize_content(content),
        }
        if uuid:
            payload["uuid"] = uuid
        response = await self._client.request_json(
            "POST",
            f"/im/v1/messages/{message_id}/reply",
            payload=payload,
        )
        return _unwrap_data(response)

    async def edit(
        self,
        message_id: str,
        *,
        msg_type: str = "text",
        content: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/im/v1/messages/{message_id}",
            payload={
                "msg_type": msg_type,
                "content": _serialize_content(content),
            },
        )
        return _unwrap_data(response)

    async def recall(self, message_id: str) -> None:
        await self._client.request_json("DELETE", f"/im/v1/messages/{message_id}")

    async def get(self, message_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/im/v1/messages/{message_id}",
        )
        return _unwrap_single_item(response)

    async def list_history(
        self,
        *,
        container_id_type: str,
        container_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sort_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params: dict[str, Any] = {
            "container_id_type": container_id_type,
            "container_id": container_id,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if sort_type:
            params["sort_type"] = sort_type
        if page_size is not None:
            params["page_size"] = page_size
        if page_token:
            params["page_token"] = page_token
        response = await self._client.request_json("GET", "/im/v1/messages", params=params)
        return _unwrap_data(response)

    async def query_read_users(
        self,
        message_id: str,
        *,
        user_id_type: str = "open_id",
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params: dict[str, Any] = {"user_id_type": user_id_type}
        if page_size is not None:
            params["page_size"] = page_size
        if page_token:
            params["page_token"] = page_token
        response = await self._client.request_json(
            "GET",
            f"/im/v1/messages/{message_id}/read_users",
            params=params,
        )
        return _unwrap_data(response)

    async def forward(
        self,
        message_id: str,
        *,
        receive_id_type: str,
        receive_id: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/messages/{message_id}/forward",
            payload={"receive_id": receive_id},
            params={"receive_id_type": receive_id_type},
        )
        return _unwrap_data(response)

    async def merge_forward(
        self,
        *,
        receive_id_type: str,
        receive_id: str,
        message_id_list: list[str],
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, Any] = {
            "receive_id": receive_id,
            "message_id_list": list(message_id_list),
        }
        params: dict[str, Any] = {"receive_id_type": receive_id_type}
        if uuid:
            params["uuid"] = uuid
        response = await self._client.request_json(
            "POST",
            "/im/v1/messages/merge_forward",
            payload=payload,
            params=params,
        )
        return _unwrap_data(response)

    async def add_reaction(self, message_id: str, emoji_type: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/messages/{message_id}/reactions",
            payload={"reaction_type": {"emoji_type": emoji_type}},
        )
        return _unwrap_data(response)

    async def list_reactions(
        self,
        message_id: str,
        *,
        reaction_type: Optional[str] = None,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "reaction_type": reaction_type,
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/im/v1/messages/{message_id}/reactions",
            params=params,
        )
        return _unwrap_data(response)

    async def delete_reaction(self, message_id: str, reaction_id: str) -> None:
        await self._client.request_json(
            "DELETE",
            f"/im/v1/messages/{message_id}/reactions/{reaction_id}",
        )

    async def pin_message(self, message_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/im/v1/pins",
            payload={"message_id": message_id},
        )
        return _unwrap_data(response)

    async def unpin_message(self, message_id: str) -> None:
        await self._client.request_json("DELETE", f"/im/v1/pins/{message_id}")

    async def list_pins(
        self,
        *,
        chat_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "chat_id": chat_id,
                "start_time": start_time,
                "end_time": end_time,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/im/v1/pins", params=params)
        return _unwrap_data(response)

    async def send_batch(self, payload: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/message/v4/batch_send/",
            payload=dict(payload),
        )
        return _unwrap_data(response)

    async def send_batch_message(
        self,
        *,
        msg_type: str,
        content: Optional[Mapping[str, object]] = None,
        card: Optional[Mapping[str, object]] = None,
        department_ids: Optional[Sequence[str]] = None,
        open_ids: Optional[Sequence[str]] = None,
        user_ids: Optional[Sequence[str]] = None,
        union_ids: Optional[Sequence[str]] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {"msg_type": msg_type}
        if content is not None:
            payload["content"] = dict(content)
        if card is not None:
            payload["card"] = dict(card)
        if department_ids is not None:
            payload["department_ids"] = list(department_ids)
        if open_ids is not None:
            payload["open_ids"] = list(open_ids)
        if user_ids is not None:
            payload["user_ids"] = list(user_ids)
        if union_ids is not None:
            payload["union_ids"] = list(union_ids)
        return await self.send_batch(payload)

    async def delete_batch_message(self, batch_message_id: str) -> None:
        await self._client.request_json(
            "DELETE",
            f"/im/v1/batch_messages/{batch_message_id}",
        )

    async def get_batch_message_progress(self, batch_message_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/im/v1/batch_messages/{batch_message_id}/get_progress",
        )
        return _unwrap_data(response)

    async def get_batch_message_read_users(self, batch_message_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/im/v1/batch_messages/{batch_message_id}/read_user",
        )
        return _unwrap_data(response)

    async def send_urgent_app(
        self,
        message_id: str,
        *,
        user_id_list: Sequence[str],
        user_id_type: str = "open_id",
    ) -> Mapping[str, Any]:
        return await self._send_urgent(
            message_id,
            urgent_type="urgent_app",
            user_id_list=user_id_list,
            user_id_type=user_id_type,
        )

    async def send_urgent_sms(
        self,
        message_id: str,
        *,
        user_id_list: Sequence[str],
        user_id_type: str = "open_id",
    ) -> Mapping[str, Any]:
        return await self._send_urgent(
            message_id,
            urgent_type="urgent_sms",
            user_id_list=user_id_list,
            user_id_type=user_id_type,
        )

    async def send_urgent_phone(
        self,
        message_id: str,
        *,
        user_id_list: Sequence[str],
        user_id_type: str = "open_id",
    ) -> Mapping[str, Any]:
        return await self._send_urgent(
            message_id,
            urgent_type="urgent_phone",
            user_id_list=user_id_list,
            user_id_type=user_id_type,
        )

    async def patch_card(self, message_id: str, *, card: Mapping[str, Any]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/im/v1/messages/{message_id}",
            payload={"content": _serialize_content(card)},
        )
        return _unwrap_data(response)

    async def send_ephemeral_card(
        self,
        *,
        chat_id: str,
        card: Mapping[str, Any],
        open_id: Optional[str] = None,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "msg_type": "interactive",
            "card": dict(card),
        }
        if open_id is not None:
            payload["open_id"] = open_id
        if user_id is not None:
            payload["user_id"] = user_id
        if email is not None:
            payload["email"] = email
        response = await self._client.request_json("POST", "/ephemeral/v1/send", payload=payload)
        return _unwrap_data(response)

    async def delete_ephemeral_card(self, message_id: str) -> None:
        await self._client.request_json(
            "POST",
            "/ephemeral/v1/delete",
            payload={"message_id": message_id},
        )

    async def delay_update_card(self, token: str, *, card: Mapping[str, Any]) -> None:
        await self._client.request_json(
            "POST",
            "/interactive/v1/card/update",
            payload={"token": token, "card": dict(card)},
        )

    async def _send_urgent(
        self,
        message_id: str,
        *,
        urgent_type: str,
        user_id_list: Sequence[str],
        user_id_type: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/im/v1/messages/{message_id}/{urgent_type}",
            params={"user_id_type": user_id_type},
            payload={"user_id_list": list(user_id_list)},
        )
        return _unwrap_data(response)


def _serialize_content(content: Mapping[str, Any]) -> str:
    return json.dumps(dict(content), ensure_ascii=False)


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return data
    return {}


def _unwrap_single_item(response: Mapping[str, Any]) -> Mapping[str, Any]:
    data = _unwrap_data(response)
    items = data.get("items")
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, Mapping):
            return dict(first)
    return data
