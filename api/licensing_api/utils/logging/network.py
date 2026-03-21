#
# Logging of network connections.
#
# For outgoing connections, log these:
#
# - Before connecting, the IP addresses that the host name resolves to (names often resolve to a
#   different IP within AWS due to different DNS servers, geolocation, or VPC endpoints).
#
# - After successful connection:
#   - The actual IP address used.
#   - SSL certificate details (for security auditing or troubleshooting).
#

import socket
from typing import Any

from urllib3 import connection

import licensing_api.utils.logging


def init() -> None:
    """Initialize network logging by patching calls."""
    (connection.VerifiedHTTPSConnection.connect) = (  # type: ignore[method-assign]
        patch_connect(connection.VerifiedHTTPSConnection.connect)
    )
    (connection.HTTPConnection.connect) = patch_connect(  # type: ignore[method-assign]
        connection.HTTPConnection.connect
    )


def patch_connect(
    original_connect: Any,
) -> Any:
    """Patch a connect method with additional logging."""

    def connect_log(self: Any) -> None:
        logger = licensing_api.utils.logging.get_logger(__name__)

        # Before connect: log IP addresses for the host name.
        addrs = socket.getaddrinfo(host=self.host, port=self.port, proto=socket.IPPROTO_TCP)
        logger.info("getaddrinfo %s:%s => %s", self.host, self.port, [addr[4] for addr in addrs])

        # Wrapped method call.
        original_connect(self)

        # After successful connect: log actual peer address and SSL certificate, if there is one.
        extra = {}

        if hasattr(self.sock, "getpeercert"):
            extra["cert"] = self.sock.getpeercert()

        if hasattr(self.sock, "getpeername"):
            extra["peername"] = self.sock.getpeername()

        logger.info("connected %s:%s", self.host, self.port, extra=extra)

    return connect_log
