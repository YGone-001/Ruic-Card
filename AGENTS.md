# AGENTS.md

## Repository purpose

This repository contains four generated RuiC holographic cards and one shared Three.js gallery. It is a final-asset repository: preserve editable card outputs under `cards/` and the directly runnable gallery under `web/`, but keep raw source photographs outside the repository.

## Branches

- `main` is the stable baseline. Do not develop directly on it.
- `develop` is the integration and day-to-day development branch.
- Use short-lived feature branches for risky or multi-step changes, then merge them into `develop`.

## Architecture

- Every card lives at `cards/<slug>/` and should use the same contract:
  - `assets/` for the five layered images and the GLB runtime model;
  - `card-config.json` for editable card metadata and material parameters;
  - `card.blend` for the editable Blender source.
- Shared automation belongs in `scripts/`; dependency manifests belong in `tools/`.
- The gallery mirrors runtime files as `web/cards/<slug>.json` and `web/assets/cards/<slug>/`.
- `web/app.js` is the frontend source. Keep `web/app.bundle.js` in sync after frontend changes.

## Validation

Before committing, run the checks relevant to the change:

```powershell
python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('scripts').glob('*.py')]"
node --check web/server.mjs
node --check web/app.js
node --check web/app.bundle.js
```

For frontend changes, run `npm install` and `npm run build` from `web/`, start `node web/server.mjs`, and verify all four card IDs: `brick-gap`, `sunset-drive`, `cloud-terrace`, and `summer-shade`.

## Generated and external content

- Do not commit `node_modules`, Python environments, downloaded Blender builds, archives, logs, render output, verification screenshots, `.blend1` files, or per-card generated `web/` directories.
- Never commit `cards/*/source/`, raw photographs, generated source studies, segmentation debug images, or local/private source paths. Build scripts must accept private inputs through documented environment variables.
- After a card's final `assets/`, GLB, and `.blend` have been produced and verified, remove its local `cards/<slug>/source/` directory before staging changes.
- Do commit the final layered artwork, GLB runtime models, final `.blend` sources, JSON configurations, and the bundled gallery JavaScript.
- Never replace user artwork or source photography unless the user explicitly requests it.
- Keep paths portable. Use repository-relative paths or documented environment variables; never commit machine-specific absolute user paths.

## Editing rules

- When adding a card, update both `cards/<slug>/` and the matching `web/` runtime files, then register the slug in `web/app.js` and `web/index.html`.
- Preserve card numbering and existing slugs unless a migration updates every source, runtime, test, and documentation reference together.
- Keep unrelated generated artifacts out of commits and ensure `git status` is clean after validation.
