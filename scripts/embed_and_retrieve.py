"""
Milestone 4 — Embedding and Retrieval
The Unofficial Guide: unofficial student knowledge about OSU housing and dorm life.

This script:
  1. Loads the chunks created in Milestone 3 (documents/chunks.json)
  2. Embeds each chunk with sentence-transformers all-MiniLM-L6-v2
  3. Stores the chunks + embeddings + metadata in a local ChromaDB collection
     (recreated each run so chunks are never duplicated)
  4. Provides retrieve(query, top_k=5) for semantic search
  5. Runs a few evaluation-style test queries and prints the top results

No Groq, no LLM generation, no answer interface yet. That is Milestone 5.
"""

import os
import json

import chromadb
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Locations and settings
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(PROJECT_ROOT, "documents", "chunks.json")
CHROMA_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"   # sentence-transformers/all-MiniLM-L6-v2
COLLECTION_NAME = "osu_housing"

# Retrieval is a two-stage funnel: pull a wider set of candidates, throw away
# the loosely-related ones, then keep the best few. This matters because rank
# is based purely on semantic (cosine) similarity, so Rank 1 is the *closest*
# vector to the query -- not necessarily the most useful answer-bearing chunk.
# Over-fetching then filtering gives later generation cleaner context.
CANDIDATE_K = 8       # how many candidates to pull from ChromaDB
MAX_DISTANCE = 0.45   # drop candidates whose cosine distance is above this
FINAL_K = 4           # how many chunks to keep after filtering

# A few evaluation-style questions (from the planning.md Evaluation Plan).
TEST_QUERIES = [
    "What do students say about North Campus versus South Campus dorm life?",
    "How does the OSU housing lottery or reselection process affect dorm availability?",
    "What do students say about getting suites or private bathrooms as a freshman?",
]

# We load the model once and reuse it for both indexing and querying.
print(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
model = SentenceTransformer(EMBEDDING_MODEL_NAME)


# ---------------------------------------------------------------------------
# Step 1: Load chunks from Milestone 3
# ---------------------------------------------------------------------------
def load_chunks():
    """Read documents/chunks.json and return the list of chunk dicts."""
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    return chunks


# ---------------------------------------------------------------------------
# Step 2 + 3: Build (or rebuild) the ChromaDB collection
# ---------------------------------------------------------------------------
def safe_metadata(chunk):
    """Build a metadata dict for ChromaDB.

    ChromaDB metadata values must be str/int/float/bool (never None), so we
    fall back to empty strings for any missing optional fields.
    """
    return {
        "source": chunk.get("source") or "",
        "source_title": chunk.get("source_title") or "",
        "source_type": chunk.get("source_type") or "",
        "url": chunk.get("url") or "",
        "chunk_id": chunk.get("chunk_id") or "",
        "char_length": int(chunk.get("char_length") or 0),
    }


def build_collection(chunks):
    """Embed every chunk and store it in a fresh ChromaDB collection.

    The collection is deleted and recreated each run so repeated runs do not
    pile up duplicate chunks.
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Clear any previous version of the collection so we start clean.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # nothing to delete on the first run

    # Use cosine distance (good for normalized sentence embeddings). With
    # normalized vectors, cosine distance ranges roughly 0 (identical) to 2.
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Pull the parallel lists ChromaDB wants.
    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [safe_metadata(c) for c in chunks]

    # Embed all chunk texts in one batch (fast and simple).
    # normalize_embeddings=True pairs with cosine distance in ChromaDB.
    print(f"Embedding {len(documents)} chunks ...")
    embeddings = model.encode(
        documents, show_progress_bar=False, normalize_embeddings=True
    ).tolist()

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"Stored {collection.count()} chunks in ChromaDB at: {CHROMA_DIR}")
    return collection


# ---------------------------------------------------------------------------
# Step 4: Retrieval (over-fetch -> filter -> keep the best few)
# ---------------------------------------------------------------------------
def print_hit(rank, hit):
    """Print a single retrieved chunk with its rank, distance, and metadata."""
    meta = hit["metadata"]
    print(f"\n--- Rank {rank} | distance: {hit['distance']:.4f} ---")
    print(f"source:   {meta.get('source')}")
    print(f"title:    {meta.get('source_title')}")
    print(f"url:      {meta.get('url')}")
    print(f"chunk_id: {meta.get('chunk_id')}")
    print("text:")
    print(hit["text"])


def retrieve(collection, query, candidate_k=CANDIDATE_K,
             max_distance=MAX_DISTANCE, final_k=FINAL_K):
    """Two-stage semantic retrieval for one query.

    1. Pull `candidate_k` nearest chunks from ChromaDB (over-fetch).
    2. Filter out any candidate whose cosine distance is above `max_distance`
       (these are only loosely related to the query).
    3. Keep the best `final_k` of what remains.

    IMPORTANT: ChromaDB orders results by semantic (cosine) similarity alone,
    so Rank 1 is simply the vector closest to the query. The closest chunk is
    not always the most useful answer-bearing one -- sometimes Rank 2 or Rank 3
    reads better. Over-fetching and distance-filtering is how we hand cleaner,
    on-topic context to the generation step later (Milestone 5).
    """
    query_embedding = model.encode([query], normalize_embeddings=True).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=candidate_k,
    )

    # ChromaDB returns one list per query; we only sent one query, so index [0].
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    candidates = [
        {"distance": distance, "metadata": meta, "text": text}
        for text, meta, distance in zip(documents, metadatas, distances)
    ]

    print("\n" + "=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)

    # --- Stage 1: show every raw candidate ChromaDB returned ---
    print(f"\nRAW CANDIDATES (top {candidate_k} by semantic similarity):")
    for rank, hit in enumerate(candidates, start=1):
        print_hit(rank, hit)

    # --- Stage 2: filter by distance, then keep the best final_k ---
    # candidates are already sorted nearest-first, so slicing keeps the best.
    kept = [hit for hit in candidates if hit["distance"] <= max_distance]
    final_hits = kept[:final_k]

    print("\n" + "-" * 70)
    print(f"FILTERED RESULTS (distance <= {max_distance}, keep best {final_k}) "
          f"-> these would be passed to the LLM later:")
    if not final_hits:
        print("  (no candidate passed the distance filter for this query)")
    for rank, hit in enumerate(final_hits, start=1):
        print_hit(rank, hit)

    return final_hits


# ---------------------------------------------------------------------------
# Step 5: Build the index, then run the evaluation-style test queries
# ---------------------------------------------------------------------------
def main():
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    collection = build_collection(chunks)

    print("\n" + "#" * 70)
    print(f"RUNNING TEST QUERIES (fetch {CANDIDATE_K} -> filter <= {MAX_DISTANCE} "
          f"-> keep {FINAL_K})")
    print("#" * 70)
    for query in TEST_QUERIES:
        retrieve(collection, query)


if __name__ == "__main__":
    main()
