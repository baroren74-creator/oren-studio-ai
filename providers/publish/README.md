# providers/publish

Thin adapter over a self-hosted Postiz instance (ADR-005) — OAuth/token
refresh/chunked upload handling for Instagram, TikTok, YouTube Shorts,
Facebook, LinkedIn. The mandatory human-approval gate is NOT implemented
here — that lives in `agents/publishing_agent` and the `approvals` table
(`docs/database.md`), which decide *when* this adapter is allowed to call
Postiz's release endpoint.
