from typing import Any, Mapping

from .feishu import AsyncFeishuClient, FeishuClient


def _unwrap_bot(response: Mapping[str, Any]) -> Mapping[str, Any]:
    bot = response.get("bot")
    if isinstance(bot, Mapping):
        return bot
    return {}


class BotService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_info(self) -> Mapping[str, Any]:
        response = self._client.request_json("GET", "/bot/v3/info")
        return _unwrap_bot(response)


class AsyncBotService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_info(self) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", "/bot/v3/info")
        return _unwrap_bot(response)
