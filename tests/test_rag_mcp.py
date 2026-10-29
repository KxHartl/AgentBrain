#!/usr/bin/env python3
"""Tests for scripts/rag/corpus.py, sync.py and mcp_server.py against fake services.

    python tests/test_rag_mcp.py

A local HTTP server plays both Qdrant and Ollama, so nothing touches the real corpus.
Mirror tests need lancedb; MCP tests need the mcp SDK. Each skips when its package is
missing.
"""
import asyncio
import importlib.util
import json
import math
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "rag"))

import corpus  # noqa: E402

HAS_LANCE = importlib.util.find_spec("lancedb") is not None
HAS_MCP = importlib.util.find_spec("mcp") is not None
DIM = 4


def embed(text):
    """Deterministic 4-dim 'embedding': a few character counts, normalised."""
    v = [text.count("a") + 1, text.count("e") + 1, text.count("o") + 1, len(text) % 7 + 1]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


class Fake:
    """State of the fake Qdrant collection."""

    def __init__(self):
        self.points = {}   # id -> {"vector", "payload"}
        self.up = True
        self.dim = DIM

    def add(self, pid, text, **payload):
        self.points[pid] = {"vector": embed(text), "payload": {"text": text, **payload}}


def make_handler(fake):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def _down(self):
            if not fake.up and self.path.startswith("/collections"):
                self.send_response(503)
                self.end_headers()
                return True
            return False

        def do_GET(self):
            if self._down():
                return
            self._json({"result": {"status": "green", "points_count": len(fake.points),
                                   "config": {"params": {"vectors": {"size": fake.dim}}}}})

        def do_POST(self):
            if self._down():
                return
            body = self._body()
            if self.path == "/api/embed":
                return self._json({"embeddings": [embed(t) for t in body["input"]]})
            if self.path.endswith("/points/search"):
                rows = []
                for p in fake.points.values():
                    must = (body.get("filter") or {}).get("must", [])
                    if all(p["payload"].get(m["key"]) == m["match"]["value"] for m in must):
                        score = sum(a * b for a, b in zip(p["vector"], body["vector"]))
                        rows.append({"score": score, "payload": p["payload"]})
                rows.sort(key=lambda r: -r["score"])
                return self._json({"result": rows[:body["limit"]]})
            if self.path.endswith("/points/scroll"):
                ids = sorted(fake.points)
                start = int(body.get("offset") or 0)
                page = ids[start:start + body["limit"]]
                nxt = start + body["limit"] if start + body["limit"] < len(ids) else None
                return self._json({"result": {"points": [{"id": i} for i in page],
                                              "next_page_offset": nxt}})
            if self.path.endswith("/points"):
                return self._json({"result": [
                    {"id": i, "vector": fake.points[i]["vector"], "payload": fake.points[i]["payload"]}
                    for i in body["ids"]]})
            self._json({}, 404)

        def do_PUT(self):
            if self._down():
                return
            for p in self._body()["points"]:
                fake.points[p["id"]] = {"vector": p["vector"], "payload": p["payload"]}
            self._json({"result": {"status": "completed"}})

    return H


class Base(unittest.TestCase):
    def setUp(self):
        self.fake = Fake()
        self.fake.add("a1", "alpha area", source_file="a.pdf", page="1", domain="norms")
        self.fake.add("b1", "beta bee", source_file="b.pdf", page="2", domain="papers")
        self.fake.add("c1", "gamma ooo", source_file="c.pdf", page="3", domain="norms")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.fake))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{self.httpd.server_port}"
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        os.environ.update(QDRANT_URL=url, OLLAMA_HOST=url, QDRANT_COLLECTION="test",
                          OLLAMA_EMBED_MODEL="fake", AGENTBRAIN_PATH=self.tmp.name,
                          RAG_MIRROR_DIR=str(Path(self.tmp.name) / "mirror"))
        os.environ.pop("RAG_INGEST_ROOTS", None)

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()


class SearchTests(Base):
    def test_search_hits_the_server_with_citations(self):
        hits = corpus.search("alpha area", k=2)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["source_file"], "a.pdf")
        self.assertEqual(hits[0]["page"], "1")
        self.assertEqual(hits[0]["origin"], "server")

    def test_filters_reach_the_server(self):
        hits = corpus.search("alpha", k=5, domain="norms")
        self.assertEqual({h["source_file"] for h in hits}, {"a.pdf", "c.pdf"})
        hits = corpus.search("alpha", k=5, source="b.pdf")
        self.assertEqual([h["source_file"] for h in hits], ["b.pdf"])

    def test_dimension_mismatch_fails_loudly(self):
        self.fake.dim = 8
        with self.assertRaisesRegex(corpus.CorpusError, "OLLAMA_EMBED_MODEL"):
            corpus.search("alpha")

    def test_server_down_without_mirror_says_how_to_fix(self):
        self.fake.up = False
        with self.assertRaisesRegex(corpus.CorpusError, "sync.py"):
            corpus.search("alpha")

    def test_empty_question_is_refused(self):
        with self.assertRaises(corpus.CorpusError):
            corpus.search("  ")

    def test_status_reports_server_embedder_and_mirror(self):
        s = corpus.status()
        self.assertTrue(s["server"]["ok"])
        self.assertEqual(s["server"]["points"], 3)
        self.assertTrue(s["embedder"]["ok"])
        self.assertFalse(s["mirror"]["ok"])


@unittest.skipUnless(HAS_LANCE, "lancedb not installed")
class MirrorTests(Base):
    def sync(self, **kw):
        import sync
        return sync.sync(out=lambda *a, **k: None, **kw)

    def test_sync_copies_vectors_and_search_falls_back(self):
        meta = self.sync()
        self.assertEqual(meta["points"], 3)
        online = corpus.search("alpha area", k=3)
        self.fake.up = False
        offline = corpus.search("alpha area", k=3)
        self.assertEqual([h["source_file"] for h in offline], [h["source_file"] for h in online])
        self.assertEqual({h["origin"] for h in offline}, {"mirror"})
        self.assertEqual([h["source_file"] for h in corpus.search("x", source="b.pdf")], ["b.pdf"])

    def test_sync_is_incremental(self):
        self.sync()
        del self.fake.points["b1"]
        self.fake.add("d1", "delta", source_file="d.pdf", page="4")
        self.assertEqual(self.sync(check=True), {"server": 3, "mirror": 3, "new": 1, "gone": 1})
        meta = self.sync()
        self.assertEqual(meta["points"], 3)
        self.fake.up = False
        files = {h["source_file"] for h in corpus.search("delta", k=5)}
        self.assertEqual(files, {"a.pdf", "c.pdf", "d.pdf"})


class IngestTests(Base):
    def parse(self, folder, enable_ocr=False):
        print("docling chatter")  # must not reach stdout (the MCP channel)
        return [{"text": "new norm text", "source_file": "n.pdf", "page": 7, "headings": "H"},
                {"text": "   ", "source_file": "n.pdf", "page": 8}]

    def test_ingest_only_inside_allowed_roots(self):
        root = Path(self.tmp.name) / "ws"
        (root / "references").mkdir(parents=True)
        outside = Path(self.tmp.name) / "elsewhere"
        outside.mkdir()
        roots = corpus.allowed_roots(root)
        self.assertEqual(corpus.check_ingest_path(root / "references", roots),
                         (root / "references").resolve())
        for bad in (outside, root / "references" / ".." / ".." / "elsewhere"):
            with self.assertRaisesRegex(corpus.CorpusError, "outside"):
                corpus.check_ingest_path(bad, roots)
        with self.assertRaisesRegex(corpus.CorpusError, "disabled"):
            corpus.check_ingest_path(root, corpus.allowed_roots(None))

    def test_env_roots_override_the_default(self):
        os.environ["RAG_INGEST_ROOTS"] = os.pathsep.join(["/x", "/y"])
        self.assertEqual(len(corpus.allowed_roots(Path(self.tmp.name))), 2)

    def test_ingest_embeds_here_and_upserts_idempotently(self):
        root = Path(self.tmp.name)
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = corpus.ingest(root, [root.resolve()], domain="norms", project="ws",
                                parse=self.parse)
        self.assertEqual(buf.getvalue(), "")
        self.assertEqual(out["chunks"], 1)
        self.assertEqual(len(self.fake.points), 4)
        corpus.ingest(root, [root.resolve()], project="ws", parse=self.parse)
        self.assertEqual(len(self.fake.points), 4)  # same chunk, same id
        hit = corpus.search("new norm text", k=1, project="ws")[0]
        self.assertEqual((hit["source_file"], hit["page"], hit["project"]), ("n.pdf", "7", "ws"))


@unittest.skipUnless(HAS_MCP, "mcp SDK not installed")
class ServerTests(Base):
    def test_bearer_auth(self):
        import mcp_server
        calls = []

        async def app(scope, receive, send):
            calls.append(scope["type"])

        async def run(headers):
            sent = []

            async def send(msg):
                sent.append(msg)
            await mcp_server.BearerAuth(app, "s3cret-token-0123")(
                {"type": "http", "headers": headers}, None, send)
            return sent

        sent = asyncio.run(run([]))
        self.assertEqual(sent[0]["status"], 401)
        sent = asyncio.run(run([(b"authorization", b"Bearer wrong")]))
        self.assertEqual(sent[0]["status"], 401)
        asyncio.run(run([(b"authorization", b"Bearer s3cret-token-0123")]))
        self.assertEqual(calls, ["http"])

    def test_tools_answer_through_the_sdk(self):
        import mcp_server
        server = mcp_server.build(ingest_default_root=None, project="ws")

        async def go():
            names = [t.name for t in await server.list_tools()]
            res = await server.call_tool("rag_search", {"question": "alpha area", "k": 1})
            ing = await server.call_tool("rag_ingest", {"folder": self.tmp.name})
            return names, res, ing
        names, res, ing = asyncio.run(go())
        self.assertEqual(sorted(names), ["rag_ingest", "rag_search", "rag_status"])
        self.assertIn("a.pdf", json.dumps(res, default=str))
        self.assertIn("disabled", json.dumps(ing, default=str))


if __name__ == "__main__":
    unittest.main()
