# Automatic source discovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Discover and publish validated Spanish publisher feeds every 48 hours without editing curated subscriptions.

**Architecture:** One Python CLI implements bounded network discovery, public state and runtime OPML assembly. Existing collector and publication validators consume the derived OPML unchanged. GitHub cache persists the small state alongside recovery artifacts.

**Tech Stack:** Python standard library and existing feedparser; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-14-automatic-source-discovery-design.md`

## Global constraints

- Preserve all 443 curated subscription IDs and all 11 folders.
- No new dependencies, keys, services, direct-main writes or auto PRs.
- 48 hours; 5 additions; 100 AUTO total; 22 publishers; 2 feeds/publisher; 100 requests; 180 seconds.
- Only public HTTPS, pinned DNS/TLS, robots and bounded responses; Spanish/relevance/date validation.

## Review focus

- Redirects or DNS answers toward private hosts must never open a connection.
- Broken/missing dates and irrelevant local headlines must never qualify.
- A completed empty scan must throttle another scan for 48 hours.
- Transient errors must retain previously accepted sources.
- Runtime catalog must preserve curated identities and publication counts.

### Task 1: Discovery and integration

**Files:** create `scripts/source_discovery.py`, `sources/discovery-policy.json`, `tests/test_source_discovery.py`; modify `.github/workflows/deploy.yml`.

**Interfaces:** `discover(curated, policy, state, fetcher, now)` returns public state; `write_runtime_opml(curated_path, state, output)` creates a merged temporary OPML. `SafeFetcher.get(url, publisher=None)` returns bounded public bytes or raises. `validate_feed(raw, category_policy, publisher, now)` returns evidence or rejects.

- [x] Write offline tests for DNS/redirect/robots/budget safety, validation windows, state persistence/throttling, category fairness and merged IDs.
- [x] Run unittest discovery for the new module and observe missing implementation failures.
- [x] Implement safe fetch, feed validation, bounded discovery/state loading and runtime OPML CLI.
- [x] Run focused tests, then complete Python suite and curated catalog audit.
- [x] Connect hourly workflow, state cache/artifact and runtime OPML; document operating limits.
- [x] Review diff, verify again, commit and report SHA to parent for independent review.

Decisiones de implementación: rechazar transporte directo si hay proxy heredado; validación del estado caduca a los 90 días para permitir dos rotaciones completas; publicar resultados de búsqueda diferenciados de indisponibilidad. La revisión independiente y la integración/publicación corresponden al agente coordinador.
