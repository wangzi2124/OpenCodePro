import asyncio
import json
import time
import uuid
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2


@dataclass
class BusEvent:
    type: str
    data: Any = None
    source: str = "system"
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# Pre-defined event types
class EventType:
    # Session events
    SESSION_CREATED = "session.created"
    SESSION_UPDATED = "session.updated"
    SESSION_DELETED = "session.deleted"
    SESSION_COMPACTED = "session.compacted"

    # Message events
    MESSAGE_CREATED = "message.created"
    MESSAGE_UPDATED = "message.updated"
    MESSAGE_DELETED = "message.deleted"

    # Tool events
    TOOL_START = "tool.start"
    TOOL_END = "tool.end"
    TOOL_ERROR = "tool.error"

    # Model events
    MODEL_CHANGED = "model.changed"
    PROVIDER_ERROR = "provider.error"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    CONFIG_CHANGED = "config.changed"

    # Agent events
    AGENT_START = "agent.start"
    AGENT_THOUGHT = "agent.thought"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"


class EventBus:
    """Central event bus with publish/subscribe pattern."""

    _instance = None
    _subscribers: Dict[str, List[Callable]] = {}
    _history: List[BusEvent] = []
    _max_history: int = 100
    _sse_clients: Set[asyncio.Queue] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def publish(cls, event_type: str, data: Any = None, source: str = "system", session_id: str = None):
        """Publish an event to all subscribers."""
        event = BusEvent(type=event_type, data=data, source=source, session_id=session_id)

        # Store in history
        cls._history.append(event)
        if len(cls._history) > cls._max_history:
            cls._history.pop(0)

        logger.debug(f"[EVENT] {event_type} from {source}")

        # Notify subscribers
        subscribers = cls._subscribers.get(event_type, [])[:]
        wildcard = cls._subscribers.get("*", [])[:]

        for callback in subscribers + wildcard:
            try:
                if asyncio.iscoroutinefunction(callback):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(callback(event))
                        else:
                            loop.run_until_complete(callback(event))
                    except RuntimeError:
                        pass
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"[EVENT] Subscriber error: {e}")

        # Notify SSE clients
        cls._notify_sse(event)

    @classmethod
    def _notify_sse(cls, event: BusEvent):
        """Push event to all SSE client queues."""
        to_remove = []
        for queue in cls._sse_clients:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                to_remove.append(queue)
            except Exception:
                to_remove.append(queue)

        for queue in to_remove:
            cls._sse_clients.discard(queue)

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable):
        """Subscribe to an event type. Use '*' for all events."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def unsubscribe(cls, event_type: str, callback: Callable):
        """Unsubscribe from an event type."""
        if event_type in cls._subscribers:
            cls._subscribers[event_type] = [c for c in cls._subscribers[event_type] if c != callback]

    @classmethod
    def subscribe_sse(cls, queue: asyncio.Queue):
        """Subscribe an SSE client queue to receive all events."""
        cls._sse_clients.add(queue)
        # Send recent history as replay
        for event in cls._history[-10:]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                break

    @classmethod
    def unsubscribe_sse(cls, queue: asyncio.Queue):
        """Remove an SSE client queue."""
        cls._sse_clients.discard(queue)

    @classmethod
    def get_history(cls, event_type: str = None, limit: int = 20) -> List[BusEvent]:
        """Get recent events, optionally filtered by type."""
        if event_type:
            return [e for e in cls._history if e.type == event_type][-limit:]
        return cls._history[-limit:]

    @classmethod
    def clear(cls):
        """Clear all subscribers and history."""
        cls._subscribers.clear()
        cls._history.clear()
        cls._sse_clients.clear()


__all__ = [
    "EventBus",
    "BusEvent",
    "EventType",
    "EventPriority",
]