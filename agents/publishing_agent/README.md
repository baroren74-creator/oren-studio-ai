# publishing_agent

Assembles the final package for a project — video, caption, title,
hashtags, thumbnail — into one export folder, and renders a
platform-style preview in the Studio UI. After Oren's approval
(`approvals.status = approved`), it does **not** call any publish API
(ADR-011) — Oren uploads manually through Instagram/TikTok/YouTube/
LinkedIn's own app, then marks the project as published himself. See
`docs/roadmap.md` Phase 5. `providers/publish` documents how to add real
API-based publishing later if it's ever wanted.
