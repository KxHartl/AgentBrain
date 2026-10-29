"""Mirror the server corpus (Qdrant) into a local LanceDB copy, vectors included.

The mirror is what `corpus.search` falls back to when the server cannot be reached. It
copies the stored vectors, so nothing is re-embedded and results match the server's.
Incremental: only points the mirror lacks are downloaded, and points the server no
longer has are deleted.

    python ~/.agentbrain/scripts/rag/sync.py            # bring the mirror up to date
    python ~/.agentbrain/scripts/rag/sync.py --check    # report the difference, change nothing

Rebuilt 2026-10-16; the original was lost with the September disk failure.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus  # noqa: E402
from rag_paths import enable_utf8_io  # noqa: E402
from store_adapter import _http  # noqa: E402

PAGE = 1000   # ids per scroll page (no vectors: cheap)
FETCH = 64    # points per vector download (4096 floats each)


def server_ids(store):
    ids, offset = [], None
    while True:
        body = {"limit": PAGE, "with_payload": False, "with_vector": False}
        if offset is not None:
            body["offset"] = offset
        res = _http("POST", f"{store.url}/collections/{store.collection}/points/scroll",
                    body, timeout=store.timeout)["result"]
        ids.extend(str(p["id"]) for p in res["points"])
        offset = res.get("next_page_offset")
        if offset is None:
            return ids


def fetch(store, ids):
    res = _http("POST", f"{store.url}/collections/{store.collection}/points",
                {"ids": ids, "with_payload": True, "with_vector": True},
                timeout=store.timeout)["result"]
    return [{"id": str(p["id"]), "vector": p["vector"],
             **{f: str(p["payload"].get(f, "")) for f in corpus.PAYLOAD_FIELDS},
             "_model": p["payload"].get("model_id", "")} for p in res]


def schema(dim):
    import pyarrow as pa
    return pa.schema([("id", pa.string()), ("vector", pa.list_(pa.float32(), dim))]
                     + [(f, pa.string()) for f in corpus.PAYLOAD_FIELDS])


def sync(check=False, out=print):
    corpus.configure()
    store = corpus.qdrant()
    if store is None:
        raise corpus.CorpusError("QDRANT_URL is not set.")
    import lancedb
    dim = store.dim()
    remote = set(server_ids(store))
    path = corpus.mirror_dir()
    db = lancedb.connect(str(path)) if not check or path.exists() else None
    table = (db.open_table(corpus.MIRROR_TABLE)
             if db is not None and corpus.has_table(db, corpus.MIRROR_TABLE) else None)
    if table is not None and table.schema.field("vector").type.list_size != dim:
        raise corpus.CorpusError(f"Mirror at {path} is not {dim}-dim; delete it and sync again.")
    local = set(table.to_arrow().column("id").to_pylist()) if table is not None else set()
    new, gone = sorted(remote - local), sorted(local - remote)
    out(f"{store.collection}: server {len(remote)}, mirror {len(local)}, "
        f"to download {len(new)}, to delete {len(gone)}")
    if check:
        return {"server": len(remote), "mirror": len(local), "new": len(new), "gone": len(gone)}

    path.mkdir(parents=True, exist_ok=True)
    model = ""
    for i in range(0, len(new), FETCH):
        rows = fetch(store, new[i:i + FETCH])
        model = model or next((r["_model"] for r in rows if r["_model"]), "")
        for r in rows:
            del r["_model"]
        if table is None:
            table = db.create_table(corpus.MIRROR_TABLE, data=rows, schema=schema(dim))
        else:
            table.add(rows)
        done = min(i + FETCH, len(new))
        if done % (FETCH * 50) == 0 or done == len(new):
            out(f"  downloaded {done}/{len(new)}", flush=True)
    for i in range(0, len(gone), 500):
        ids = ", ".join("'" + x + "'" for x in gone[i:i + 500])
        table.delete(f"id IN ({ids})")
    old = corpus.mirror_meta() or {}
    meta = {"collection": store.collection, "server": store.url, "dim": dim,
            "points": table.count_rows() if table is not None else 0,
            "model": model or old.get("model", ""),
            "synced_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    (path / "mirror.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    out(f"Mirror at {path}: {meta['points']} points.")
    return meta


def main():
    enable_utf8_io()
    p = argparse.ArgumentParser(description="Mirror the Qdrant corpus into local LanceDB.")
    p.add_argument("--check", action="store_true", help="Report the difference only.")
    args = p.parse_args()
    try:
        sync(check=args.check)
    except corpus.CorpusError as e:
        sys.exit(f"sync: {e}")


if __name__ == "__main__":
    main()
