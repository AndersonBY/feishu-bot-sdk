from ..exceptions import SDKError


class WSClientError(SDKError):
    pass


class WSEndpointError(WSClientError):
    pass


class WSConnectionError(WSClientError):
    pass


class WSHandlerError(WSClientError):
    pass
