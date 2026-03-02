import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.im.content import MessageContent
from feishu_bot_sdk.im.media import AsyncMediaService, MediaService
from feishu_bot_sdk.im.messages import AsyncMessageService, MessageService


@dataclass
class _DummyResponse:
    status_code: int = 200
    json_data: Optional[Mapping[str, Any]] = None
    content: bytes = b""
    text: str = ""

    def json(self) -> Mapping[str, Any]:
        if self.json_data is None:
            raise ValueError("json unavailable")
        return self.json_data


class _SyncClientStub:
    def __init__(self, resolver: Optional[Any] = None) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(base_url="https://open.feishu.cn/open-apis", timeout_seconds=30.0)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "payload": dict(payload or {}),
                "params": dict(params or {}),
            }
        )
        if self._resolver is not None:
            return self._resolver(self.calls[-1])
        return {"code": 0, "data": {"ok": True}}

    def get_access_token(self) -> str:
        return "token"


class _AsyncClientStub:
    def __init__(self, resolver: Optional[Any] = None) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(base_url="https://open.feishu.cn/open-apis", timeout_seconds=30.0)

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "payload": dict(payload or {}),
                "params": dict(params or {}),
            }
        )
        if self._resolver is not None:
            return self._resolver(self.calls[-1])
        return {"code": 0, "data": {"ok": True}}

    async def get_access_token(self) -> str:
        return "token"


def test_message_send_builds_payload():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.send_text(receive_id_type="open_id", receive_id="ou_1", text="hello", uuid="u1")

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/im/v1/messages"
    assert call["params"] == {"receive_id_type": "open_id"}
    assert call["payload"]["receive_id"] == "ou_1"
    assert call["payload"]["msg_type"] == "text"
    assert call["payload"]["content"] == '{"text": "hello"}'
    assert call["payload"]["uuid"] == "u1"


def test_message_content_builders():
    post_payload = MessageContent.post_locale(
        locale="zh_cn",
        title="标题",
        content=[
            [MessageContent.post_text("hello"), MessageContent.post_at("ou_1")],
            [MessageContent.post_hr()],
        ],
    )
    interactive_payload = MessageContent.interactive_template(
        "ctp_1",
        template_version_name="1.0.0",
        template_variable={"name": "Tom"},
    )
    system_payload = MessageContent.system_divider(
        text="新会话",
        i18n_text={"zh_CN": "新会话", "en_US": "New Session"},
        need_rollup=True,
    )

    assert post_payload["zh_cn"]["title"] == "标题"
    assert post_payload["zh_cn"]["content"][0][0]["tag"] == "text"
    assert interactive_payload == {
        "type": "template",
        "data": {
            "template_id": "ctp_1",
            "template_version_name": "1.0.0",
            "template_variable": {"name": "Tom"},
        },
    }
    assert system_payload == {
        "type": "divider",
        "params": {
            "divider_text": {
                "text": "新会话",
                "i18n_text": {"zh_CN": "新会话", "en_US": "New Session"},
            }
        },
        "options": {"need_rollup": True},
    }


def test_message_send_convenience_methods_for_multiple_types():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.send_image(receive_id_type="open_id", receive_id="ou_1", image_key="img_1")
    service.send_file(receive_id_type="open_id", receive_id="ou_1", file_key="file_1")
    service.send_media(
        receive_id_type="open_id",
        receive_id="ou_1",
        file_key="file_video",
        image_key="img_cover",
    )
    service.send_system_divider(
        receive_id_type="open_id",
        receive_id="ou_1",
        text="新会话",
        need_rollup=True,
    )

    assert len(stub.calls) == 4
    assert stub.calls[0]["payload"]["msg_type"] == "image"
    assert stub.calls[0]["payload"]["content"] == '{"image_key": "img_1"}'
    assert stub.calls[1]["payload"]["msg_type"] == "file"
    assert stub.calls[1]["payload"]["content"] == '{"file_key": "file_1"}'
    assert stub.calls[2]["payload"]["msg_type"] == "media"
    assert stub.calls[2]["payload"]["content"] == '{"file_key": "file_video", "image_key": "img_cover"}'
    assert stub.calls[3]["payload"]["msg_type"] == "system"
    assert stub.calls[3]["payload"]["content"] == (
        '{"type": "divider", "params": {"divider_text": {"text": "新会话"}}, "options": {"need_rollup": true}}'
    )


def test_message_send_markdown_convenience_method():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.send_markdown(
        receive_id_type="open_id",
        receive_id="ou_1",
        markdown="### hello",
        locale="zh_cn",
        title="日报",
    )

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["payload"]["msg_type"] == "post"
    assert call["payload"]["content"] == (
        '{"zh_cn": {"content": [[{"tag": "md", "text": "### hello"}]], "title": "日报"}}'
    )


def test_message_reply_markdown_convenience_method():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.reply_markdown(
        "om_1",
        "### reply md",
        locale="zh_cn",
        title="回复",
    )

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["path"] == "/im/v1/messages/om_1/reply"
    assert call["payload"]["msg_type"] == "post"
    assert call["payload"]["content"] == (
        '{"zh_cn": {"content": [[{"tag": "md", "text": "### reply md"}]], "title": "回复"}}'
    )


def test_message_merge_forward_builds_params():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.merge_forward(
        receive_id_type="chat_id",
        receive_id="oc_1",
        message_id_list=["om_1", "om_2"],
        uuid="u2",
    )

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["path"] == "/im/v1/messages/merge_forward"
    assert call["params"] == {"receive_id_type": "chat_id", "uuid": "u2"}
    assert call["payload"] == {"receive_id": "oc_1", "message_id_list": ["om_1", "om_2"]}


def test_message_reaction_pin_and_batch_methods():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.add_reaction("om_1", "SMILE")
    service.list_reactions("om_1", reaction_type="SMILE", user_id_type="open_id", page_size=20)
    service.delete_reaction("om_1", "rec_1")
    service.pin_message("om_1")
    service.unpin_message("om_1")
    service.list_pins(chat_id="oc_1", page_size=10)
    service.send_batch_message(
        msg_type="interactive",
        card={"type": "template", "data": {"template_id": "ctp_xxx"}},
        open_ids=["ou_1"],
    )
    service.get_batch_message_progress("bm_1")
    service.get_batch_message_read_users("bm_1")
    service.delete_batch_message("bm_1")

    assert len(stub.calls) == 10
    assert stub.calls[0]["path"] == "/im/v1/messages/om_1/reactions"
    assert stub.calls[0]["payload"] == {"reaction_type": {"emoji_type": "SMILE"}}
    assert stub.calls[1]["params"] == {
        "reaction_type": "SMILE",
        "user_id_type": "open_id",
        "page_size": 20,
    }
    assert stub.calls[2]["path"] == "/im/v1/messages/om_1/reactions/rec_1"
    assert stub.calls[3]["path"] == "/im/v1/pins"
    assert stub.calls[4]["path"] == "/im/v1/pins/om_1"
    assert stub.calls[5]["params"] == {"chat_id": "oc_1", "page_size": 10}
    assert stub.calls[6]["path"] == "/message/v4/batch_send/"
    assert stub.calls[6]["payload"] == {
        "msg_type": "interactive",
        "card": {"type": "template", "data": {"template_id": "ctp_xxx"}},
        "open_ids": ["ou_1"],
    }
    assert stub.calls[7]["path"] == "/im/v1/batch_messages/bm_1/get_progress"
    assert stub.calls[8]["path"] == "/im/v1/batch_messages/bm_1/read_user"
    assert stub.calls[9]["path"] == "/im/v1/batch_messages/bm_1"


def test_message_urgent_and_card_methods():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.send_urgent_app("om_1", user_id_list=["ou_1"], user_id_type="open_id")
    service.send_urgent_sms("om_2", user_id_list=["ou_2"], user_id_type="user_id")
    service.send_urgent_phone("om_3", user_id_list=["ou_3"], user_id_type="union_id")
    service.patch_card("om_4", card={"type": "template", "data": {"template_id": "ctp_1"}})
    service.send_ephemeral_card(
        chat_id="oc_1",
        open_id="ou_1",
        card={"type": "template", "data": {"template_id": "ctp_1"}},
    )
    service.delete_ephemeral_card("om_5")
    service.delay_update_card("c-token", card={"elements": []})

    assert len(stub.calls) == 7
    assert stub.calls[0]["path"] == "/im/v1/messages/om_1/urgent_app"
    assert stub.calls[0]["params"] == {"user_id_type": "open_id"}
    assert stub.calls[0]["payload"] == {"user_id_list": ["ou_1"]}
    assert stub.calls[1]["path"] == "/im/v1/messages/om_2/urgent_sms"
    assert stub.calls[2]["path"] == "/im/v1/messages/om_3/urgent_phone"
    assert stub.calls[3]["path"] == "/im/v1/messages/om_4"
    assert stub.calls[3]["method"] == "PATCH"
    assert stub.calls[3]["payload"] == {
        "content": '{"type": "template", "data": {"template_id": "ctp_1"}}'
    }
    assert stub.calls[4]["path"] == "/ephemeral/v1/send"
    assert stub.calls[4]["payload"]["chat_id"] == "oc_1"
    assert stub.calls[5]["path"] == "/ephemeral/v1/delete"
    assert stub.calls[6]["path"] == "/interactive/v1/card/update"


def test_message_edit_includes_msg_type():
    stub = _SyncClientStub()
    service = MessageService(cast(FeishuClient, stub))

    service.edit("om_1", msg_type="text", content={"text": "updated"})

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["path"] == "/im/v1/messages/om_1"
    assert call["method"] == "PUT"
    assert call["payload"] == {"msg_type": "text", "content": '{"text": "updated"}'}


def test_message_get_unwraps_first_item():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "code": 0,
            "data": {
                "items": [
                    {
                        "message_id": "om_1",
                        "chat_id": "oc_1",
                    }
                ]
            },
        }

    stub = _SyncClientStub(resolver=resolver)
    service = MessageService(cast(FeishuClient, stub))

    response = service.get("om_1")

    assert response.ok is True
    assert response.message is not None
    assert response.message.message_id == "om_1"
    assert response.message.chat_id == "oc_1"


def test_message_send_returns_typed_response():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "code": 0,
            "msg": "ok",
            "data": {
                "message_id": "om_send_1",
                "chat_id": "oc_1",
                "msg_type": "text",
            },
        }

    stub = _SyncClientStub(resolver=resolver)
    service = MessageService(cast(FeishuClient, stub))

    response = service.send_text(
        receive_id_type="open_id",
        receive_id="ou_1",
        text="hello",
    )

    assert response.ok is True
    assert response.message is not None
    assert response.message.message_id == "om_send_1"
    assert response.message.msg_type == "text"


def test_media_upload_image_builds_multipart(monkeypatch: Any):
    captured: dict[str, Any] = {}

    def fake_request_raw(
        _self: MediaService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        captured["params"] = dict(params or {})
        return _DummyResponse(json_data={"code": 0, "data": {"image_key": "img_1"}})

    monkeypatch.setattr(MediaService, "_request_raw", fake_request_raw)
    service = MediaService(cast(FeishuClient, _SyncClientStub()))

    data = service.upload_image_bytes("test.png", b"abc", image_type="avatar")

    assert data == {"image_key": "img_1"}
    assert captured["method"] == "POST"
    assert captured["path"] == "/im/v1/images"
    assert captured["form_data"] == {"image_type": "avatar"}
    assert captured["params"] == {}
    file_part = captured["files"]["image"]
    assert file_part[0] == "test.png"
    assert file_part[1] == b"abc"
    assert file_part[2] == "image/png"


def test_media_download_message_resource_uses_query(monkeypatch: Any):
    captured: dict[str, Any] = {}

    def fake_request_raw(
        _self: MediaService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        captured["params"] = dict(params or {})
        return _DummyResponse(content=b"file-bytes")

    monkeypatch.setattr(MediaService, "_request_raw", fake_request_raw)
    service = MediaService(cast(FeishuClient, _SyncClientStub()))

    binary = service.download_message_resource("om_1", "file_1", resource_type="file")

    assert binary == b"file-bytes"
    assert captured["method"] == "GET"
    assert captured["path"] == "/im/v1/messages/om_1/resources/file_1"
    assert captured["params"] == {"type": "file"}


def test_async_message_reply_text():
    async def run() -> None:
        stub = _AsyncClientStub()
        service = AsyncMessageService(cast(AsyncFeishuClient, stub))

        await service.reply_text("om_1", "ok")

        assert len(stub.calls) == 1
        call = stub.calls[0]
        assert call["path"] == "/im/v1/messages/om_1/reply"
        assert call["payload"]["msg_type"] == "text"
        assert call["payload"]["content"] == '{"text": "ok"}'

    asyncio.run(run())


def test_async_message_advanced_methods():
    async def run() -> None:
        stub = _AsyncClientStub()
        service = AsyncMessageService(cast(AsyncFeishuClient, stub))

        await service.add_reaction("om_1", "OK")
        await service.send_urgent_app("om_1", user_id_list=["ou_1"], user_id_type="open_id")
        await service.send_ephemeral_card(
            chat_id="oc_1",
            open_id="ou_1",
            card={"type": "template", "data": {"template_id": "ctp_xxx"}},
        )
        await service.delay_update_card("c-token", card={"elements": []})

        assert len(stub.calls) == 4
        assert stub.calls[0]["path"] == "/im/v1/messages/om_1/reactions"
        assert stub.calls[1]["path"] == "/im/v1/messages/om_1/urgent_app"
        assert stub.calls[2]["path"] == "/ephemeral/v1/send"
        assert stub.calls[3]["path"] == "/interactive/v1/card/update"

    asyncio.run(run())


def test_async_message_send_convenience_methods():
    async def run() -> None:
        stub = _AsyncClientStub()
        service = AsyncMessageService(cast(AsyncFeishuClient, stub))

        await service.send_post(
            receive_id_type="open_id",
            receive_id="ou_1",
            post=MessageContent.post_locale(
                locale="zh_cn",
                content=[[MessageContent.post_text("hello")]],
            ),
        )
        await service.send_interactive(
            receive_id_type="open_id",
            receive_id="ou_1",
            interactive=MessageContent.interactive_card("card_1"),
        )

        assert len(stub.calls) == 2
        assert stub.calls[0]["payload"]["msg_type"] == "post"
        assert stub.calls[0]["payload"]["content"] == (
            '{"zh_cn": {"content": [[{"tag": "text", "text": "hello"}]]}}'
        )
        assert stub.calls[1]["payload"]["msg_type"] == "interactive"
        assert stub.calls[1]["payload"]["content"] == '{"type": "card", "data": {"card_id": "card_1"}}'

    asyncio.run(run())


def test_async_message_send_markdown_convenience_method():
    async def run() -> None:
        stub = _AsyncClientStub()
        service = AsyncMessageService(cast(AsyncFeishuClient, stub))

        await service.send_markdown(
            receive_id_type="open_id",
            receive_id="ou_1",
            markdown="**hello**",
        )

        assert len(stub.calls) == 1
        assert stub.calls[0]["payload"]["msg_type"] == "post"
        assert stub.calls[0]["payload"]["content"] == (
            '{"zh_cn": {"content": [[{"tag": "md", "text": "**hello**"}]]}}'
        )

    asyncio.run(run())


def test_async_message_reply_markdown_convenience_method():
    async def run() -> None:
        stub = _AsyncClientStub()
        service = AsyncMessageService(cast(AsyncFeishuClient, stub))

        await service.reply_markdown(
            "om_1",
            "**reply**",
        )

        assert len(stub.calls) == 1
        call = stub.calls[0]
        assert call["path"] == "/im/v1/messages/om_1/reply"
        assert call["payload"]["msg_type"] == "post"
        assert call["payload"]["content"] == (
            '{"zh_cn": {"content": [[{"tag": "md", "text": "**reply**"}]]}}'
        )

    asyncio.run(run())


def test_async_media_upload_file(monkeypatch: Any):
    captured: dict[str, Any] = {}

    async def fake_request_raw(
        _self: AsyncMediaService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        captured["params"] = dict(params or {})
        return _DummyResponse(json_data={"code": 0, "data": {"file_key": "file_1"}})

    monkeypatch.setattr(AsyncMediaService, "_request_raw", fake_request_raw)
    service = AsyncMediaService(cast(AsyncFeishuClient, _AsyncClientStub()))

    async def run() -> None:
        data = await service.upload_file_bytes(
            "report.pdf",
            b"pdf-bytes",
            file_type="pdf",
            duration=3000,
        )
        assert data == {"file_key": "file_1"}

    asyncio.run(run())
    assert captured["method"] == "POST"
    assert captured["path"] == "/im/v1/files"
    assert captured["form_data"] == {"file_type": "pdf", "file_name": "report.pdf", "duration": "3000"}
    assert captured["params"] == {}
    file_part = captured["files"]["file"]
    assert file_part[0] == "report.pdf"
    assert file_part[1] == b"pdf-bytes"
    assert file_part[2] == "application/pdf"
