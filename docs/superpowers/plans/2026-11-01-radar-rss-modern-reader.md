# Radar RSS modern reader implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Apply the approved Radar RSS identity and clean blue reader design.
**Architecture:** Preserve static HTML/JS behavior and storage. Edit active theme rules in place; regenerate the existing raster asset family from a new master and update offline versions atomically.
**Tech Stack:** Python 3.12, plain HTML/CSS/JS, Chromium/Playwright for functional verification and raster export.
**Spec:** docs/superpowers/specs/2026-11-01-radar-rss-modern-reader-design.md

## Global constraints
- Visible name: Radar RSS. Technical prefix, storage, GUID and UID remain unchanged.
- No production dependency, collector, workflow or catalogue changes.
- Light/dark, 320–1440 px, reduced motion, 44 px primary controls.
- Do not merge or publish. Existing isolated cloud checkout and feature branch suffice.

## Review focus
- Previous installed cache must upgrade atomically and retain unrelated caches (existing Node/cache browser tests).
- Theme/reading preference and backups must survive (browser compatibility fixtures).
- Mobile navigation, long headlines and enlarged titles must fit (responsive smoke).
- Missing images must retain truthful fallback (existing browser fixtures).
- Active metadata and all exported icons must match visible identity (asset tests, browser screenshots).

### Task 1: Identity and assets
Files: web/index.html, web/manifest.webmanifest, scripts/site_config.py, visible copy in web/*.js, assets/brand, browser_tests/export_radar_brand.py, tests/test_notisonda_assets.py, tests/test_notisonda_publication.py, docs/project-status.md.
Interfaces: keep all asset filenames, URL paths, storage names and calendar identifiers; SITE_NAME becomes Radar RSS.
- [x] Update identity expectations in existing tests; run and observe failure.
- [x] Generate blue RSS symbol master, export all existing sizes and social card without changing historical assets.
- [x] Replace active display copy, document current identity and preserve historical notes.
- [x] Run Python identity tests and inspect exports.

### Task 2: Reader style and motion
Files: web/dimension.css, web/news-effects.css, browser_tests/responsive_smoke.py, tests/test_card_title_size.py.
Interfaces: DOM IDs, CSS classes and current app state stay intact; title control reports effective normal font size.
- [x] Add regression for exact normal title size; observe failure.
- [x] Edit existing palette, geometry, shadows, navigation and motion rules; no new stylesheet override layer.
- [x] Run responsive smoke in Chromium and inspect actual light/dark/mobile screenshots.
- [x] Fix only failures caused by this change or the documented title-size discrepancy, preserving meaningful assertions.

### Task 3: Offline integration and verification
Files: web/sw.js, web/index.html version queries, browser_tests fixture reports; docs implementation notes.
Interfaces: new cache radar-rss-v59 with existing atomic install and legacy cleanup retained.
- [x] Increment cache and changed resource versions; verify all active shell assets exist.
- [x] Run full Python/Node CI, Chromium responsive, theme/identity regressions and compatibility cache fixture.
- [x] Obtain independent whole-branch review; fix material findings and verify.
- [x] Record evidence, commit changes and deliver screenshots plus publication limits.
