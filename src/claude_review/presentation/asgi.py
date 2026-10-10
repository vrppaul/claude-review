"""The words of ASGI that the review's own middleware and routes read and write.

Starlette names none of them as constants; they are ASGI's own, spelled
once here.
"""

# What kind of connection a scope is
HTTP_SCOPE = "http"
WEBSOCKET_SCOPE = "websocket"

# What kind of message passes along a connection
HTTP_REQUEST = "http.request"
HTTP_DISCONNECT = "http.disconnect"
HTTP_RESPONSE_START = "http.response.start"
WEBSOCKET_CLOSE = "websocket.close"
