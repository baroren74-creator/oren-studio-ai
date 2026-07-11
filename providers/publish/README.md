# providers/publish

**Not used in v1 (ADR-011).** Publishing is manual: `agents/publishing_agent`
assembles the final package and a preview; Oren uploads it himself
through each platform's own app — no publish API call happens.

This folder is kept as the documented place to add a Postiz adapter
(OAuth/token refresh/chunked upload handling for Instagram, TikTok,
YouTube Shorts, Facebook, LinkedIn) if automated/scheduled posting is
ever wanted later — see ADR-005 for that original design and
`docs/roadmap.md` Phase 5.7 for how to resume it. Nothing else in the
architecture needs to change to add this later; the approval gate
(`agents/publishing_agent`, `approvals` table) would gate a real
provider call here exactly the same way it already gates the manual
"mark as published" action.
