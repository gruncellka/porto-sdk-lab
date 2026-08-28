"""Lab PortoClient factory. Injects tracing transport when HTTP trace is enabled."""

from __future__ import annotations

from porto_sdk import PortoClient, PortoConfig
from porto_sdk.transport import HttpClient

from .http_trace import wrap_transport


def create_porto_client(config: PortoConfig | None = None) -> PortoClient:
    cfg = config or PortoConfig()
    policy = cfg.resolved_transport()
    inner = HttpClient(timeout=policy.timeout, retries=policy.retries)
    return PortoClient(cfg, transport=wrap_transport(inner))
