from typing import Any, Mapping, Optional, Sequence


class MessageContent:
    @staticmethod
    def text(text: str) -> dict[str, str]:
        return {"text": text}

    @staticmethod
    def post(locales: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        return {str(k): dict(v) for k, v in locales.items()}

    @staticmethod
    def post_locale(
        *,
        locale: str = "zh_cn",
        title: Optional[str] = None,
        content: Sequence[Sequence[Mapping[str, Any]]],
    ) -> dict[str, Any]:
        locale_payload: dict[str, Any] = {
            "content": [[dict(node) for node in line] for line in content],
        }
        if title is not None:
            locale_payload["title"] = title
        return {locale: locale_payload}

    @staticmethod
    def post_text(
        text: str,
        *,
        un_escape: Optional[bool] = None,
        style: Optional[Sequence[str]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "text", "text": text}
        if un_escape is not None:
            payload["un_escape"] = un_escape
        if style:
            payload["style"] = list(style)
        return payload

    @staticmethod
    def post_link(
        text: str,
        href: str,
        *,
        style: Optional[Sequence[str]] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "a", "text": text, "href": href}
        if style:
            payload["style"] = list(style)
        return payload

    @staticmethod
    def post_at(user_id: str, *, style: Optional[Sequence[str]] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "at", "user_id": user_id}
        if style:
            payload["style"] = list(style)
        return payload

    @staticmethod
    def post_image(image_key: str) -> dict[str, str]:
        return {"tag": "img", "image_key": image_key}

    @staticmethod
    def post_media(file_key: str, *, image_key: Optional[str] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "media", "file_key": file_key}
        if image_key is not None:
            payload["image_key"] = image_key
        return payload

    @staticmethod
    def post_emotion(emoji_type: str) -> dict[str, str]:
        return {"tag": "emotion", "emoji_type": emoji_type}

    @staticmethod
    def post_code_block(text: str, *, language: Optional[str] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"tag": "code_block", "text": text}
        if language is not None:
            payload["language"] = language
        return payload

    @staticmethod
    def post_hr() -> dict[str, str]:
        return {"tag": "hr"}

    @staticmethod
    def post_md(text: str) -> dict[str, str]:
        return {"tag": "md", "text": text}

    @staticmethod
    def image(image_key: str) -> dict[str, str]:
        return {"image_key": image_key}

    @staticmethod
    def interactive(payload: Mapping[str, Any]) -> dict[str, Any]:
        return dict(payload)

    @staticmethod
    def interactive_card(card_id: str) -> dict[str, Any]:
        return {"type": "card", "data": {"card_id": card_id}}

    @staticmethod
    def interactive_template(
        template_id: str,
        *,
        template_version_name: Optional[str] = None,
        template_variable: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"template_id": template_id}
        if template_version_name is not None:
            data["template_version_name"] = template_version_name
        if template_variable is not None:
            data["template_variable"] = dict(template_variable)
        return {"type": "template", "data": data}

    @staticmethod
    def share_chat(chat_id: str) -> dict[str, str]:
        return {"chat_id": chat_id}

    @staticmethod
    def share_user(user_id: str) -> dict[str, str]:
        return {"user_id": user_id}

    @staticmethod
    def audio(file_key: str) -> dict[str, str]:
        return {"file_key": file_key}

    @staticmethod
    def media(file_key: str, *, image_key: Optional[str] = None) -> dict[str, str]:
        payload: dict[str, str] = {"file_key": file_key}
        if image_key is not None:
            payload["image_key"] = image_key
        return payload

    @staticmethod
    def file(file_key: str) -> dict[str, str]:
        return {"file_key": file_key}

    @staticmethod
    def sticker(file_key: str) -> dict[str, str]:
        return {"file_key": file_key}

    @staticmethod
    def system(payload: Mapping[str, Any]) -> dict[str, Any]:
        return dict(payload)

    @staticmethod
    def system_divider(
        text: str,
        *,
        i18n_text: Optional[Mapping[str, str]] = None,
        need_rollup: Optional[bool] = None,
    ) -> dict[str, Any]:
        divider_text: dict[str, Any] = {"text": text}
        if i18n_text:
            divider_text["i18n_text"] = {str(k): str(v) for k, v in i18n_text.items()}
        payload: dict[str, Any] = {
            "type": "divider",
            "params": {"divider_text": divider_text},
        }
        if need_rollup is not None:
            payload["options"] = {"need_rollup": need_rollup}
        return payload
