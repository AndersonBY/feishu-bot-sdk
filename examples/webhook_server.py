import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from feishu_bot_sdk import FeishuEventRegistry
from feishu_bot_sdk.webhook import WebhookReceiver

from _settings import load_settings


settings = load_settings()
registry = FeishuEventRegistry()


def _on_im_message_receive(event):
    print("[im.message.receive_v1]", event.message_id, event.text or event.content)


def _on_bot_menu(event):
    print("[application.bot.menu_v6]", event.event_key)


def _on_card_action_trigger(event):
    print("[card.action.trigger]", event.action_tag, event.action_value)
    return {
        "toast": {
            "type": "info",
            "content": "card callback handled",
        }
    }


def _on_url_preview_get(event):
    print("[url.preview.get]", event.url, event.preview_token)
    return {"inline": {"title": event.url or "preview"}}


registry.on_im_message_receive(_on_im_message_receive)
registry.on_bot_menu(_on_bot_menu)
registry.on_card_action_trigger(_on_card_action_trigger)
registry.on_url_preview_get(_on_url_preview_get)


event_receiver = WebhookReceiver(
    registry,
    encrypt_key=settings.encrypt_key,
    verification_token=settings.verification_token,
    is_callback=False,
)
callback_receiver = WebhookReceiver(
    registry,
    encrypt_key=settings.encrypt_key,
    verification_token=settings.verification_token,
    is_callback=True,
)


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        headers = {str(k): str(v) for k, v in self.headers.items()}

        try:
            if self.path == "/webhook/event":
                payload = event_receiver.handle(headers, body)
            elif self.path == "/webhook/callback":
                payload = callback_receiver.handle(headers, body)
            else:
                self.send_response(404)
                self.end_headers()
                return
            response_body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as exc:
            response_body = json.dumps({"msg": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)


def main() -> None:
    server = HTTPServer(("127.0.0.1", 7777), _Handler)
    print("webhook server started at http://127.0.0.1:7777")
    print("event endpoint:    POST /webhook/event")
    print("callback endpoint: POST /webhook/callback")
    server.serve_forever()


if __name__ == "__main__":
    main()
