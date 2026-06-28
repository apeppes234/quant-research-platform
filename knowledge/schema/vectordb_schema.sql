-- Vector DB schema for search_knowledge (pgvector path). docs/06.
-- If VECTORDB_KIND=qdrant, the equivalent is a collection with a payload of the same fields.
-- Frozen embedding model: intfloat/e5-small-v2 (384 dimensions), docs/14 D11.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id           BIGSERIAL PRIMARY KEY,
    corpus       TEXT NOT NULL,            -- papers | repo | strategy_library | contract
    source       TEXT NOT NULL,            -- file/url/identifier the chunk came from
    citation     TEXT NOT NULL,            -- human-readable citation (powers the provenance view, docs/09)
    tags         TEXT[] DEFAULT '{}',      -- e.g. {mean-reversion, pairs-trading, regime}
    chunk_text   TEXT NOT NULL,
    embedding    vector(384),
    metadata     JSONB DEFAULT '{}',
    content_hash TEXT,                     -- dedup key: hash(provider + source + citation + chunk_text)
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Idempotent migration for tables created before content_hash existed.
ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS content_hash TEXT;

-- ANN index (cosine). Tune lists/probes for corpus size.
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS knowledge_chunks_corpus_idx ON knowledge_chunks (corpus);
CREATE INDEX IF NOT EXISTS knowledge_chunks_tags_idx   ON knowledge_chunks USING gin (tags);

-- Dedup: re-running an ingestion job must not insert the same chunk twice. The
-- upsert path relies on this unique index via ON CONFLICT (content_hash) DO NOTHING.
CREATE UNIQUE INDEX IF NOT EXISTS knowledge_chunks_content_hash_idx
    ON knowledge_chunks (content_hash);
