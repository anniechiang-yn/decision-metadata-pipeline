"""Script 9: turn texts into vectors with a local embedding model, and compare vectors.

Usage:  imported by scripts/compare.py; needs Ollama running with the model in config.json
        (ollama pull bge-m3). MOCK=1 skips Ollama and returns made-up vectors, to test the
        program flow only; results in that mode mean nothing.
Input:  a list of texts; the embedding URL, model and cache file in config.json
Output: one vector (a list of numbers) per text; vectors are cached so a rerun does not recompute them
"""

import hashlib
import json
import math
import os
import urllib.request
from pathlib import Path

MOCK = os.environ.get("MOCK") == "1"


def text_key(model, text):
    """Cache key: the model name and the text, hashed, so a different model never reuses old vectors."""
    return hashlib.sha256((model + "\n" + text).encode("utf-8")).hexdigest()


def mock_vector(text):
    """A made-up 32-number vector derived from the text. For testing the flow only."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255 - 0.5 for b in digest]


def request_vectors(url, model, texts):
    """Ask Ollama for the vectors of several texts in one request."""
    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["embeddings"]


def embed_texts(config, texts):
    """Return one vector per text, in the same order, using the cache where possible."""
    settings = config["embedding"]
    cache_path = Path(settings["cache"])
    cache = {}
    if cache_path.exists() and not MOCK:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    missing = [t for t in texts if text_key(settings["model"], t) not in cache]
    if missing:
        vectors = [mock_vector(t) for t in missing] if MOCK else request_vectors(settings["url"], settings["model"], missing)
        for text, vector in zip(missing, vectors):
            cache[text_key(settings["model"], text)] = vector
        if not MOCK:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache), encoding="utf-8")
    return [cache[text_key(settings["model"], t)] for t in texts]


def cosine(a, b):
    """Cosine similarity: 1 means the two vectors point the same way, 0 means unrelated."""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))
