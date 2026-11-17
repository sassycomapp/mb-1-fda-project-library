---
title: "mb-1-fda-pre-pdlf-todo"
doc-id: "mb-5f1d2a84"
updated: "2026-11-17"
---
# Mybizz FDA — To Do Before PDLF Runs

Every item here is checked and closed before Mybizz FDA enters PDLF.

| # | Item | Why | Done when |
|---|---|---|---|
| 1 | Add the tables `health_log`, `error_log` and `rate_limits` to `docs-local/authoritative-schema.md` | The test suite's scanner (`ts_scan.py`, check DD-13 of ST-07) requires every Mybizz app to have the five standard log and control tables: `health_log`, `activity_log`, `error_log`, `webhook_log` and `rate_limits`. The Mybizz FDA schema has only `activity_log` and `webhook_log`, so Step 17 fails without them. | All five tables are in the schema, each matching the shape the Mybizz CS schema gives it |
