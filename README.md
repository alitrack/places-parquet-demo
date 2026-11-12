# places-parquet demo

Browser-native prefix search over 237,004 GeoNames cities — the layout-is-the-product
PoC from the [duckdb-dryrun / places-as-parquet research](https://github.com/duckdb/community-extensions/pull/3593) chain.

**One page, three trust layers** (no backend — the engine is DuckDB-WASM, fully local):

1. **dryrun-style estimate (pre-execution)** — `parquet_metadata()` row-group stats ×
   required columns → "this query would touch 1/116 row groups, 73 KB of 8.4 MB" —
   *before* running the query. The duckdb-dryrun philosophy transplanted to the browser.
2. **actual (post-execution)** — result rows, warm query time, engine boot time.
3. **tantivy_stats (native sidecar, best-effort)** — the same query estimated against a
   native tantivy index via `tantivy_stats()`: exact postings+positions byte ranges,
   confidence + notes. When the sidecar isn't running (as on this static page), the
   panel degrades honestly instead of lying.

The corpus is sorted by `nkey` (normalized prefix key) with `ROW_GROUP_SIZE=1024`, so a
prefix query lands on a contiguous run of row groups — the layout *is* the index.

## Local run

```bash
cd web && python3 -m http.server 8791
# open http://127.0.0.1:8791/
```

Optional third layer (native tantivy estimate, needs the
[duckdb-tantivy](https://github.com/alitrack/duckdb-tantivy) extension built):

```bash
python3 tantivy_sidecar.py   # serves :8792 — see the research repo for the script
```

## Layout

```
web/
  index.html        # single-file demo (engine + estimate panels + results)
  places.parquet    # 9.8 MB, 116 row groups, nkey-sorted  (deploy-fetched)
  vendor/           # duckdb-mvp.wasm + matching worker    (deploy-fetched)
```

The wasm binaries and parquet are fetched at deploy time (`.gitignore`d) to keep git
history small; locally, put them under `web/vendor/` yourself if you clone.
