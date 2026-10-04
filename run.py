import numpy as np
from sentence_transformers import SentenceTransformer;


model = SentenceTransformer("BAAI/bge-m3")

sentences = [    "Das Obligationenrecht regelt Verträge wie Kauf, Miete und Arbeit.",
    "Volljährig ist, wer das 18. Lebensjahr vollendet hat.",
    "Das Bundesgericht in Lausanne ist das oberste Gericht der Schweiz.",
    "Ein Mieter kann eine missbräuchliche Mietzinserhöhung anfechten.",
    "Die Bundesverfassung garantiert die Meinungs- und Informationsfreiheit.",
    "Das Strafgesetzbuch definiert Diebstahl als Straftat.",
    "Der Butterzopf wird traditionell am Sonntagmorgen gegessen.",
    "Im Winter fahren viele Leute in den Alpen Ski.",

    ]

query = "Wie kann ich Pasta Wasser verwenden?"
sentences_emb = model.encode(sentences)
print(type(sentences_emb), sentences_emb.shape)

query_emb = model.encode(query)
print(type(query_emb), query_emb.shape)

query_emb_list = model.encode([query])
print(query_emb_list.shape)

dot_prod = np.dot(sentences_emb, query_emb)
print(dot_prod)

m = np.array([[1, 2],
              [3, 4],
              [5, 6]])
print(np.sum(m, axis=0))
print(np.sum(m, axis=1))

query_norm = np.linalg.norm(query_emb)
print(query_norm)
embed_norm = np.linalg.norm(sentences_emb, axis=1)
print(embed_norm)
print(embed_norm.shape)

cosine_scores = dot_prod / query_norm * embed_norm
print(cosine_scores)

score_sorted = sorted(zip(sentences, dot_prod), key=lambda p: p[1], reverse=True)

for i, k in score_sorted: 
    print(f"{k:.3f}", i)



