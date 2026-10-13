from ollama import Client
from functools import partial
import re


SYSTEM = (
    "Die verfügbaren Quellen stammen ALLE aus schweizerischen Gesetzen von Fedlex.\n"
    "Wenn sich die Frage nicht auf Schweizer Recht bezieht, antworte exakt mit dem Satz: "
    "Diese Frage bezieht sich nicht auf das Schweizer Gesetz.\n"
    "Antworte NUR auf Basis der bereitgestellten Auszüge.\n"
    "Zitiere jede Aussage mit [Nummer].\n"
    "Wenn die Antwort nicht in den Auszügen steht, antworte exakt mit dem Satz: "
    "Diese Information finde ich nicht in den vorliegenden Dokumenten.\n"
    "Erfinde nichts."
)

MAX_ATTEMPTS = 3

from common import (
    COLLECTION_NAME,
    CHAT_MODEL,
    get_qdrant_client,
    load_embedding_model,
    embed_texts,
)

     
     

def retrieve(query, model, qdrant, collection, k=3):
    q = embed_texts(model, [query])[0]

    hits = qdrant.query_points(
        collection_name=collection,
        query=q.tolist(),
        limit=k,
    ).points
    return [(hit.payload, hit.score) for hit in hits]

def call_llm(client, context, query, hint=None):
    user_message = f"Auszüge:\n{context}\n\nFrage: {query}"
    if hint: 
            user_message += f"\n\nHinweis: {hint}"
    resp = client.chat(
    model=CHAT_MODEL,
    messages=[
        {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": user_message,
            },
        ],
        options={"temperature": 0.1},
    )

    answer = resp["message"]["content"]
    
    answer = re.sub(
        r"<think>.*?</think>",
        "",
        answer,
        flags=re.DOTALL,
        ).strip()

    
    return answer

    
def extract_citations(answer, n_sources):
    """Return unique valid citation numbers and invalid citation numbers."""
    groups = re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", answer)

    numbers = [
        int(number)
        for group in groups
        for number in group.split(",")
    ]

    # Preserve first-citation order and remove duplicates.
    numbers = list(dict.fromkeys(numbers))

    valid = [n for n in numbers if 1 <= n <= n_sources]
    invalid = [n for n in numbers if n < 1 or n > n_sources]

    return valid, invalid

def hint_builder(invalid, n_sources):

    return f"Deine letzte Antwort enthielt ungültige Quellenangaben: {invalid}. Es gibt nur die Auszüge [1] bis [{n_sources}]. Beantworte die Frage erneut und verwende ausschliesslich diese Nummern. Wenn sich eine Aussage mit keinem dieser Auszüge belegen lässt, lass sie weg."

def answer_with_retry(generate, query, context, n_sources, max_attempts=MAX_ATTEMPTS):
    hint = None
    for i in range(max_attempts):
        answer=generate(query=query, context=context, hint=hint)

        valid, invalid = extract_citations(answer, n_sources)
        if not invalid: 
            return answer, valid, invalid, i+1
        hint = hint_builder(invalid, n_sources)

    return answer, valid, invalid, max_attempts



          
if __name__ == "__main__":
    # 1. Clients + collection check
    qdrant = get_qdrant_client()
    client = Client(host="http://127.0.0.1:11434")

    if not qdrant.collection_exists(collection_name=COLLECTION_NAME):
        raise SystemExit(
            f"Collection '{COLLECTION_NAME}' does not exist. "
            "Please run ingest.py first."
        )

    # 2. Model
    model = load_embedding_model()

    # 3. Question -> retrieve
    query = "Wie hoch ist die Busse für einen Verstoss gegen die DSGVO?"
    results = retrieve(query, model, qdrant, COLLECTION_NAME)

    # 4. Nothing found -> exit
    if not results:
        print("Keine passenden Auszüge gefunden.")
        raise SystemExit(0)

    # 5. Build context
    context = ""
    for i, (chunk, score) in enumerate(results, start=1):
        context += (
            f"[{i}] (Quelle: {chunk['source']})\n"
            f"{chunk['text']}\n\n"
        )

    # 6. Generate with retry
    generate = partial(call_llm, client)
    answer, valid, invalid, attempts = answer_with_retry(
        generate=generate,
        query=query,
        context=context,
        n_sources=len(results),
    )

    # 7. Answer
    print(answer)

    # 8. Sources (always)
    print("\nQuellen:")
    if not valid:
        print("Keine Quellen zitiert.")
    else:
        for n in valid:
            chunk, score = results[n - 1]
            print(f"[{n}] {chunk['source']}")

    # 9. Warning only in addition
    if invalid:
        print(f"\nWARNUNG: Ungültige Quellenangaben nach {attempts} Versuchen: {invalid}")
        print("Diese Antwort ist nicht verlässlich belegt. Bitte vor Verwendung prüfen.")

