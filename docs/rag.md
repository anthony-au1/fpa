# RAG design

The supplied Markdown corpus is authoritative input but not uniformly authoritative content. Ingestion will parse YAML front matter, preserve document ID, title, version, effective/superseded dates, status, owner, classification, jurisdiction, and tags, then split Markdown by heading. Oversized sections may be subdivided with small overlap while retaining the heading path and stable content hash.

## Index and retrieval

A later task will create embeddings through a configurable embedding boundary and persist vectors and chunk metadata beneath `data/index`. For this small corpus, an in-process cosine index plus metadata records is sufficient; no external vector database is justified. Retrieval will combine semantic similarity with metadata-aware ranking and return ranked chunks with relevance and complete citation fields.

Default current-policy retrieval admits `status: current` as authority. Superseded chunks remain searchable only when history is requested and are visibly labelled. Untrusted external documents can be returned as case evidence or risk indicators but never as policy authority. Irrelevant documents are retained to measure retrieval precision.

Citations identify document ID, version, heading/section, and stable chunk ID. Recommendations cite source records rather than model prompts or retrieval rank alone.

## Security and limitations

A retrieved document is evidence, not an instruction. `supplier_payment_instructions.md` contains a deliberate injection and bank-change signals; its commands are ignored and FIN-POL-004 controls apply. `travel_policy_extract.md` contains plausible numbers but is out of scope. The superseded delegation matrix must never supply current limits.

Access checks must occur before chunks are returned. Prompt text is not an access control. Corpus/index deletions must invalidate derived chunks and caches. Retrieval may miss relevant text or rank distractors; the workflow therefore exposes sources and unknowns, uses deterministic required-evidence checks, and never treats absence from retrieval as proof that a control is satisfied.

The foundation defines contracts only. Ingestion, embeddings, index updates, quality metrics, and citation-grounding evaluations are intentionally deferred.
