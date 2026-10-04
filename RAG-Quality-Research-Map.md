# On-Prem RAG Quality — Research Map & Build Guide

**Purpose:** a working reference for building a *reliable* on-premise, German-language, citation-grounded RAG assistant for regulated Swiss clients (labs, law firms, fiduciaries). Organized by the five things that actually determine quality: chunking, embeddings, reranking, citations, and refusal/faithfulness.

> The naïve RAG demo is easy; the *reliable* one is the craft — and the moat. This maps the evidence so you build on research, not blog folklore.

---

## 1. Chunking — retrieval quality starts here

Retrieval failures (not the LLM) cause most bad answers, and chunking is the biggest lever.

| Paper | arXiv | Takeaway |
|---|---|---|
| Reconstructing Context: Evaluating Advanced Chunking Strategies for RAG | 2504.19754 | Fixed-size chunks fragment context → incomplete retrieval. Compares "late chunking" vs "contextual retrieval". |
| Chunking Methods on RAG — Effectiveness vs Computational Cost | 2606.00881 | Semantic chunking helps coherence, but gains often **aren't worth the compute**. Match the method to constraints. |
| Evaluating Chunking Strategies for RAG in Enterprise Documents | 2603.24556 | **Structure-aware chunking wins** on real manuals/tables — best retrieval *and* lowest cost. Pure-text RAG fails on diagrams. |
| Financial Report Chunking for Effective RAG | 2402.05131 | Element/structure-based chunking for financial/tabular docs. |
| Advanced Chunking for Clinical Decision Support | PMC12649634 | Regulated-domain analogue (proposition/semantic/adaptive vs fixed). |

**Lesson:** Start **structure-aware / recursive**, not fixed-size, not fancy-semantic. Preserve document structure (headings, articles, tables). Only reach for semantic/late chunking if evaluation on your own corpus justifies the cost.

---

## 2. German-capable embeddings — pick empirically, in German

| Resource | arXiv / source | Takeaway |
|---|---|---|
| MTEB / MMTEB — Massive Text Embedding Benchmark | 2210.07316 | The standard leaderboard. Use as a **shortlist**, not a verdict. |
| German Text Embedding Clustering Benchmark | 2401.02709 | German-specific eval (GBERT, GELECTRA, multilingual models). |
| Granite Embedding Models | 2502.20204 | Reports German retrieval incl. **LegalQuAD** (German legal QA). multilingual-e5 scores well on German legal. |

**The gift for your legal demo:** **LegalQuAD** is a German *legal* retrieval benchmark — test your embedding choice on it before touching client data.

**Candidate open models to benchmark:** `BGE-M3`, `multilingual-e5` (small/base/large), `Qwen3-Embedding`, `KaLM-Gemma3`.

**Lesson:** Generic MTEB scores don't guarantee German/legal performance — **benchmark on your own data**. Fine-tuning yields **+10–30%** in specialized domains (legal/medical). Changing embeddings later means re-embedding everything, so choose deliberately.

---

## 3. Reranking — the highest-ROI precision boost

| Paper | arXiv | Takeaway |
|---|---|---|
| BTZSC (European Central Bank) | 2603.11991 | Modern rerankers (e.g. Qwen3-Reranker) are SOTA; **scaling benefits rerankers more than embedding models**. |
| Cross-encoder foundations | Reimers & Gurevych (sentence-transformers); ECIR-2022 reranking studies | Two-stage: bi-encoder retrieves top-k → cross-encoder reranks. |

**Lesson:** Adopt the **two-stage retrieve → rerank** pattern. A cross-encoder reranker on the top-k is the cheapest large gain in answer precision.

---

## 4. Citations / attribution — faithfulness, not just correctness

| Paper | arXiv | Takeaway |
|---|---|---|
| Measuring & Enhancing Trustworthiness of LLMs in RAG through Grounded Attributions and Learning to Refuse | 2409.11242 | Best combined citation+refusal paper. Five failure types: inaccurate answer, over-responsiveness, excessive refusal, overcitation, improper citation. |
| Correctness is not Faithfulness in RAG Attributions | 2412.18004 | A citation can be **correct but unfaithful** — models post-rationalize (answer first, cite after), undermining verifiability. |

**Lesson:** For a regulated buyer, the trust-critical property is that **the citation actually supports the claim** (faithfulness), not merely that a plausible source is attached. Design retrieval + prompting so citations are load-bearing.

---

## 5. Faithfulness / refusal / abstention — the "won't bluff" behavior you're selling

| Resource | arXiv / source | Takeaway |
|---|---|---|
| RAGTruth | 2401.00396 | Foundational RAG hallucination corpus. |
| Benchmarking LLM Faithfulness in RAG (Vectara) | 2505.04847 | Gives you a **tool**: HHEM detector + FaithJudge. RAG reduces but doesn't eliminate hallucination. |
| Hallucination Evaluation under an Abstention Policy | RAGAS/DeepEval/LLM-judge study | Directly about "I don't know from the provided documents". **Warning:** evaluators score refusals inconsistently. |
| OCC-RAG | 2606.00683 | **Compact task-specialized small models can match bigger ones** on faithfulness/abstention — good for on-prem. |
| RAGAS | 2309.15217 | Go-to automated eval (faithfulness, context precision/recall) — backbone of your eval harness. |

**Lesson:** Treat refusal as a **measured behavior**. Build abstention test cases (answerable *and* deliberately unanswerable) into your eval harness, and score with RAGAS + HHEM. This is the behavior that sells to a regulated client.

---

## Concrete toolkit (falls out of the above)

- **Eval harness:** RAGAS (faithfulness, context precision/recall) + Vectara HHEM (hallucination detection). Include unanswerable queries to test abstention.
- **German benchmark:** LegalQuAD for legal; build a small hand-labelled Q&A set per client corpus.
- **Embeddings shortlist:** BGE-M3 / multilingual-e5 / Qwen3-Embedding — then test on *your* German docs.
- **Reranker:** a cross-encoder (e.g. Qwen3-Reranker or a multilingual cross-encoder).
- **Serving (on-prem):** Ollama / vLLM with an open-weight model (Llama / Mistral / Qwen class).

---

## Recommended build order (for the Fedlex/legal demo)

1. **Ugly end-to-end loop first.** Ollama + a small RAG framework + a handful of Fedlex docs (OR, revDSG). Get *any* cited answer working locally this week.
2. **Fix retrieval.** Structure-aware chunking → German embedding (test on LegalQuAD) → add cross-encoder reranker.
3. **Grounding & refusal.** Prompt + retrieval design for inline citations and "not in the provided documents" abstention.
4. **Eval harness.** RAGAS + HHEM + your own answerable/unanswerable German test set. Measure faithfulness, citation faithfulness, and abstention.
5. **Demo theatre last.** German UI, offline proof (airplane mode / zero outbound traffic), the 3-minute script.

> **Build the ugly working version first, improve retrieval second, pretty last.** Most people invert this and never ship.

---

## Recommended commercial stack — all self-hostable, all commercially licensed

> Licence legend: 🟢 permissive (Apache-2.0 / MIT — build & resell freely, attribution only) · 🟡 conditional (usable but read terms) · 🔴 avoid in a paid product.

| Layer | Pick | Licence | Why this one |
|---|---|---|---|
| **Inference serving** | **Ollama** (start) → **vLLM** (scale) | 🟢 MIT / Apache-2.0 | Ollama = simplest local start; vLLM = throughput when concurrency grows. |
| **LLM (generator)** | **Qwen3 / Qwen3.5** (size to hardware) | 🟢 Apache-2.0 | Clean licence, strong German/multilingual, huge ecosystem. Test **Gemma 3** as alt. |
| **Embeddings** | **BGE-M3** | 🟢 MIT | Multilingual, hybrid dense+sparse in one model, strong German. |
| **Reranker** | **bge-reranker-v2-m3** | 🟢 MIT | **Matched pair** with BGE-M3 (same team); top multilingual/German reranking. |
| **Vector DB** | **Qdrant** (or **pgvector** if they run Postgres) | 🟢 Apache-2.0 / PostgreSQL | Fast, self-hosted, easy on-prem. |
| **Orchestration** | **LlamaIndex** or **Haystack** — or build on **Onyx** | 🟢 MIT / Apache-2.0 | RAG pipeline glue. Onyx = whole platform if you'd rather not hand-roll. |
| **PDF / doc parsing** | **Docling** | 🟢 MIT | Structure-aware extraction (tables, headings) → pairs with structure-aware chunking. |
| **Eval** | **RAGAS** + **Vectara HHEM-open** | 🟢 Apache-2.0 | Faithfulness / context metrics + hallucination detection. |

**Do they work together? Yes — by design.** RAG is modular (each stage passes text chunks → embeddings → top-k → answer), so these compose without friction. Two deliberate coherence points:
- **BGE-M3 + bge-reranker-v2-m3** are a *matched family* from the same team (BAAI), trained to complement each other — the strongest interoperability in the stack.
- The pipeline is linear and standard: **Docling → structure-aware chunking → BGE-M3 → Qdrant → bge-reranker → Qwen3 → RAGAS/HHEM.**
- **All-Qwen retrieval variant** (if you prefer one ecosystem): Qwen3-Embedding + Qwen3-Reranker + Qwen3 — all Apache-2.0.

**Avoid in the paid product (🔴 / traps):**
- **Jina** embeddings v4 & reranker v3 → **CC-BY-NC-4.0 (non-commercial)**. Use BGE/Qwen instead.
- **Mistral MNPL-tier models** (some "Large/Medium") → non-production only. Use the **Apache-2.0** Mistral models (Small 4, Large 3) if you want Mistral.
- **PyMuPDF (AGPL)** and **Marker** (restrictive) for parsing → use **Docling** instead.
- **Any cloud API** (OpenAI/Cohere/Gemini embeddings) → not a licence issue but breaks "nothing leaves the building". Demo only, never client data.

**Standing discipline:** confirm the LICENSE file per model/repo before shipping (badges lie), and pick the LLM/embeddings *empirically* on your own German eval set — "best" depends on your hardware and corpus, not the leaderboard.

---

*Reference compiled for a private, on-prem, German RAG assistant targeting regulated Swiss SMEs. arXiv IDs let you pull each paper directly (arxiv.org/abs/<id>). Not legal advice — verify licences per repo for your specific commercial use.*
