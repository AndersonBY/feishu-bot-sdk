from ..exceptions import SDKError


class WebhookError(SDKError):
    pass


class WebhookTimestampError(WebhookError):
    pass


class WebhookSignatureError(WebhookError):
    pass


class WebhookDecryptError(WebhookError):
    pass


class WebhookTokenError(WebhookError):
    pass


class WebhookChallengeError(WebhookError):
    pass


class WebhookHandlerError(WebhookError):
    pass
