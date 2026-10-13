
from common import (
    COLLECTION_NAME,
    embed_texts,
    get_qdrant_client,
    load_embedding_model,
)
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    FilterSelector,
)
import re
import xml.etree.ElementTree as ET
from uuid import uuid5, NAMESPACE_URL

AKN = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"}

BLOCK_TAGS = {
    "heading",
    "p",
    "paragraph",
    "listIntroduction",
    "item",
}


def local_name(tag):
    return tag.split("}", 1)[-1]


def get_block_text(el):
    """Extract text while preserving inline text and separating nested blocks."""
    parts = []

    if el.text:
        parts.append(el.text)

    for child in el:
        child_tag = local_name(child.tag)

        if child_tag == "br":
            parts.append(" ")

        elif child_tag in BLOCK_TAGS:
            parts.append(" ")
            parts.append(get_block_text(child))
            parts.append(" ")

        else:
            parts.append(get_block_text(child))

        if child.tail:
            parts.append(child.tail)

    return "".join(parts)


def get_article_text(art):
    blocks = []

    for el in art:
        tag = local_name(el.tag)

        if tag in BLOCK_TAGS:
            text = get_block_text(el)

            if text.strip():
                blocks.append(text)

        else:
            for child in el:
                if local_name(child.tag) in BLOCK_TAGS:
                    text = get_block_text(child)

                    if text.strip():
                        blocks.append(text)

    text = " ".join(blocks)
    return re.sub(r"\s+", " ", text).strip()


def load_and_chunk_xml(path, law_short_name):
    root = ET.parse(path).getroot()
    chunks = []

    for art in root.findall(".//akn:article", AKN):
        num = art.find("akn:num", AKN)
        num_text = (
            " ".join(num.itertext()).strip()
            if num is not None else ""
        )

        heading = art.find("akn:heading", AKN)
        head_text = (
            " ".join(heading.itertext()).strip()
            if heading is not None else ""
        )

        body = get_article_text(art)

        source = f"{law_short_name} {num_text}"

        if head_text:
            source += f" ({head_text})"

        # Use a stable fallback if the XML article has no eId.
        article_id = art.get("eId") or num_text

        if not article_id:
            raise ValueError(
                f"Article without eId or number in {path}"
            )

        chunks.append({
            "text": body,
            "source": source,
            "id": article_id,
        })

    return chunks


if __name__ == "__main__":
    # Law-specific configuration
    law_short_name = "DSG"
    sr_number = "235.1"
    path = "docs/dsg.xml"

    qdrant = get_qdrant_client()
    model = load_embedding_model()

    chunks = load_and_chunk_xml(path, law_short_name)

    if not chunks:
        raise ValueError(
            f"No articles found in {path}; existing data was not changed."
        )

    # Prepare all vectors before deleting existing data.
    chunk_texts = [chunk["text"] for chunk in chunks]
    chunk_vecs = embed_texts(model, chunk_texts)

    # Create the collection only if it does not exist.
    if not qdrant.collection_exists(
        collection_name=COLLECTION_NAME
    ):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=chunk_vecs.shape[1],
                distance=Distance.COSINE,
            ),
        )

    # Delete only points belonging to this law.
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="law",
                        match=MatchValue(value=law_short_name),
                    )
                ]
            )
        ),
        wait=True,
    )

    # Upsert articles using deterministic IDs.
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(
                    uuid5(
                        NAMESPACE_URL,
                        f"ch.fedlex.rag:{law_short_name}:{chunk['id']}",
                    )
                ),
                vector=chunk_vecs[i].tolist(),
                payload={
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "eId": chunk["id"],
                    "law": law_short_name,
                    "sr": sr_number,
                },
            )
            for i, chunk in enumerate(chunks)
        ],
        wait=True,
    )

    print(
        f"Ingested {len(chunks)} articles for "
        f"{law_short_name} (SR {sr_number}) "
        f"into {COLLECTION_NAME}."
    )
