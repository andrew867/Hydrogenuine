"""Pack4: Shared event bus (Redis pubsub) for horizontal scaling."""

from hg_core.events.publisher import publish as publish_event
from hg_core.events.subscriber_redis import create_subscriber

__all__ = ["publish_event", "create_subscriber"]
