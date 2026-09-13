# DAI — Développement d'applications internet

Course material for the DAI teaching unit at
[HEIG-VD](https://heig-vd.ch), built with [Quarto](https://quarto.org).

**This is the permanent upstream repository.** Each semester runs from a
fork in its own GitHub org (e.g. `heigvd-dai-26`) — see the yearly
lifecycle below. Students: use your semester's org, not this repo.

## Structure

```
_quarto.yml        site config (nav, theme, footer)
_variables.yml     year-specific values — the only per-semester config
index.qmd          landing page + per-class schedule tables
chapters/          one .qmd per chapter (notes + exercises + solutions)
slides/            one reveal.js deck per chapter
assets/            theme (dai.scss, dai-slides.scss), logo
tools/             new-year.sh (semester setup), sync.sh (fork sync)
```

## Local preview

```sh
quarto preview
```

The site is rendered and deployed to GitHub Pages by
`.github/workflows/publish.yml` on every push to `main`.

## Yearly lifecycle

1. Create the semester org manually (no API for this): `heigvd-dai-<yy>`.
2. `tools/new-year.sh heigvd-dai-<yy>` — forks this repo into the org as
   `<org>.github.io` (so the site serves at `https://<org>.github.io/`),
   enables Actions and Pages, triggers the first build.
3. During the semester: fix in the fork; contribute back regularly with
   `tools/sync.sh push heigvd-dai-<yy>`; pull upstream improvements with
   `tools/sync.sh pull heigvd-dai-<yy>`.
4. Year-specific content lives only in `_variables.yml` and `index.qmd`,
   so syncs never conflict with chapter content.

## License

[CC BY-SA 4.0](LICENSE.md) — adapted from the
[HEIG-VD DAI course](https://github.com/heig-vd-dai-course/heig-vd-dai-course)
by L. Delafontaine and H. Louis. This version:
O. Tischhauser, with the help of [Claude](https://claude.com) (Anthropic).
