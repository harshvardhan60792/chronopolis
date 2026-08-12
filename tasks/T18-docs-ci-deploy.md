# T18 — Docs, screenshots, CI, deploy

**Blocked by:** T16 · **Effort:** medium · Ship it.

## Files
- edit: `README.md` · new: `LICENSE`, `.github/workflows/ci.yml`,
  `.github/workflows/pages.yml`, `docs/img/*`

## README (rewrite for a stranger, not for us)
Order: one-line pitch → hero screenshot/GIF → what makes it different (the
four pillars, one line each with an image) → 60-second quickstart → CLI
reference → how to read the city (legend explainer: height, footprint, colour,
arcs, traffic) → performance notes → limitations, stated honestly (Python-only
deep parsing, approximate history, commit-count ownership) → licence.

Assets to capture: overview hero, arcs on, traffic close-up (GIF), timeline
scrub (GIF), health overlay, info panel. Put them in `docs/img/`.

## LICENSE
MIT unless Q1 in `docs/OPEN-QUESTIONS.md` was answered otherwise. Add the
three.js attribution note in README (three.js is MIT too — no conflict).

## CI (`ci.yml`)
On push and PR, Ubuntu, Python 3.11 + Node 20:
1. `python citygen/tests/*.py` (they run standalone; no pytest needed)
2. build a city from `fixtures/toyrepo` and assert the invariants script passes
3. `cd viewer && npm ci && npm run build`
4. run the viewer selftest headlessly against the toyrepo city; fail if the
   console does not print `SELFTEST OK`

Keep CI under 3 minutes. No fps assertions in CI (hardware varies).

## Deploy (`pages.yml`)
GitHub Pages from the built `viewer/dist`, with two demo cities copied into it:
`demo/reachable.city.json` and one 1000+ file city (gzipped, whichever public
repo was used in T16 — note its licence and link the source).

Landing URL should load the demo city directly so a visitor sees a city
immediately, with the drop zone one click away. A visitor who has to generate
their own JSON before seeing anything will leave.

Free-forever check: Pages is static, the parser stays local, there is no
backend, no API key, no paid service anywhere in the stack. Confirm the built
page makes zero third-party requests (no fonts from a CDN — bundle or use system
fonts).

## Acceptance criteria
- A stranger can go from the README to their own city in under two minutes.
- CI green on a clean clone.
- Pages URL loads a demo city in under 3 s and holds 60 fps on the demo.
- Zero external network requests from the deployed page (check the network
  panel; it is a stated project requirement).
- `docs/CHANGELOG.md` and `STATUS.md` fully reflect reality at ship time.

## Default if ambiguous
- MIT licence, GitHub Pages, no custom domain.
- Do not publish to npm or PyPI in v1; a git clone is the install path.
