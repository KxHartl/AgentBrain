"""Server-first vector store + Ollama embeddings, stdlib only.

Reconstructed on 2026-09-25 after the loss of the unpushed AgentBrain work (the
original module never reached GitHub). The interface is the one the LiteRealm
projects already call:

    from store_adapter import get_vector_store, load_env, ollama_embed
    store = get_vector_store()          # QdrantStore if reachable, else LanceStore
    store.search(vector, k)             # -> list of payload dicts + "score"
    store.upsert_chunks(chunks, model_id=..., dim=..., scope=..., domain=...)

Configuration (project `.env`, then the process environment):
    QDRANT_URL          e.g. http://qdrant.lan  (unset -> LanceDB only)
    QDRANT_COLLECTION   default agentbrain_corpus_8b
    QDRANT_TIMEOUT      seconds, default 60
    OLLAMA_HOST         default http://127.0.0.1:11434
    OLLAMA_EMBED_MODEL  default qwen3-embedding:8b
    RAG_STRICT_EMBED    1 -> never substitute a different embedding model

Everything here uses urllib only, so a query against Qdrant needs neither the
brain venv nor torch/lancedb.
"""

import json
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_COLLECTION = "agentbrain_corpus_8b"
DEFAULT_EMBED_MODEL = "qwen3-embedding:8b"


def load_env(root=None):
    """Load KEY=VALUE lines from <root>/.env into os.environ (existing vars win)."""
    env_file = Path(root or Path.cwd()) / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def strict_embed():
    return os.environ.get("RAG_STRICT_EMBED", "0") == "1"


def _http(method, url, payload=None, timeout=60):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# --- Embeddings -------------------------------------------------------------

def ollama_model():
    return os.environ.get("OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL)


def ollama_embed(texts, model=None, host=None, timeout=300):
    """Embed a string or list of strings through Ollama's /api/embed."""
    model = model or ollama_model()
    host = (host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
    if not host.startswith("http"):
        host = "http://" + host
    single = isinstance(texts, str)
    body = _http("POST", f"{host}/api/embed",
                 {"model": model, "input": [texts] if single else list(texts)}, timeout=timeout)
    vecs = body["embeddings"]
    return vecs[0] if single else vecs


def ollama_embedder():
    """Return (embed_fn, dim, model_id) for the configured Ollama model, or raise."""
    model = ollama_model()
    probe = ollama_embed("dimension probe", model=model)
    return (lambda texts: ollama_embed(texts, model=model)), len(probe), f"ollama:{model}"


# --- Stores -----------------------------------------------------------------

class QdrantStore:
    def __init__(self, url, collection, timeout):
        self.url = url.rstrip("/")
        self.collection = collection
        self.timeout = timeout

    def ping(self):
        info = _http("GET", f"{self.url}/collections/{self.collection}", timeout=5)
        return info["result"]

    def dim(self):
        return self.ping()["config"]["params"]["vectors"]["size"]

    def search(self, vector, k=5, flt=None):
        payload = {"vector": vector, "limit": k, "with_payload": True}
        if flt:
            payload["filter"] = flt
        res = _http("POST", f"{self.url}/collections/{self.collection}/points/search",
                    payload, timeout=self.timeout)["result"]
        return [{**p["payload"], "score": p["score"]} for p in res]

    def ensure_collection(self, dim):
        try:
            have = self.dim()
        except urllib.error.HTTPError:
            _http("PUT", f"{self.url}/collections/{self.collection}",
                  {"vectors": {"size": dim, "distance": "Cosine"}}, timeout=self.timeout)
            return
        if have != dim:
            raise RuntimeError(f"Collection {self.collection} is {have}-dim, embeddings are {dim}-dim.")

    def upsert_chunks(self, chunks, model_id, dim, scope="local", domain="general", batch=100,
                      project=None):
        self.ensure_collection(dim)
        n = 0
        for i in range(0, len(chunks), batch):
            points = []
            for c in chunks[i:i + batch]:
                key = f"{c['source_file']}|{c.get('page', '')}|{c['text'][:200]}"
                points.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, key)),
                    "vector": c["vector"],
                    "payload": {
                        "text": c["text"], "source_file": c["source_file"],
                        "page": str(c.get("page", "")), "headings": c.get("headings", ""),
                        "domain": c.get("domain", domain), "intelligence": c.get("intelligence", domain),
                        "scope": scope, "model_id": model_id,
                        **({"project": project} if project else {}),
                    },
                })
            _http("PUT", f"{self.url}/collections/{self.collection}/points?wait=true",
                  {"points": points}, timeout=self.timeout)
            n += len(points)
        return n

    def delete_sources(self, names, project):
        """Delete the points of these source files - only those tagged with `project`.

        The collection is shared across projects (and holds points written before
        tagging existed), so an untagged or foreign point is never touched.
        """
        if not names:
            return
        flt = {"must": [{"key": "source_file", "match": {"any": list(names)}},
                        {"key": "project", "match": {"value": project}}]}
        _http("POST", f"{self.url}/collections/{self.collection}/points/delete?wait=true",
              {"filter": flt}, timeout=self.timeout)


class LanceStore:
    """Local LanceDB fallback (the June 2.2.0 behaviour)."""

    def __init__(self, store_dir, table="project_docs"):
        self.store_dir = Path(store_dir)
        self.table = table

    def upsert_chunks(self, chunks, model_id, dim, scope="local", domain="general"):
        import lancedb
        self.store_dir.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(self.store_dir))
        rows = [{k: v for k, v in c.items()} for c in chunks]
        if self.table in db.table_names():
            db.drop_table(self.table)
        db.create_table(self.table, data=rows)
        return len(rows)

    def _db(self):
        import lancedb
        self.store_dir.mkdir(parents=True, exist_ok=True)
        return lancedb.connect(str(self.store_dir))

    def append_chunks(self, rows):
        """Add rows to the table, creating it on first use (incremental sync)."""
        if not rows:
            return 0
        db = self._db()
        if self.table in db.table_names():
            db.open_table(self.table).add(rows)
        else:
            db.create_table(self.table, data=rows)
        return len(rows)

    def delete_sources(self, names, project=None):  # noqa: ARG002 - per-project table already
        db = self._db()
        if not names or self.table not in db.table_names():
            return
        quoted = ", ".join("'" + n.replace("'", "''") + "'" for n in names)
        db.open_table(self.table).delete(f"source_file IN ({quoted})")

    def drop(self):
        db = self._db()
        if self.table in db.table_names():
            db.drop_table(self.table)


def get_vector_store(project_root=None):
    """QdrantStore when QDRANT_URL is set and answers; otherwise LanceStore."""
    load_env(project_root)
    url = os.environ.get("QDRANT_URL")
    if url:
        store = QdrantStore(url, os.environ.get("QDRANT_COLLECTION", DEFAULT_COLLECTION),
                            float(os.environ.get("QDRANT_TIMEOUT", "60")))
        try:
            store.ping()
            return store
        except Exception as e:  # noqa: BLE001
            if strict_embed():
                raise RuntimeError(f"Qdrant at {url} unreachable and RAG_STRICT_EMBED=1: {e}")
            print(f"  Qdrant unreachable ({e}); falling back to local LanceDB.")
    from rag_paths import resolve_store_dir
    root = Path(project_root or Path.cwd())
    return LanceStore(resolve_store_dir(root / ".ai" / "rag" / "db", project_root=root))
