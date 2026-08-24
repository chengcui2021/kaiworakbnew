"""Application-wide constants (limits, embedding config)."""

# Titan Text Embeddings V2 on Bedrock only accepts these output sizes (AWS docs).
TITAN_EMBED_V2_DIMENSIONS: frozenset[int] = frozenset({256, 512, 1024})

# pgvector column dimension; must match BEDROCK_EMBEDDING_DIMENSIONS and migrations.
EMBEDDING_DIMENSION = 1024

BEDROCK_EMBEDDING_MODEL_ID_DEFAULT = "amazon.titan-embed-text-v2:0"

# GET /search
SEARCH_DEFAULT_LIMIT = 10
SEARCH_MAX_LIMIT = 50

# GET /entries
LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 100

ENTRY_TITLE_MAX_LENGTH = 255
