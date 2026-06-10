"""
Milestone 5 — Grounded Generation and Query Interface
The Unofficial Guide: unofficial student knowledge about OSU housing and dorm life.

Pipeline (reusing the Milestone 3/4 work):
  documents/chunks.json
    -> embed with sentence-transformers all-MiniLM-L6-v2 (normalized)
    -> store/search in local ChromaDB (cosine distance)
    -> retrieve candidate_k=8, filter distance <= 0.45, keep final_k=4
    -> Groq llama-3.3-70b-versatile answers using ONLY the retrieved chunks
    -> sources are appended programmatically (not trusted to the LLM)

Run it with:  python app.py   (opens at http://localhost:7860)

Unsupported-question test (grounding check):
  "Which OSU dorm has the best gym?"
  Our corpus has no content about gym quality, so retrieval should return
  nothing under the distance threshold and the app must answer:
  "I don't have enough information in the provided documents to answer that."
"""

import os
import json

import chromadb
import gradio as gr
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuration (mirrors scripts/embed_and_retrieve.py exactly)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CHUNKS_FILE = os.path.join(PROJECT_ROOT, "documents", "chunks.json")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"   # sentence-transformers/all-MiniLM-L6-v2
COLLECTION_NAME = "osu_housing"

CANDIDATE_K = 8       # how many candidates to pull from ChromaDB
MAX_DISTANCE = 0.45   # drop candidates whose cosine distance is above this
FINAL_K = 4           # how many chunks to keep after filtering

GROQ_MODEL = "llama-3.3-70b-versatile"

FALLBACK_ANSWER = (
    "I don't have enough information in the provided documents to answer that."
)

# Strict grounding instructions for the LLM.
SYSTEM_PROMPT = (
    "You are a grounded RAG assistant. Answer the user's question using only "
    "the retrieved context. Do not use outside knowledge. If the context is "
    "insufficient, say you do not have enough information. Do not invent facts. "
    "Write a concise answer. Synthesize the evidence directly instead of "
    "repeating 'one commenter says' in every sentence. Still make clear when "
    "information is student-reported versus official."
)

EXAMPLE_QUESTIONS = [
    "What do students say about North Campus versus South Campus dorm life?",
    "How does the OSU housing lottery or reselection process affect dorm availability?",
    "What do students say about getting suites or private bathrooms as a freshman?",
]

# ---------------------------------------------------------------------------
# One-time setup: keys, model, vector store
# ---------------------------------------------------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# Groq client (only usable if a key is present).
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def load_chunks():
    """Read documents/chunks.json and return the list of chunk dicts."""
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_metadata(chunk):
    """ChromaDB metadata must be str/int/float/bool (never None)."""
    return {
        "source": chunk.get("source") or "",
        "source_title": chunk.get("source_title") or "",
        "source_type": chunk.get("source_type") or "",
        "url": chunk.get("url") or "",
        "chunk_id": chunk.get("chunk_id") or "",
        "char_length": int(chunk.get("char_length") or 0),
    }


def build_collection():
    """Embed every chunk and (re)build a fresh ChromaDB collection."""
    chunks = load_chunks()
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Recreate the collection so repeated runs never duplicate chunks.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # cosine distance
    )

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [safe_metadata(c) for c in chunks]

    print(f"Embedding {len(documents)} chunks ...")
    embeddings = model.encode(
        documents, show_progress_bar=False, normalize_embeddings=True
    ).tolist()

    collection.add(
        ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
    )
    print(f"Stored {collection.count()} chunks in ChromaDB at: {CHROMA_DIR}")
    return collection


# Build the index once at startup.
collection = build_collection()


# ---------------------------------------------------------------------------
# Retrieval: over-fetch -> filter by distance -> keep the best few
# ---------------------------------------------------------------------------
def retrieve_chunks(question, candidate_k=CANDIDATE_K,
                    max_distance=MAX_DISTANCE, final_k=FINAL_K):
    """Return the best `final_k` chunks for a question after distance filtering.

    Note: ChromaDB ranks by semantic similarity only, so the closest chunk is
    not always the most useful one. Over-fetching then filtering loose matches
    gives the LLM cleaner, on-topic context.
    """
    query_embedding = model.encode([question], normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=candidate_k)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    candidates = [
        {"distance": dist, "metadata": meta, "text": text}
        for text, meta, dist in zip(documents, metadatas, distances)
    ]
    kept = [hit for hit in candidates if hit["distance"] <= max_distance]
    return kept[:final_k]


def build_context(hits):
    """Format retrieved chunks into a numbered, labeled context block."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        meta = hit["metadata"]
        label = meta.get("source_type") or "source"
        title = meta.get("source_title") or meta.get("source") or "unknown"
        blocks.append(
            f"[Context {i}] (source: {title}; type: {label})\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def sources_from_hits(hits):
    """Build the programmatic source list (do NOT rely on the LLM for this)."""
    sources = []
    for hit in hits:
        meta = hit["metadata"]
        sources.append({
            "source": meta.get("source"),
            "title": meta.get("source_title"),
            "url": meta.get("url"),
            "chunk_id": meta.get("chunk_id"),
            "distance": round(float(hit["distance"]), 4),
        })
    return sources


# ---------------------------------------------------------------------------
# End-to-end: retrieve -> ground -> generate -> attach sources
# ---------------------------------------------------------------------------
def ask(question: str) -> dict:
    """Answer a question using only retrieved context; attach sources.

    Returns:
        {"answer": str, "sources": [{source, title, url, chunk_id, distance}]}
    """
    question = (question or "").strip()
    if not question:
        return {"answer": "Please enter a question.", "sources": []}

    hits = retrieve_chunks(question)

    # If nothing survived the distance filter, the documents cannot support an
    # answer -- return the fallback without calling the LLM.
    if not hits:
        return {"answer": FALLBACK_ANSWER, "sources": []}

    if groq_client is None:
        return {
            "answer": ("GROQ_API_KEY is not set. Copy .env.example to .env and "
                       "add your Groq API key, then restart the app."),
            "sources": sources_from_hits(hits),
        }

    context = build_context(hits)
    user_message = (
        f"Retrieved context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above."
    )

    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # Source attribution is guaranteed programmatically from the retrieved
    # chunks -- we never trust the LLM to list its sources.
    return {"answer": answer, "sources": sources_from_hits(hits)}


def format_sources(sources):
    """Render the source list as readable text for the UI."""
    if not sources:
        return "(no sources retrieved above the relevance threshold)"
    lines = []
    for i, s in enumerate(sources, start=1):
        lines.append(
            f"{i}. {s['title']}  (distance: {s['distance']})\n"
            f"   chunk_id: {s['chunk_id']}\n"
            f"   file: {s['source']}\n"
            f"   url:  {s['url']}"
        )
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Gradio interface
# ---------------------------------------------------------------------------
def ask_ui(question):
    """Gradio wrapper: returns (answer_text, sources_text)."""
    result = ask(question)
    return result["answer"], format_sources(result["sources"])


def build_interface():
    with gr.Blocks(title="The Unofficial Guide — OSU Housing RAG") as demo:
        gr.Markdown(
            "# The Unofficial Guide — OSU Housing & Dorm Life\n"
            "Ask about OSU housing. Answers are grounded **only** in the "
            "retrieved student/official documents; if the documents don't "
            "cover it, the assistant says so."
        )
        question = gr.Textbox(
            label="Your question",
            placeholder="e.g. What do students say about North vs South Campus?",
            lines=2,
        )
        ask_button = gr.Button("Ask", variant="primary")
        answer_box = gr.Textbox(label="Answer", lines=8)
        sources_box = gr.Textbox(label="Sources (attached programmatically)", lines=10)

        ask_button.click(fn=ask_ui, inputs=question, outputs=[answer_box, sources_box])
        question.submit(fn=ask_ui, inputs=question, outputs=[answer_box, sources_box])

        gr.Examples(examples=[[q] for q in EXAMPLE_QUESTIONS], inputs=question)

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860)
