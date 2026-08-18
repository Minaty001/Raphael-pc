import pytest
import asyncio
from raphael.core.event_bus import EventBus, Event

@pytest.mark.anyio
async def test_event_bus_subscribe_and_publish():
    bus = EventBus()
    received = []

    async def sample_handler(event: Event):
        received.append(event.data.get("msg"))

    bus.subscribe("test.event", sample_handler)
    await bus.publish("test.event", {"msg": "hello_raphael"})

    assert len(received) == 1
    assert received[0] == "hello_raphael"
