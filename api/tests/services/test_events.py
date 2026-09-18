import asyncio

from app.services.events import EventBus


async def test_publish_before_subscribe_is_replayed_then_live_then_closed():
    bus = EventBus()
    bus.publish("s1", "status", {"stage": "geocode"})
    q = bus.subscribe("s1")
    bus.publish("s1", "lead", {"id": "l1"})
    bus.close("s1")
    got = []
    while (ev := await asyncio.wait_for(q.get(), 1)) is not None:
        got.append(ev["type"])
    assert got == ["status", "lead"]
    # a late subscriber after close still gets the buffer and an immediate sentinel
    q2 = bus.subscribe("s1")
    types = []
    while (ev := q2.get_nowait()) is not None:
        types.append(ev["type"])
    assert types == ["status", "lead"]
