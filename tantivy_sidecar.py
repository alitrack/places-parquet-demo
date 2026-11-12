#!/usr/bin/env python3
"""Sidecar: tantivy_stats over HTTP for the demo page (third trust panel).

Bridges the browser demo to the native duckdb-tantivy extension: builds a
persistent tantivy index over the same GeoNames places corpus once at startup,
then answers GET /tantivy_stats?q=<query> by shelling out to the duckdb CLI.
The index is built with tantivy_create_index(..., language := 'english').
"""
import json, subprocess, sys, os, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

EXT = '/mnt/d/wsl2/duckdb-tantivy/build/release/tantivy.duckdb_extension'
IDX_DIR = os.path.expanduser('~/research/dryrun-poc-20261112/tantivy-sidecar-idx')
PLACES = os.path.expanduser('~/research/dryrun-poc-20261112/places.parquet')
DUCKDB = '/home/lhy/.local/bin/duckdb'
PORT = 8792

def q(sql):
    r = subprocess.run([DUCKDB, '-unsigned', '-json', '-c', sql],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:500])
    out = r.stdout.strip()
    # multi-statement -json emits one JSON array PER LINE; keep the last array
    lines = [l for l in out.splitlines() if l.strip().startswith('[')]
    rows = json.loads(lines[-1]) if lines else []
    return rows[0] if rows else {}

def build_index():
    os.makedirs(IDX_DIR, exist_ok=True)
    sql = f"""
    LOAD '{EXT}';
    CREATE OR REPLACE TABLE docs AS
    SELECT geonameid AS id, name || ' ' || coalesce(admin1,'') || ' ' || coalesce(country,'') AS body
    FROM read_parquet('{PLACES}');
    SELECT * FROM tantivy_create_index('places', 'docs', id_column := 'id', text_column := 'body', language := 'english', path := '{IDX_DIR}');
    """
    print('[sidecar] building tantivy index over 237k places…', file=sys.stderr)
    row = q(sql)
    print(f"[sidecar] index ready: {row}", file=sys.stderr)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == '/tantivy_stats':
            query = urllib.parse.parse_qs(u.query).get('q', [''])[0]
            try:
                sql = (f"LOAD '{EXT}'; "
                       f"SELECT * FROM tantivy_load_index('places', path := '{IDX_DIR}'); "
                       f"SELECT num_docs, segments, query_terms, estimated_postings_bytes, "
                       f"total_index_bytes, estimated_max_candidates, confidence, notes "
                       f"FROM tantivy_stats('places', '{query.replace(chr(39), chr(39)*2)}')")
                row = q(sql)
                body = json.dumps(row).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif u.path == '/healthz':
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
        else:
            self.send_response(404); self.end_headers()

    def log_message(self, *a): pass

if __name__ == '__main__':
    build_index()
    HTTPServer(('0.0.0.0', PORT), H).serve_forever()
