# TASKS — finishing the Fedlex chat demo

Task-level plan to take the demo from "embeddings script" to "offline, cited,
evaluated German RAG chat you can defend line by line." Follow the phases in
order — each builds on the last. **This file lists what to build and how to know
it's done. It does not contain the code — you write that** (see `CLAUDE.md`).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done.
Each task has an **Acceptance** (how you know it's finished) and, where it
matters, a **Checkpoint** (a question you must be able to answer — that's the
learning, not the green checkmark).

---

## Phase 0 — Setup  `[x]`

- [x] Project folder, `.venv`, `sentence-transformers` installed.
- [x] Ollama installed on the machine (you have `.ollama` in your home dir).

---

## Phase 1 — Understand retrieval (embeddings + similarity)  `[~]`

You have `run.py`. Finish it properly before moving on.

- [~] **1.1 Embed a corpus + query, rank by similarity.**
  - Acceptance: the on-topic sentence (Volljährigkeit) ranks top for the
    Volljährigkeit query; the decoys (Butterzopf, Ski) rank at the bottom.
- [x] **1.2 Fix the similarity math.**
  - Right now you compute `cosine_scores` but then **sort by `dot_prod`** — so
    your ranking isn't using the cosine you calculated. And look hard at the
    cosine line itself: write out the formula for cosine similarity on paper,
    then read line 42 with operator precedence in mind. Is that what you wrote?
  - Acceptance: ranking is driven by a correct cosine, and you can state why
    dot-product and cosine can disagree.
  - **Checkpoint:** does BGE-M3 return normalized vectors by default? If they
    were already unit-length, what would cosine and dot product have in common?
- [ ] **1.3 Off-topic query probe.**
  - Change the query to something the corpus can't answer (e.g. a question about
    tax rates). Look at the *absolute* top score.
  - **Checkpoint:** the top result is still "closest" — so similarity alone
    can't tell you "the answer isn't here." What would you need on top of it?
    (Hold that thought — it becomes the refusal behaviour in Phase 4.)

> Concept refs: research map §2 (embeddings) and §3 (why reranking exists).

---

## Phase 2 — The ugly end-to-end loop  `[ ]`

Goal: **any** cited answer, working fully offline. Quality comes later. Keep it
crude on purpose — no Qdrant, no Docling yet.

- [ ] **2.1 Get documents.** Download 1–2 Fedlex laws as PDF (start small: e.g.
  OR / ZGB excerpt) into a `docs/` folder. Public documents only.
- [ ] **2.2 Naive load + chunk.** Extract text and split it into crude
  fixed-size chunks (e.g. ~500 chars, small overlap). Plain text extraction is
  fine here — you'll replace it in Phase 3.
  - Acceptance: a Python list of chunk strings, each with a label you can cite
    (e.g. filename + chunk index).
- [ ] **2.3 In-memory retrieval.** Embed all chunks once (reuse Phase 1). Write
  `retrieve(query, k)` → returns the top-k chunks + labels by cosine. No DB yet;
  a numpy array in memory is the store.
  - Acceptance: asking a question whose answer is in the docs returns the right
    passage in the top 3.
- [ ] **2.4 Talk to the local LLM.** `ollama pull` a model that fits 8 GB
  (e.g. a 7–8B quant). Call it from Python with a hand-built prompt that pastes
  the retrieved chunks as context and asks the question.
  - Acceptance: `python run.py "<eine Frage>"` prints a German answer grounded in
    the pasted chunks, and it runs with Wi-Fi off.
  - **Checkpoint:** which parts of this loop touch the network at runtime? Prove
    it to yourself (airplane mode).

> This is the "it works" milestone. Commit it to git before improving anything.

---

## Phase 3 — Make retrieval good  `[ ]`

Now replace the crude parts with the real stack, one lever at a time, and
*measure* each change against a couple of fixed test questions.

- [ ] **3.1 Structure-aware chunking (Docling).** Swap fixed-size splitting for
  Docling + a structure-aware chunker so articles/headings stay intact and you
  get a heading path to use as the citation label.
  - Acceptance: chunks no longer cut mid-article; the label shows the article/
    heading, not just a number.
- [ ] **3.2 Vector DB (Qdrant).** Stand up Qdrant in Docker; move your vectors
  out of the numpy array into a Qdrant collection. Split the code into an
  `ingest` step (parse → chunk → embed → upsert) and a `query` step.
  - Acceptance: you can re-run queries without re-embedding the corpus each time.
- [ ] **3.3 Two-stage retrieve → rerank.** Retrieve top-k (e.g. 20) from Qdrant,
  then rerank with `bge-reranker-v2-m3` and keep the best n (e.g. 5).
  - Acceptance: on your test questions, the passage you *know* is correct moves
    up after reranking vs. embeddings alone. Note the before/after ranks.
  - **Checkpoint:** why can a cross-encoder reranker beat the bi-encoder that
    retrieved the candidates? Why not just use the reranker on all chunks?

> Concept refs: research map §1 (chunking), §3 (reranking).

---

## Phase 4 — Grounding, citations, refusal  `[ ]`

The behaviour you actually sell to a regulated buyer.

- [ ] **4.1 Grounded prompt + citation mapping.** Build the context so each
  passage carries a number `[1]…[n]`, and instruct the model (in German) to
  answer only from the passages and cite the number behind each claim. Return
  the answer plus the source list the numbers map to.
  - Acceptance: answers carry `[n]` markers and you can click from a marker to
    the exact passage it used.
- [ ] **4.2 Refusal / abstention.** Make it answer exactly one fixed German
  sentence ("… nicht in den vorliegenden Dokumenten.") when the passages don't
  contain the answer. Lower temperature to reduce invention.
  - Acceptance: the off-topic question from 1.3 now triggers the refusal instead
    of a confident guess.
  - **Checkpoint:** what's the difference between a *correct* citation and a
    *faithful* one? (research map §4). Can you produce an example where the
    answer is right but the citation doesn't actually support it?

---

## Phase 5 — Chat UI  `[ ]`

- [ ] **5.1 Streamlit front end.** A single input box → answer + an expander
  showing the source passages behind each citation. (You already have Streamlit
  config in your home dir.)
  - Acceptance: `streamlit run app.py` gives a clean German chat box that shows
    answer *and* sources, still fully offline.

---

## Phase 6 — Evaluation (EDD)  `[ ]`

This is the part that separates you from a demo-wrapper. Build it small, early.

- [ ] **6.1 Hand-labelled test set.** ~15–20 German Q&A pairs over your corpus:
  a mix of clearly answerable and deliberately unanswerable questions, each with
  the expected behaviour (answer vs. refuse) and, for answerable ones, the
  source it should cite.
- [ ] **6.2 Refusal/accuracy harness.** A script that runs the set and reports:
  answered-when-should-answer, refused-when-should-refuse, and wrong behaviour.
  - Acceptance: one command prints a small scorecard you can re-run after any
    change.
- [ ] **6.3 Plug in RAGAS + HHEM.** Add faithfulness / context-precision (RAGAS)
  and hallucination detection (Vectara HHEM) on top of your set.
  - **Checkpoint:** which single metric would you show a Treuhand buyer first,
    and why that one?

> Concept refs: research map §5 (faithfulness/refusal) + "Concrete toolkit".

---

## Phase 7 — Polish, README, ship  `[ ]`

- [ ] **7.1 docker-compose** the whole thing (Ollama, Qdrant, app) so it's one
  command to run — this is what becomes the deployable product.
- [ ] **7.2 README** a hiring manager can skim: what it is, the architecture
  (Docling → chunk → BGE-M3 → Qdrant → reranker → LLM → cited answer), the
  eval scorecard, and the "runs offline" proof. No marketing, just what it does
  and the numbers.
- [ ] **7.3 Demo script.** The 3-minute walkthrough: offline proof → hard
  question with citations → the honest refusal → drop in a new PDF and re-ask.
- [ ] **7.4 Push to GitHub** as a clean, defensible repo.

---

## Later — separate repos (roadmap, not this demo)

- [ ] MCP retrieval tool wrapping the engine.
- [ ] Azure deployment of the same stack with evaluation-driven CI.

---

## Definition of done (this demo)

Runs fully offline · answers German questions from public Fedlex docs · cites
the passage behind every claim · refuses honestly when the docs don't cover it ·
has an eval scorecard · one-command run · README + you can explain **every**
design decision, including the reranker cutoff.
