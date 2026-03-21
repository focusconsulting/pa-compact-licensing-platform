from typing import Self
from urllib.parse import ParseResult, urlencode, urlunparse

import botocore.session
from botocore.model import ServiceId
from botocore.signers import RequestSigner
from cachetools import TTLCache, cached
from redis import ConnectionPool, CredentialProvider, Redis, SSLConnection

from licensing_api.utils.config import get_app_config
from licensing_api.utils.logging import get_logger

logger = get_logger(__name__)


# The implementation is taken from the Redis docs
# https://redis.readthedocs.io/en/stable/examples/connection_examples.html#Connecting-to-a-redis-instance-with-ElastiCache-IAM-credential-provider.
class ElastiCacheIAMProvider(CredentialProvider):
    def __init__(self: Self, user: str, cluster_name: str, region: str = "us-east-1") -> None:
        self.user = user
        self.cluster_name = cluster_name
        self.region = region

        session = botocore.session.get_session()
        self.request_signer = RequestSigner(
            ServiceId("elasticache"),
            self.region,
            "elasticache",
            "v4",
            session.get_credentials(),
            session.get_component("event_emitter"),
        )

    # Generated IAM tokens are valid for 15 minutes
    @cached(cache=TTLCache(maxsize=128, ttl=900))
    def get_credentials(self) -> tuple[str] | tuple[str, str]:  # type: ignore[override]  # @cached decorator wrapper type doesn't match base class signature
        query_params = {"Action": "connect", "User": self.user}
        url = urlunparse(
            ParseResult(
                scheme="https",
                netloc=self.cluster_name,
                path="/",
                query=urlencode(query_params),
                params="",
                fragment="",
            )
        )
        signed_url = self.request_signer.generate_presigned_url(
            {"method": "GET", "url": url, "body": {}, "headers": {}, "context": {}},
            operation_name="connect",
            expires_in=900,
            region_name=self.region,
        )
        # RequestSigner only seems to work if the URL has a protocol, but
        # Elasticache only accepts the URL without a protocol
        # So strip it off the signed URL before returning
        return (self.user, str(signed_url).removeprefix("https://"))


class Cache:
    _client: Redis | None = None

    @classmethod
    def get_cache(cls) -> Redis:
        if cls._client is not None:
            return cls._client

        config = get_app_config()

        if not config.session_config.use_iam_auth:
            cls._client = Redis.from_url(
                f"{get_app_config().session_config.redis_url}:{get_app_config().session_config.redis_port}"
            )
        else:
            credentials_provider = ElastiCacheIAMProvider(
                user=config.session_config.redis_user,
                cluster_name=config.session_config.redis_cluster_name,
            )
            if not config.session_config.redis_host or not config.session_config.redis_port:
                raise ValueError("Redis host and port must be configured to use IAM auth")

            redis_pool = ConnectionPool(
                host=config.session_config.redis_host,
                port=config.session_config.redis_port,
                connection_class=SSLConnection,
                ssl_cert_reqs="none",
            )

            cls._client = Redis(
                connection_pool=redis_pool,
                port=int(config.session_config.redis_port),
                credential_provider=credentials_provider,
                ssl=True,
            )

        cls._client.ping()
        logger.info("Successfully pinged redis cache")
        return cls._client
