# Vision

*Distilled from `docs/prd.md`. Read the PRD for full context — this file
is the one-page version to re-anchor on when a decision feels ambiguous.*

Oren Studio AI is a system built for one user: Oren. It is not a SaaS
product and not a commercial venture in its first phase. The goal is a
single, intelligent, modular workspace that lets Oren produce
high-quality Hebrew-language tech content as fast as possible.

**The end goal:** walk into the studio, pick an idea, and within minutes
produce a short video ready to publish.

Over time, the system should become a personal agent — one that knows
Oren, his interests, and his voice.

## Core philosophy

- Not a feature collection — a **modular platform**. Every new capability
  is an independent Agent that can be added or removed without touching
  the rest of the system.
- **Agent First.** Every Agent receives a task, performs it, and returns a
  result.

## Main goal

Turn any idea, video, link, or repository into *original* content — never
copied. The system learns and understands a source, then produces
something new in Oren's own language and style.

## Non-negotiables

- **No content publishes without human approval.** Ever.
- **No vendor lock-in** for any external capability (LLM, video, avatar,
  voice) — see `docs/decisions.md` for where this held up under research
  and where it had to be revised (voice/avatar, specifically).
- Every architectural decision is tested against one question: *does this
  bring the system closer to being a smart, flexible personal agent for
  the long term?* If not, it doesn't get built.

## Style guide (content, not code)

Short. Fast. Clear. Technical. Not exhausting. Hook within 3 seconds.
Recommended length: 10–40 seconds.
