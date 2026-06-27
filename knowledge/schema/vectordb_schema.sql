-- Vector DB schema for search_knowledge (pgvector path). docs/06.
-- If VECTORDB_KIND=qdrant, the equivalent is a collection with a payload of the same fields.
-- NOTE: set the embedding dimension N to match the FROZEN embedding model (docs/14 O2).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          BIGSERIAL PRIMARY KEY,
    corpus      TEXT NOT NULL,            -- papers | repo | strategy_library | contract
    source      TEXT NOT NULL,            -- file/url/identifier the chunk came from
    citation    TEXT NOT NULL,            -- human-readable citation (powers the provenance view, docs/09)
    tags        TEXT[] DEFAULT '{}',      -- e.g. {mean-reversion, pairs-trading, regime}
    chunk_text  TEXT NOT NULL,
    embedding   vector(768),             -- TODO: set N to the embedding model's dimension
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ANN index (cosine). Tune lists/probes for corpus size.
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS knowledge_chunks_corpus_idx ON knowledge_chunks (corpus);
CREATE INDEX IF NOT EXISTS knowledge_chunks_tags_idx   ON knowledge_chunks USING gin (tags);
