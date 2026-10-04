from pypdf import PdfReader   # pip install pypdf
import numpy as np
from ollama import Client
import re
from sentence_transformers import SentenceTransformer;

model = SentenceTransformer("BAAI/bge-m3")
client = Client(host="http://127.0.0.1:11434")

def load_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"        # YOU: append this page's extracted text (+ a "\n")
    return text

def chunk_text(text, size=500, overlap=50, ):
    chunks = []
    start = 0
    index = 0
    source_name = "SR 235.1 Datenschutzgesetz, DSG"
    while start < len(text):
        end = start + size
        chunks.append({"text": text[start:end], "source": f"{source_name}#{index}"})
        start +=  size-overlap       # YOU: move forward, but leave `overlap` chars shared
        index += 1
    return chunks

if __name__ == "__main__":
    text = load_pdf("docs/SR 235.1 Datenschutzgesetz, DSG.pdf")     # your actual filename                 
    chunks = chunk_text(text)


# --- build the index ONCE (module level, not inside retrieve) ---
chunk_texts = [c["text"] for c in chunks]
chunk_vecs  = model.encode(chunk_texts, normalize_embeddings=True)

def retrieve(query, k=3):
    q = model.encode([query], normalize_embeddings=True)[0]          # one unit vector
    scores = chunk_vecs @ q        # dot product against every chunk = cosine, since normalized
    score_sorted = sorted(zip(chunks, scores), key=lambda p: p[1], reverse=True)
    #       (return the chunk dicts so you keep text + source; the score is useful too)
    return score_sorted[:k]

query = "Was bezweckt das Datenschutzgesetz?"
results = retrieve(query)


context = ""
for i, (chunk, score) in enumerate(results, start=1):
    context += f"[{i}] (Quelle: {chunk['source']})\n{chunk['text']}\n\n"
print(context)

SYSTEM = (
    "Antworte NUR auf Basis der bereitgestellten Auszüge.\n"
    "Zitiere jede Aussage mit [Nummer].\n"
    "Wenn die Antwort nicht in den Auszügen steht, antworte exakt mit dem Satz: "
    "Diese Information finde ich nicht in den vorliegenden Dokumenten.\n"
    "Erfinde nichts."
)

resp = client.chat(
    model="qwen3:8b",
    messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Auszüge:\n{context}\n\nFrage: {query}"},
    ],
    options={"temperature": 0.1},
)


answer = resp["message"]["content"]
answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()   # drop the reasoning
print(answer)