"""WebSocket endpoint — see docs/api.md 'WebSocket'.

Phase 1 skeleton: accepts a connection per project and echoes whatever is
published on a simple in-process broadcaster. Phase 2+ wires this to the
real Redis Streams event bus (docs/architecture.md section 2) so the
Studio UI progress bar reflects actual Agent runs instead of this stub.
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# In-process only — replaced by Redis Streams pub/sub once services/
# orchestrator-worker exists (docs/roadmap.md). Good enough to prove the
# WebSocket contract works end-to-end in the meantime.
_subscribers: dict[str, set[WebSocket]] = defaultdict(set)


async def publish_event(project_id: str, event: dict) -> None:
    for ws in list(_subscribers.get(project_id, ())):
        try:
            await ws.send_json(event)
        except Exception:
            _subscribers[project_id].discard(ws)


@router.websocket("/ws/projects/{project_id}/events")
async def project_events_ws(websocket: WebSocket, project_id: str) -> None:
    await websocket.accept()
    _subscribers[project_id].add(websocket)
    try:
        while True:
            # Client doesn'''t need to send anything; this just blocks
            # until the client disconnects (or sends a ping message,
            # which we ignore) — events flow out via publish_event(),
            # called from wherever an Agent run happens (Phase 2+).
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers[project_id].discard(websocket)
