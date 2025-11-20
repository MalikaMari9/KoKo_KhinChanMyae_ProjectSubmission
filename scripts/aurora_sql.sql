CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS bedrock_integration;

GRANT ALL ON SCHEMA bedrock_integration TO bedrock_user;

SET SESSION AUTHORIZATION bedrock_user;

CREATE TABLE IF NOT EXISTS bedrock_integration.bedrock_kb (
    id uuid PRIMARY KEY,
    embedding vector(1536),
    chunks text,
    metadata json
);

CREATE INDEX IF NOT EXISTS bedrock_kb_embedding_idx
    ON bedrock_integration.bedrock_kb
    USING hnsw (embedding vector_cosine_ops);
