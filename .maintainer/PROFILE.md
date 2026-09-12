# Maintainer profile — scope and tone

## What we own

- This repository: the FastAPI backend (`api/`, `open_notebook/`), the surreal-commands
  worker (`commands/`), the prompt templates (`prompts/`), the Next.js frontend (`frontend/`),
  the SurrealDB schema and migrations, the Docker images (regular and `-single`) and the
  `docker-compose` files, the documentation under `docs/`.
- The product decisions recorded in `VISION.md` and `docs/7-DEVELOPMENT/decisions/`.

## What we do not own

- Upstream libraries with their own repositories: `content-core` (extraction),
  `esperanto` (provider abstraction), `podcast-creator`, `surreal-commands`,
  `surreal-basics`. A defect that lives there gets the `upstream` label plus the library's
  label (`content-core`, `esperanto`, `podcast-creator`); the fix is an upstream issue first,
  then a bump here.
- SurrealDB itself, the AI providers' services and their pricing or availability.
- Community packaging channels (Unraid, Helm charts, Podman recipes, desktop wrappers): valid
  ideas that wait for a champion.
- The third-party "Installation Assistant" GPT linked from the issue forms.

## Tone in public text

- Answer first; no filler, no marketing, no "great question". Warmth comes from specificity
  (acknowledging a working prototype, a good decomposition), never from compliments.
- Say what was verified in the code, separately from opinion ("I checked the code: …").
- No promises of features or timelines ("no commitment on timing yet"); constraints come with
  their reasons and a link to the decision record.
- A "no" is said in the first paragraph, with the reasons; it never hides behind questions.
- Everything posted publicly is in English.

## Never cite in public

- `.tmp-context/`, `CLAUDE.local.md`, private maintainer drafts and internal plans.
- Unpublished vision specifics: "aligns with where the product is heading" is the most that
  can be said. Public anchors are `VISION.md`, the decision records, open issues and PRs.
