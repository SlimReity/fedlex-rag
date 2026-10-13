from functools import partial

from ollama import Client

from rag import retrieve, call_llm, answer_with_retry
from common import (
    COLLECTION_NAME,
    get_qdrant_client,
    load_embedding_model,
)


if __name__ == "__main__":
    # Setup, once
    qdrant = get_qdrant_client()
    client = Client(host="http://127.0.0.1:11434")

    if not qdrant.collection_exists(collection_name=COLLECTION_NAME):
        raise SystemExit(
            f"Collection '{COLLECTION_NAME}' does not exist. "
            "Please run ingest.py first."
        )

    model = load_embedding_model()
    generate = partial(call_llm, client)

    questions = [
        # expected: answer, [1] -> DSG Art. 1
        "Was bezweckt das Datenschutzgesetz?",
        # expected: "Diese Information finde ich nicht in den vorliegenden Dokumenten."
        "Was ist die Hauptzutat von Tortellini?",
        # expected: "Diese Frage bezieht sich nicht auf das Schweizer Gesetz." (3x: temperature check)
        "Wie hoch ist die Busse für einen Verstoss gegen die DSGVO?",
        "Wie hoch ist die Busse für einen Verstoss gegen die DSGVO?",
        "Wie hoch ist die Busse für einen Verstoss gegen die DSGVO?",
        # expected: answer with DSG Art. 5, NO foreign-law refusal (over-refusal check)
        "Was sind Personendaten?",
    ]

    for query in questions:
        print(f"\nFrage: {query}")
        print("=" * 60)

        results = retrieve(query, model, qdrant, COLLECTION_NAME)

        if not results:
            print("Keine passenden Auszüge gefunden.")
            continue

        context = ""
        for i, (chunk, score) in enumerate(results, start=1):
            context += (
                f"[{i}] (Quelle: {chunk['source']})\n"
                f"{chunk['text']}\n\n"
            )

        answer, valid, invalid, attempts = answer_with_retry(
            generate=generate,
            query=query,
            context=context,
            n_sources=len(results),
        )

        print(answer)

        print("\nQuellen:")
        if not valid:
            print("Keine Quellen zitiert.")
        else:
            for n in valid:
                chunk, score = results[n - 1]
                print(f"[{n}] {chunk['source']}")

        if invalid:
            print(f"\nWARNUNG: Ungültige Quellenangaben nach {attempts} Versuchen: {invalid}")
            print("Diese Antwort ist nicht verlässlich belegt. Bitte vor Verwendung prüfen.")