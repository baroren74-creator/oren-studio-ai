# prompts

Versioned source files for the Prompt Library — mirrors (and seeds) the
`prompt_library` table in Postgres (`docs/database.md`). Treat this as
the git-trackable staging area for prompts before they're loaded into the
DB; the DB copy (with `version`/`parent_id`) is what agents actually read
at runtime, not these files directly.
