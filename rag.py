from ollama import Client
import re
import xml.etree.ElementTree as ET
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

qdrant = QdrantClient(url="http://localhost:6333")




client = Client(host="http://127.0.0.1:11434")


def load_and_chunk(path, source_name, law_short_name):
    doc = DocumentConverter().convert(path).document
    chunks = []

    for i, ch in enumerate(HybridChunker().chunk(doc)):
        headings = ch.meta.headings or []

        article_heading = None
        article_match = None

        for h in headings:
            match = re.match(r"(Art\. \d+[a-zA-Z]*)", h)
            if match:
                article_heading = h
                article_match = match
                break

        if article_match:
            article = article_match.group(1)
            title = article_heading[len(article):].strip()

            source = f"{article} {law_short_name}"
            if title:
                source += f" ({title})"
        else:
            source = source_name

        chunks.append({
            "text": ch.text,
            "source": source,
            "id": i
        })

    return chunks

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
            # Nested block: separate it from surrounding text
            parts.append(" ")
            parts.append(get_block_text(child))
            parts.append(" ")

        else:
            # Inline element: concatenate without adding spaces
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
        num_text = " ".join(num.itertext()).strip() if num is not None else ""

        heading = art.find("akn:heading", AKN)
        head_text = " ".join(heading.itertext()).strip() if heading is not None else ""

        body = get_article_text(art)

        source = f"{law_short_name} {num_text}"

        if head_text:
            source += f" ({head_text})"

        chunks.append({
            "text": body,
            "source": source,
            "id": art.get("eId"),
        })

    return chunks

def retrieve(query, model, COLLECTION, k=3,): 
    q = model.encode([query], normalize_embeddings=True)[0]
    hits = qdrant.query_points(COLLECTION, query=q.tolist(), limit=k).points
    return [(hit.payload, hit.score) for hit in hits]


SYSTEM = (
    "Antworte NUR auf Basis der bereitgestellten Auszüge.\n"
    "Zitiere jede Aussage mit [Nummer].\n"
    "Wenn die Antwort nicht in den Auszügen steht, antworte exakt mit dem Satz: "
    "Diese Information finde ich nicht in den vorliegenden Dokumenten.\n"
    "Erfinde nichts."
)


if __name__ == "__main__":
    path = "docs\\dsg.xml"
    source_name = "SR 235.1"
    law_short_name = "DSG"
    model = SentenceTransformer("BAAI/bge-m3")
    chunks = load_and_chunk_xml(path, law_short_name)
    collection = "dsg_xml"
    chunk_texts = [c["text"] for c in chunks]

    

    chunk_vecs = model.encode(
        chunk_texts,
        normalize_embeddings=True
    )

    

    qdrant.recreate_collection(
        collection,
        vectors_config=VectorParams(size=chunk_vecs.shape[1], distance=Distance.COSINE),
    )

    qdrant.upsert(
        collection,
        points=[
            PointStruct(
                id=i,
                vector=chunk_vecs[i].tolist(),
                payload={"text": c["text"], "source": c["source"], "eId": c["id"]},
            )
            for i, c in enumerate(chunks)
        ],
    )




    query = "Was bezweckt das Datenschutzgesetz?"
    results = retrieve(query, model, collection)
    context = ""
    for i, (chunk, score) in enumerate(results, start=1):
            context += (
                f"[{i}] (Quelle: {chunk['source']})\n"
                f"{chunk['text']}\n\n"
            )

    

    resp = client.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": f"Auszüge:\n{context}\n\nFrage: {query}"
                },
            ],
            options={"temperature": 0.1},
        )

    answer = resp["message"]["content"]
    answer = re.sub(
            r"<think>.*?</think>",
            "",
            answer,
            flags=re.DOTALL
        ).strip()
    print(answer)
    
by_id = {c["id"]: c for c in chunks}

for eid in ["art_5", "art_6", "art_21"]:
    c = by_id.get(eid)
    print("=" * 80)
    if c is None:
        print(f"{eid}: NOT FOUND")
        continue

    # repr() makes leading/trailing spaces and empty () visible
    print("SOURCE:", repr(c["source"]))
    print("TEXT:")
    print(c["text"])
    print()

    # automatic checks
    src = c["source"]
    print("  source stripped:", src == src.strip())
    print("  empty '()':     ", "()" in src)

    if eid == "art_5":
        print("  'Personendaten: alle Angaben' count:",
              c["text"].count("Personendaten: alle Angaben"))
        for w in ["automatisierten", "persönliche", "Profiling:"]:
            print(f"  '{w}' present:", w in c["text"])
    if eid == "art_21":
        print("  'SR 172.021' count:", c["text"].count("SR 172.021"))

print("=" * 80)
print("total chunks:", len(chunks))
print("duplicate ids:", len(chunks) - len({c["id"] for c in chunks}))
