"""
Minimal SSE Event Broker for Gate E compliance.

P6.5: Provides in-memory event broker with backlog + live streaming.
Enables late-connecting SSE clients to receive missed events.

Single-process scope (acceptable for MVP).
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import AsyncIterator, Deque, Dict, Optional


@dataclass
class SSEEvent:
    """SSE event with type and payload."""

    event_type: str
    payload: dict


# Sentinel for heartbeat events
# NOTE: P6.6 changed from "__heartbeat__" to "heartbeat" per Tech Spec §16.4.1
# This enables JS-visible data events for frontend idle detection.
HEARTBEAT_EVENT = SSEEvent(event_type="heartbeat", payload={})


class EventBroker:
    """In-memory event broker with backlog + live streaming.

    Features:
    - Per-workflow event backlog (configurable size)
    - Single subscriber per workflow (MVP scope)
    - Backlog replay on subscribe
    - Live event streaming after backlog
    """

    def __init__(self, backlog_size: int = 200):
        """Initialize broker with configurable backlog size.

        Args:
            backlog_size: Maximum events to retain per workflow for replay.
        """
        self._queues: Dict[str, asyncio.Queue[SSEEvent]] = {}
        self._backlog: Dict[str, Deque[SSEEvent]] = {}
        self._lock = asyncio.Lock()
        self._backlog_size = backlog_size

    async def publish(self, workflow_id: str, event: SSEEvent) -> None:
        """Publish event to backlog and any active subscriber.

        Args:
            workflow_id: Target workflow ID.
            event: SSE event to publish.
        """
        async with self._lock:
            # Add to backlog (auto-evicts oldest if full)
            backlog = self._backlog.setdefault(
                workflow_id, deque(maxlen=self._backlog_size)
            )
            backlog.append(event)

            # Push to active subscriber if present
            queue = self._queues.get(workflow_id)
            if queue:
                queue.put_nowait(event)

    async def subscribe(
        self,
        workflow_id: str,
        timeout: float = 30.0,
    ) -> AsyncIterator[SSEEvent]:
        """Subscribe to events for a workflow.

        Yields backlog first (for late-connecting clients),
        then streams live events with timeout between events.

        Args:
            workflow_id: Workflow to subscribe to.
            timeout: Max seconds to wait for next event (default 30s).

        Yields:
            SSEEvent objects in order (backlog then live).
        """
        queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        async with self._lock:
            # Register subscriber
            self._queues[workflow_id] = queue
            # Snapshot backlog under lock
            backlog = list(self._backlog.get(workflow_id, []))

        # Replay backlog first
        for event in backlog:
            yield event

        # Stream live events with timeout
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    yield event
                except asyncio.TimeoutError:
                    # No new events within timeout - yield heartbeat to keep connection alive
                    # This allows SSE clients to receive periodic keep-alive signals
                    yield HEARTBEAT_EVENT
        except asyncio.CancelledError:
            # Clean exit on cancellation
            raise
        finally:
            # Cleanup on disconnect
            async with self._lock:
                if self._queues.get(workflow_id) is queue:
                    del self._queues[workflow_id]

    async def subscribe_live(
        self,
        workflow_id: str,
        timeout: float = 30.0,
    ) -> AsyncIterator[SSEEvent]:
        """Subscribe to LIVE events only (no backlog replay).

        Use this when replaying from DB to avoid backlog mixing.
        Per Fix 2 in remediation plan: subscribe_live for race-free replay.

        Args:
            workflow_id: Workflow to subscribe to.
            timeout: Max seconds to wait for next event (default 30s).

        Yields:
            SSEEvent objects from live stream only (no backlog).
        """
        queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        async with self._lock:
            # Register subscriber - NO backlog replay
            self._queues[workflow_id] = queue

        # Stream live events with timeout (no backlog replay)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    yield event
                except asyncio.TimeoutError:
                    # Yield heartbeat to keep connection alive
                    yield HEARTBEAT_EVENT
        except asyncio.CancelledError:
            # Clean exit on cancellation
            raise
        finally:
            # Cleanup on disconnect
            async with self._lock:
                if self._queues.get(workflow_id) is queue:
                    del self._queues[workflow_id]

    async def clear_workflow(self, workflow_id: str) -> None:
        """Clear backlog for a workflow.

        Args:
            workflow_id: Workflow to clear.
        """
        async with self._lock:
            self._backlog.pop(workflow_id, None)


# =============================================================================
# Module Singleton
# =============================================================================

_broker: Optional[EventBroker] = None


def get_event_broker() -> EventBroker:
    """Get or create the global EventBroker instance.

    Returns:
        Singleton EventBroker instance.
    """
    global _broker
    if _broker is None:
        _broker = EventBroker()
    return _broker


def reset_event_broker() -> None:
    """Reset the global EventBroker (for testing).

    Creates a fresh broker instance.
    """
    global _broker
    _broker = EventBroker()
