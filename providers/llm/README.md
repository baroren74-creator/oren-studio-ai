# providers/llm

LLM provider abstraction via self-hosted LiteLLM (ADR-001's sibling
decision for routing — see `docs/open-source-landscape.md` section 2).
Claude first, then OpenAI/Gemini/local models as needed. OpenRouter, if
ever used, is configured as one failover provider *behind* LiteLLM, not
the primary router.
