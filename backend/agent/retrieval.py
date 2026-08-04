"""RAG — Retrieval-Augmented Generation knowledge layer.

A lightweight, dependency-free knowledge base over platform policy documents.
Queries are scored with BM25-style token weighting (no external embedding model
is required) and the top snippets are returned for the orchestrator to ground
its answer. This is the third step of the ``MAG -> DAG -> RAG -> fallback``
regression.
"""
from __future__ import annotations

import re
import threading
from collections import Counter
from math import log

SEED_DOCUMENTS: list[dict] = [
    {
        "id": "escrow-policy",
        "title": "Investor escrow policy",
        "tags": ["escrow", "deposit", "investor", "abundant", "rare", "hold", "release", "refund"],
        "text": (
            "Investor escrow on a bulking register: the buyer deposits a percentage of the deal value "
            "up front. The rate is 30% for abundant-supply items and 65% for rare-supply items. "
            "The escrow basis follows precedence: closed deal value, then accepted bid value, then "
            "register target price times target quantity. Escrow is held by the platform until buyer "
            "delivery is confirmed, then released to the seller; it is refunded if the register is "
            "cancelled before any accepted bid."
        ),
    },
    {
        "id": "settlement-policy",
        "title": "Seller settlement policy",
        "tags": ["settlement", "payout", "seller", "net", "fee", "payee", "paid"],
        "text": (
            "Settlements are what a seller is owed for accepted bids or closed deals, net of the "
            "platform fee (default 2.5%). Gross equals quantity times unit price; net equals gross "
            "minus the platform fee. Settlements are grouped per payee and paid out once payment is "
            "confirmed by the provider. Supported providers include Stripe, M-Pesa, Airtel Money, "
            "MTN MoMo, Visa, Mastercard, bank transfer and cash."
        ),
    },
    {
        "id": "register-workflow",
        "title": "Bulking register lifecycle",
        "tags": ["register", "workflow", "draft", "sourcing", "aggregated", "closed", "transition"],
        "text": (
            "A bulking register moves through: draft -> sourcing -> aggregated -> closed (or cancelled). "
            "Bids may only be created while the register is in sourcing. Deals close only after the "
            "register is aggregated and warehouse capacity is booked. Escrow is deposited before deals "
            "close; settlements follow after payment succeeds."
        ),
    },
    {
        "id": "quality-grades",
        "title": "Produce quality grades",
        "tags": ["quality", "grade", "inspection", "certification", "lab", "residue"],
        "text": (
            "Quality inspection assigns a grade (e.g. A, B, C or Rejected) from certifications and "
            "laboratory results. Grade A requires full certification and clean lab results. Any "
            "residue above the accepted threshold or an expired certification downgrades or rejects "
            "the lot."
        ),
    },
    {
        "id": "payment-methods",
        "title": "Payment methods and references",
        "tags": ["payment", "stripe", "mpesa", "airtel", "mtn", "visa", "mastercard", "bank", "cash", "reference"],
        "text": (
            "Payments are recorded per provider with a provider reference. Stripe references start "
            "with pi_, ch_ or py_; M-Pesa with STK/PGW/UAG/SAF/TXC; Airtel and MTN MoMo use their "
            "transaction IDs. A payment only succeeds after the provider confirms the reference."
        ),
    },
    {
        "id": "sourcing-strategy",
        "title": "Sourcing strategies",
        "tags": ["sourcing", "mode", "cooperative", "aggregator", "marketplace", "self", "overhead"],
        "text": (
            "Sourcing modes carry a fractional overhead on the target price: self 0%, cooperative 3%, "
            "aggregator network 6%, marketplace 9%. A register is feasible when it has a target price "
            "and enough estimated source count to cover the target volume."
        ),
    },
]

_BM25_K1 = 1.5
_BM25_B = 0.75

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "do",
    "does", "did", "of", "to", "in", "on", "at", "for", "with", "and", "or",
    "not", "this", "that", "it", "its", "as", "by", "from", "how", "what",
    "when", "where", "which", "who", "whom", "whose", "can", "could", "would",
    "should", "will", "may", "might", "must", "i", "you", "he", "she", "we",
    "they", "them", "their", "me", "my", "our", "your", "show", "tell", "me",
    "please", "get", "give", "want", "need", "about", "about", "find",
}


class KnowledgeBase:
    """Thread-safe, memory-backed knowledge store with BM25 retrieval."""

    def __init__(self) -> None:
        self._docs: list[dict] = []
        self._df: Counter[str, int] = Counter()
        self._lock = threading.Lock()
        for doc in SEED_DOCUMENTS:
            self.add_document(doc)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-z0-9_]{2,}", (text or "").lower())

    def _query_tokens(self, text: str) -> list[str]:
        return [t for t in self._tokens(text) if t not in _STOPWORDS]

    def _refresh_df(self) -> None:
        df: Counter[str, int] = Counter()
        for doc in self._docs:
            seen = set(self._tokens(doc["text"]))
            seen.update(t.lower() for t in doc.get("tags", []))
            for token in seen:
                df[token] += 1
        self._df = df

    def add_document(self, doc: dict) -> dict:
        entry = {
            "id": doc.get("id") or f"doc-{len(self._docs) + 1}",
            "title": doc.get("title") or "Untitled",
            "tags": list(doc.get("tags", []) or []),
            "text": doc.get("text") or "",
        }
        with self._lock:
            self._docs.append(entry)
            self._refresh_df()
        return entry

    def retrieve(self, query: str, limit: int = 3) -> list[dict]:
        query_tokens = self._query_tokens(query)
        if not query_tokens or not self._docs:
            return []
        with self._lock:
            docs = list(self._docs)
            df = dict(self._df)

        avg_len = sum(len(self._tokens(d["text"])) for d in docs) / max(len(docs), 1)
        n_docs = len(docs)
        scores: list[tuple[float, dict]] = []

        for doc in docs:
            tokens = self._tokens(doc["text"])
            tag_tokens = [t.lower() for t in doc.get("tags", [])]
            lens = len(tokens)
            tf = Counter(tokens)
            tf.update(tag_tokens)
            score = 0.0
            for token in query_tokens:
                if token not in tf:
                    continue
                f = tf[token]
                doc_freq = df.get(token, 0)
                idf = log(1 + (n_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                tf_norm = (f * (_BM25_K1 + 1)) / (f + _BM25_K1 * (1 - _BM25_B + _BM25_B * lens / avg_len))
                score += idf * tf_norm
            if score > 0:
                scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "score": round(s, 4),
                "id": doc["id"],
                "title": doc["title"],
                "tags": doc["tags"],
                "text": doc["text"],
            }
            for s, doc in scores[:limit]
        ]

    def count(self) -> int:
        with self._lock:
            return len(self._docs)


knowledge_base = KnowledgeBase()
