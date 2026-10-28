# Graph Report - BaseGov  (2026-10-27)

## Corpus Check
- 14 files · ~173,961 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .example 1)

## Summary
- 96 nodes · 169 edges · 9 communities (6 shown, 3 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- PDF Image Extraction & Matching
- Document Ingestion & Search Debug
- Telegram Bot Interface
- Response Caching (SQLite)
- LLM Model Providers (Gemini/NVIDIA)
- LangGraph RAG Workflow Routing
- RAG Generation & Context Assembly
- Query Rewriter (Conversation History)

## God Nodes (most connected - your core abstractions)
1. `State` - 10 edges
2. `build_graph()` - 10 edges
3. `PdfImages` - 7 edges
4. `main()` - 7 edges
5. `_connect()` - 6 edges
6. `normalize()` - 6 edges
7. `generate()` - 6 edges
8. `answer()` - 5 edges
9. `get()` - 5 edges
10. `put()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `lookup()` --calls--> `get()`  [EXTRACTED]
  graph.py → cache.py
- `generate()` --calls--> `put()`  [EXTRACTED]
  graph.py → cache.py
- `main()` --calls--> `clear()`  [EXTRACTED]
  ingest.py → cache.py
- `load_pdfs()` --calls--> `PdfImages`  [EXTRACTED]
  ingest.py → images.py
- `split_documents()` --calls--> `best_match()`  [EXTRACTED]
  ingest.py → images.py

## Import Cycles
- None detected.

## Communities (9 total, 3 thin omitted)

### Community 0 - "PDF Image Extraction & Matching"
Cohesion: 0.15
Nodes (3): best_match(), _key(), PdfImages

### Community 1 - "Document Ingestion & Search Debug"
Cohesion: 0.18
Nodes (6): get_embeddings(), is_toc(), load_documents(), load_pdfs(), main(), split_documents()

### Community 2 - "Telegram Bot Interface"
Cohesion: 0.26
Nodes (4): answer(), main(), send_images(), start()

### Community 3 - "Response Caching (SQLite)"
Cohesion: 0.29
Nodes (5): clear(), _connect(), get(), normalize(), put()

### Community 6 - "LangGraph RAG Workflow Routing"
Cohesion: 0.36
Nodes (8): build_graph(), from_cache(), lookup(), not_found(), retrieve(), route(), route_cache(), State

### Community 7 - "RAG Generation & Context Assembly"
Cohesion: 0.33
Nodes (3): generate(), pick_images(), text_of()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PdfImages` connect `PDF Image Extraction & Matching` to `Document Ingestion & Search Debug`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `build_graph()` (e.g. with `from_cache()` and `generate()`) actually correct?**
  _`build_graph()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Why does `pick_images()` connect `RAG Generation & Context Assembly` to `LLM Model Providers (Gemini/NVIDIA)`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `split_documents()` connect `Document Ingestion & Search Debug` to `PDF Image Extraction & Matching`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._