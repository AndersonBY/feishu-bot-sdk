import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from feishu_bot_sdk import FeishuEventRegistry
from feishu_bot_sdk.webhook import WebhookReceiver

from _settings import load_settings


settings = load_settings()
registry = FeishuEventRegistry()


def _on_card_action(event):
    print("[card.action.trigger]", event.action_tag, event.action_value)
    return {
        "toast": {
            "type": "success",
            "content": "callback accepted",
        }
    }


registry.on_card_action_trigger(_on_card_action)

receiver = WebhookReceiver(
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
            payload = receiver.handle(headers, body)
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
    server = HTTPServer(("127.0.0.1", 7778), _Handler)
    print("card callback demo: http://127.0.0.1:7778/")
    server.serve_forever()


if __name__ == "__main__":
    main()
