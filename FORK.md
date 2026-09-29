# CamerTrace fork of `whimo-backend`

This repository is **CamerTrace** (traçabilité du cacao et du café au Cameroun),
a fork of [EuropeanForestInstitute/whimo-backend](https://github.com/EuropeanForestInstitute/whimo-backend)
(MIT licence; keep `LICENCE`/`LICENSE` and EFI's copyright notice).

Two goals drive how it is organised:

1. **Keep pulling EFI's work** with as few conflicts as possible.
2. **Contribute back to EFI** with pull requests that contain *no* CamerTrace
   branding, text or configuration.

## Branches

| Branch | Content | Rule |
|---|---|---|
| `main` | exact copy of `upstream/main` | only `git merge --ff-only upstream/main`, never commit here |
| `camertrace` | `main` + brand overlay + Cameroon features | default branch, the one deployed; receives `main` by **merge** |
| `feat/*`, `fix/*` | generic work, candidate for EFI | branch from **`main`**, PR to EFI, then merge into `camertrace` |
| `cm/*` | Cameroon-only work | branch from **`camertrace`**, PR to `prosygma/whimo-backend:camertrace` |
| `archive/*` | history before this model (2026-09-29) | read-only |

## First time on a new clone

```bash
scripts/fork-setup.sh     # upstream remote, push to EFI disabled, rerere, merge=ours driver
```

## Pulling EFI's changes

```bash
git fetch upstream
git switch main && git merge --ff-only upstream/main && git push origin main
git switch camertrace && git merge main          # resolve, build, test
git push origin camertrace
```

`rerere` replays conflict resolutions you already made once. Binary brand files
listed in `.gitattributes` with `merge=ours` always keep the CamerTrace version.
Text brand files (theme, config) are **not** auto-resolved on purpose: when EFI
adds a new token or key, you want to see it and give it a CamerTrace value.

## Sending a change to EFI

```bash
git switch -c feat/my-change main     # from main, NOT from camertrace
# ... work, commit (English, generic wording, EFI's defaults) ...
scripts/check-upstream-clean.sh feat/my-change
git push origin feat/my-change        # open the PR on GitHub: base = EFI main
git switch camertrace && git merge feat/my-change
```

Rules for an upstream-bound change:

- never mention CamerTrace, CICC, prosygma, `camertrace.cm`;
- new user-visible text: add the key to EFI's locale files (en, and fr/es when
  you can) with neutral wording; CamerTrace wording goes in the brand overlay;
- new colour, logo or name: add it to the brand layer with EFI's value as the
  default, then give it the CamerTrace value on `camertrace` only.

`check-upstream-clean.sh` fails on the words in `.fork/forbidden-words` and
warns about paths in `.fork/brand-paths`.

## Where the CamerTrace brand lives

| File | Holds |
|---|---|
| `whimo/brand/__init__.py` | product name (e-mails, SMS, admin title), admin primary colour scale, paths of the admin icon, favicon, login image and stylesheet |
| `whimo/brand/static/brand/` | `icon.svg`, `favicon-32.png`, `login.webp`, `admin.css` (Montserrat / Open Sans) |
| `deploy/*camertrace*` | CamerTrace deployment script and runbook |

`whimo/brand/admin.py` (turns these values into Unfold settings) and the
`%(app_name)s` messages come from the generic `feat/white-label` branch, the
first candidate PR for EFI. Put Cameroon-specific features in their own Django
app (for example `whimo/camertrace/`, added to `INSTALLED_APPS`) so that their
models and migrations never collide with EFI's.

Brand sources (logos, graphic chart, export scripts) are outside the repo, in
`Documents/whimo/logos/camertrace-cicc/` (`charte-graphique.html`,
`render.sh`, `declinaisons/`).
