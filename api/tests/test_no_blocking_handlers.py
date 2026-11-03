"""Guard against blocking the event loop.

Every route here does synchronous work (SQLAlchemy sessions, the sync Anthropic
client). FastAPI runs plain ``def`` handlers in a threadpool, but runs
``async def`` handlers directly on the event loop, where one slow DB query or
Claude call would stall every request, /health included. Keep handlers sync
until the code they call is genuinely async.
"""
import inspect

from fastapi.routing import APIRoute

from app.main import app


def test_route_handlers_are_sync():
    async_routes = [
        f"{sorted(r.methods)} {r.path}"
        for r in app.routes
        if isinstance(r, APIRoute) and inspect.iscoroutinefunction(r.endpoint)
    ]
    assert async_routes == [], (
        "These handlers are async def but the app's I/O is blocking; "
        f"make them plain def: {async_routes}"
    )
