# RAG Demo — Roadmap & Goal

## Why this project exists

I have a working on-prem German RAG demo (Fedlex / Swiss federal law), but I
**did not write it myself and don't fully understand it.** In an interview that
is a liability: if someone opens the repo and asks "why a 0.08 reranker score
floor, and what breaks at 0.05?", I can't answer.

This project rebuilds that demo **from the ground up, by hand,** so it is
genuinely mine and I can defend every design decision. Understanding first,
speed never.

## Target

- **Direction:** applied AI / LLM engineer.
- **Niche:** document AI for regulated Swiss firms (Treuhand, legal, finance).
  Example target company: Docpier.
- **Selling point:** private, on-prem systems — answers grounded in the
  client's own documents, every claim cited, honest refusal when the answer
  isn't in the documents. Nothing leaves the building.

## Constraints (mine)

- Runs locally on my homelab GPU: **8 GB VRAM** (keep embeddings on CPU to leave
  the full 8 GB for the LLM). One deliberate Azure cloud deployment near the end.
- ~**5 hours/week**, spread across 2–3 shorter sessions, over ~12 weeks.
- Every deliverable is a **clean, defensible GitHub repo with a README.**

## Skills I'm actually here to learn

RAG · embedding & re-ranking models · AI evaluation & observability ·
Evaluation-Driven Development (EDD) · AI workflows / agents ·
Model Context Protocol (MCP).

Honest starting point: I couldn't cleanly explain what an embedding is, what
attention does, or RAG vs. fine-tuning. That gap is real and this closes it.

## Build order (do NOT invert this)

1. **Understand retrieval.** Embeddings → cosine similarity, by hand, on a tiny
   corpus. No vector DB, no framework yet.
2. **Ugly end-to-end loop.** A handful of Fedlex docs → any cited answer working
   locally. Correctness of the *loop*, not quality.
3. **Make retrieval good.** Structure-aware chunking (Docling) → German
   embeddings (BGE-M3) → two-stage retrieve + cross-encoder rerank.
4. **Grounding + refusal.** Inline citations that actually support the claim;
   "nicht in den vorliegenden Dokumenten" when the docs don't cover it.
5. **Evaluation.** RAGAS + Vectara HHEM + my own answerable/unanswerable German
   test set. Measure faithfulness, citation faithfulness, abstention.
6. **Polish + demo theatre.** German UI, offline proof, the 3-minute script.

Then, as separate repos: an **MCP retrieval tool**, and an **Azure deployment**
of the same stack with evaluation-driven CI.

> Build the ugly working version first, improve retrieval second, pretty last.
> Most people invert this and never ship.

## Target stack (all self-hostable, all commercially licensed)

Ollama + Qwen3 · BGE-M3 embeddings · bge-reranker-v2-m3 · Qdrant · Docling ·
FastAPI · Docker. (Details and licence flags live in the research map.)

## Where I am now

- **Week 1 — fundamentals: embeddings.**
- Current task: fresh project + venv, write a script that embeds ~6 German
  sentences, computes cosine similarity against a query, prints them sorted
  most-similar-first, and observe what the top scores do for an off-topic query.
- Model choice open: `multilingual-e5-small` (fast) vs. `BAAI/bge-m3` (heavier,
  what the real demo uses).
