# Perch

An authenticated **element-screenshot dashboard** for localhost. Captures specific DOM elements from pages you're logged into and tiles them on a single page; manual refresh on demand. Generic by design — LLM usage meters, billing pages, LAN Grafana panels, status pages; if you can see it in a browser, you can put it on the wall.

See [`docs/inception.md`](docs/inception.md) for the full design rationale, decisions, and rejected alternatives. This README is the source of truth for **how to run it**; the inception doc is the source of truth for **why**.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `jonocodes/perch` and are driven via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) used verbatim. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root, produced lazily by `/domain-modeling`. See `docs/agents/domain.md`.