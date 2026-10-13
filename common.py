from qdrant_client import QdrantClient
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


# --- Configuration ----------------------------------------------------------

QDRANT_URL = "http://localhost:6333"

EMBED_MODEL = "BAAI/bge-m3"
CHAT_MODEL = "qwen3:8b"

COLLECTION_SOURCE = "fedlex"

COLLECTION_NAME = f"{COLLECTION_SOURCE}_{EMBED_MODEL.replace('/', '_')}"





# --- Client factories -------------------------------------------------------

def get_qdrant_client() -> QdrantClient:
    """Create and return a Qdrant client."""
    return QdrantClient(url=QDRANT_URL)



# --- Embedding model --------------------------------------------------------

def load_embedding_model() -> "SentenceTransformer":
    """Load and return the configured embedding model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed_texts(
    model: "SentenceTransformer",
    texts: list[str],
):
    """Embed a list of texts and return normalized vectors."""
    return model.encode(
        texts,
        normalize_embeddings=True,
    )