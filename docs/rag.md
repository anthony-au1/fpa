# RAG implementation

The RAG subsystem is an independent, read-only vertical slice. It ingests the supplied Markdown corpus, validates metadata, creates stable heading-aware chunks, persists a deterministic local index, and returns cited evidence. It has no workflow-state, approval, model-prompt, or finance-tool capability.

## Ingestion and metadata

`make ingest` reads sorted `finance_rag_corpus/*.md` files and parses YAML front matter with PyYAML. Pydantic requires document ID, title, version, effective date, optional superseded date, status, owner, classification, jurisdiction, tags, and source filename. Missing or malformed front matter, invalid fields, duplicate document IDs, empty bodies, and empty chunk sets fail the entire build with the source filename. The previous index is replaced atomically only after validation succeeds.

The corpus fingerprint is SHA-256 over sorted source filenames and source checksums. The generated versioned JSON index is written to `data/index/rag-index-v1.json`; it contains no volatile timestamp, so an unchanged corpus and configuration produce byte-equivalent output.

## Chunking and citations

The parser maintains the Markdown heading hierarchy and creates chunks within a policy section. Documents with only an H1 retain that heading as their section. Sections larger than `RAG_CHUNK_MAX_CHARS` split first at paragraph boundaries and only then at a safe whitespace boundary. Separate headings are never merged.

Chunk IDs are the first 20 hexadecimal characters of SHA-256 over document ID, version, heading path, part number, and normalized chunk text. They are stable when the source section is unchanged. A citation keeps document ID, version, heading, chunk ID, and source filename; identity never depends on retrieval score.

## Embedding and index strategy

The default `local_tfidf` embedding provider creates normalized sparse TF-IDF vectors from word unigrams and bigrams. It is fitted during ingestion, and its sorted vocabulary and IDF values are stored with the index. This is a deterministic lexical vector representation—not a neural semantic model—but it is credential-free, reviewable, fast for this corpus, and works identically in tests and Docker. The provider boundary permits a future approved embedding adapter without changing retrieval contracts.

No vector database is used. The small index is loaded into memory, and cosine similarity is calculated directly. This avoids hosted infrastructure, native extensions, model downloads, and nondeterministic external calls.

## Retrieval and ranking

`retrieve_finance_documents` accepts a query, `top_k`, and `include_superseded`. Superseded evidence is included by default and participates in the same relevance calculation as every other chunk. Callers that do not need historical evidence can explicitly set `include_superseded=false`. Ranking combines configurable signals whose defaults sum to one:

- 0.50 normalized BM25 over chunk search text.
- 0.35 TF-IDF cosine similarity.
- 0.15 query-token coverage in document ID, title, heading, and tags.

An exact full document-ID query is sorted first explicitly. Other ties are resolved by score, document ID, heading, and chunk ID. Returned component scores make ranking explainable. Status does not apply a relevance penalty or boost: a superseded policy can rank highly when its text is genuinely relevant. Superseded material is never deleted from the index.

## Authority, trust, and prompt injection

Relevance and authority are separate fields. Current policies are `current_authority`; superseded policies are always `historical_only` and `superseded_policy`; the supplier document is `evidence_only`; and metadata tagged `irrelevant` is `non_authority`. Status, category, classification, jurisdiction, and tags remain visible on every result. Future financial decision logic must admit only `current_authority` evidence into authoritative policy findings even when historical evidence has a strong relevance score.

The adversarial supplier text is indexed and returned verbatim for relevant queries. Retrieval does not interpret instructions, construct executable actions, call tools, alter prompts, or mutate workflow state. Its external/unverified metadata is a structural signal to downstream code. The travel extract is not hardcoded out: AP queries rank it through the same signals, while travel queries can retrieve it.

## Evaluation

`make rag-eval` runs nine deterministic queries from `fixtures/rag_evaluation.json`. HitRate@5 measures whether each query retrieves at least one acceptable source; macro Recall@5 measures coverage when several documents are legitimately relevant. Acceptance requires HitRate@5 of 1.0 and macro Recall@5 of at least 0.85. Precision is deliberately not claimed from this small synthetic corpus.

`make retrieve QUERY="..."` prints rank, document/version/status, authority eligibility, section, citation source, score, and a short preview for inspection. Retrieval errors are explicit for missing, malformed, or incompatible indexes. The async boundary applies `RAG_RETRIEVAL_TIMEOUT_SECONDS` and raises a typed timeout error.

## Limitations and production changes

- TF-IDF does not provide neural semantic understanding or multilingual similarity. Production could add an approved regional embedding endpoint or packaged local model behind the existing provider interface.
- The corpus has no caller/ACL mapping. Production retrieval must enforce legal-entity, business-unit, role, and classification access before returning chunks.
- The JSON index is intentionally simple and memory-resident; a larger corpus would need incremental indexing, deletion propagation, concurrency control, and a suitable local or managed vector store.
- BM25 statistics are calculated over eligible candidates at query time, which is appropriate for this corpus but should be precomputed for scale.
- Retrieved evidence is not yet connected to LangGraph or an LLM. Prompt construction, citation enforcement in recommendations, and workflow audit events are Task 3 concerns.
