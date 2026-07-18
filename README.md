# Perch

An authenticated **element-screenshot dashboard** for localhost. Captures specific DOM elements from pages you're logged into and tiles them on a single page; manual refresh on demand. Generic by design — LLM usage meters, billing pages, LAN Grafana panels, status pages; if you can see it in a browser, you can put it on the wall.

See [`docs/inception.md`](docs/inception.md) for the full design rationale, decisions, and rejected alternatives. This README is the source of truth for **how to run it**; the inception doc is the source of truth for **why**.

## Status

Pre-implementation. The current spike proves the only mechanically risky piece — Playwright **element-clipped screenshots** of an authenticated page — works end-to-end. No dashboard, server, or config model exists yet.

## Project layout

```
docs/inception.md                 design + rationale
.flox/                            flox environment (Python 3.13 + Playwright pinned to 1.59)
scratch/clipping-spike/           isolated experiment proving Playwright element-clipping works
  spike.py                          headless capture of one public element (self-check)
  demo.py                           login (headed) / capture (headless) CLI for a real URL
  scripts/pw-browsers-path          resolves the nixpkgs-built Playwright Chromium linkFarm
  Justfile                          thin wrapper around flox activate + python
```

The spike lives under `scratch/` — it is throwaway scaffolding, not part of the eventual product. The flox environment at the repo root powers both the spike and (later) the real implementation.

## Prerequisites

- [flox](https://flox.dev) and Nix (`nix` on PATH for the one-time browser resolution)
- `just` (optional — recipes are thin wrappers around `flox activate`)

## First-time setup

```sh
flox install              # idempotent — uses .flox/env/manifest.toml
just --justfile scratch/clipping-spike/Justfile selfcheck
```

`selfcheck` resolves the **nixpkgs-built Playwright Chromium linkFarm** matching the flox-pinned `python313Packages.playwright` version (currently `1.59.0`, expecting `chromium_headless_shell-1217`). The resolution script caches the store path in `.flox/cache/playwright-browsers-path` and re-resolves only when that path has been garbage-collected.

> If flox's `playwright` version ever drifts from the user's `nixpkgs` channel's `python313Packages.playwright.tests.browsers` linkFarm version, capture will fail with `Executable doesn't exist at …/chromium_headless_shell-NNNN/…`. Fix: `flox uninstall playwright && flox install python313Packages.playwright@<nixpkgs version>` and `rm -f .flox/cache/playwright-browsers-path`. Pinning rather than tracking latest keeps them aligned with the local channel.

## Running the spike

```sh
JF="scratch/clipping-spike/Justfile"
just --justfile $JF selfcheck                                     # clip <div> from example.com → scratch/clipping-spike/shots/example.png
just --justfile $JF login   https://cursor.com/settings           # headed: log in by hand, cookies saved to spike's .demo-profile/
just --justfile $JF capture https://cursor.com/settings '.billing-card' cursor  # headless: clip → shots/cursor.png
```

`scratch/clipping-spike/.demo-profile/` contains live session cookies — treat as credentials. It is gitignored and not synced.

## What's next

Per `docs/inception.md` §13, the agreed design is: config (`sources → targets`), click-to-pick setup overlay, FastAPI server with SSE tile-streaming refresh, SQLite index, htmx front end. Open implementation threads: shared vs per-source profile, sequential vs parallel refresh, tile sizing, SQLite schema.