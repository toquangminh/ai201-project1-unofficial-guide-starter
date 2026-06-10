"""
Milestone 3 — Document Ingestion and Chunking
The Unofficial Guide: unofficial student knowledge about OSU housing and dorm life.

This script does five things and nothing more:
  1. Load every .txt file from documents/raw/
  2. Clean each document (strip HTML, entities, boilerplate, blank/junk lines)
  3. Save the cleaned text into documents/processed/
  4. Split cleaned text into paragraph- AND sentence-aware chunks
     (300-450 chars, 50-75 chars of whole-sentence overlap)
  5. Save chunks to documents/chunks.json and print summary stats + 5 sample chunks

No embeddings, no vector store, no retrieval, no LLM. Those come in later milestones.
"""

import os
import re
import json
import glob
import html
import random

# ---------------------------------------------------------------------------
# Folder locations (relative to the project root, not this script's folder).
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "documents", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "documents", "processed")
CHUNKS_FILE = os.path.join(PROJECT_ROOT, "documents", "chunks.json")

# ---------------------------------------------------------------------------
# Chunking settings (from the planning.md Chunking Strategy section).
# Sizes are measured in characters and INCLUDE the overlap text.
# ---------------------------------------------------------------------------
TARGET_MAX = 450      # stop adding sentences once a chunk passes this size
OVERLAP_MIN = 50      # carry at least this many chars of context into next chunk
OVERLAP_MAX = 75      # ...but no more than this (overlap is whole sentences)
MIN_CHUNK_SIZE = 180  # a chunk must reach this before we close it (target ~300-450)


# ---------------------------------------------------------------------------
# Step 1: Load raw documents
# ---------------------------------------------------------------------------
def load_documents():
    """Read every .txt file in documents/raw/ and return a list of dicts."""
    documents = []
    pattern = os.path.join(RAW_DIR, "*.txt")
    for path in sorted(glob.glob(pattern)):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        documents.append({
            "filename": os.path.basename(path),
            "text": text,
        })
    return documents


# ---------------------------------------------------------------------------
# Step 2: Clean a single document
# ---------------------------------------------------------------------------

# Lines that are pure boilerplate / navigation / UI noise. If a line matches
# any of these patterns we drop it. Kept simple and readable on purpose.
BOILERPLATE_PATTERNS = [
    r"^\s*(home|menu|search|login|log in|sign up|sign in)\s*$",
    r"^\s*(share|reply|report|save|award|upvote|downvote)\s*$",
    r"^\s*(cookie|cookies|privacy policy|terms of service|all rights reserved)",
    r"^\s*(advertisement|sponsored|ad)\s*$",
    r"^\s*\d+\s*(points?|comments?|upvotes?)\s*$",   # "42 points", "8 comments"
    r"^\s*(next|previous|back to top|read more|continue reading)\s*$",
    r"^\s*posted by\s+u/",                            # reddit byline
    r"^\s*\d+\s+(years?|months?|days?|hours?)\s+ago\s*$",
]


def is_boilerplate(line):
    """Return True if a line looks like navigation / UI / boilerplate noise."""
    for pattern in BOILERPLATE_PATTERNS:
        if re.search(pattern, line, flags=re.IGNORECASE):
            return True
    return False


def is_substantive(line):
    """Return True if a line carries real content worth keeping.

    We keep student opinions, dorm descriptions, advice, complaints, ratings,
    and context (dorm names, campus areas). We drop scraps that are too short
    to mean anything (like a stray '·' or a single punctuation mark).
    """
    stripped = line.strip()
    if stripped == "":
        return False
    # Must contain at least one letter or digit to be meaningful.
    if not re.search(r"[A-Za-z0-9]", stripped):
        return False
    # Drop ultra-short fragments that are not whole words (e.g. "x", "—").
    if len(stripped) < 3:
        return False
    return True


# Project meta-commentary: notes written FOR this project (how the RAG system
# should use a source) rather than actual source content.
PROJECT_META_PATTERNS = [
    r"\bfor the rag system\b",
    r"\bthe rag system\b",
    r"\bthe system should\b",
    r"\bthis (source|document) should be (treated|used)\b",
    r"\bshould be treated as\b",
    r"\bit can answer\b",
    r"\bit can support answers\b",
    r"\bcan support answers\b",
    r"\bcan be combined with student\b",
    r"\bif a user asks\b",
    r"\banswer should\b",
    r"\bopinion source\b",
    r"\bhelps answer\b",
    r"\bdoes not provide student opinions\b",
]

# Source-summary framing: sentences that DESCRIBE the source ("This Reddit
# thread compares...", "It is useful because...") instead of carrying
# answer-bearing content. We drop these so retrieval returns real opinions,
# facts, dorm names, and examples rather than descriptions of the source.
# The "^this ..." patterns are anchored to the sentence start so we only catch
# descriptive openers ("This page is about...") and keep content sentences
# like "The page says..." or "The directory includes...".
SOURCE_SUMMARY_PATTERNS = [
    r"^this reddit thread\b",
    r"^this thread\b",
    r"^this (reddit )?megathread\b",
    r"^this official\b",
    r"^this r/osu\b",
    r"^this wiki\b",
    r"^this source\b",
    r"^this document\b",
    r"^this page\b",
    r"\bit is useful\b",
    r"\bis useful (because|for|as)\b",
    r"\bthe page is useful\b",
]

# Any sentence matching one of these is dropped during cleaning.
REMOVE_PATTERNS = PROJECT_META_PATTERNS + SOURCE_SUMMARY_PATTERNS


def is_meta_commentary(sentence):
    """Return True if a sentence is meta-commentary or source-summary framing.

    These describe the source or instruct the project, rather than carrying
    answer-bearing content, so they should not be embedded.
    """
    sentence = sentence.strip()
    for pattern in REMOVE_PATTERNS:
        if re.search(pattern, sentence, flags=re.IGNORECASE):
            return True
    return False


def remove_meta_commentary(line):
    """Drop meta / source-summary sentences from a line, keeping real content.

    We split the line into sentences and remove any sentence that describes the
    source or is written for the project (e.g. "This Reddit thread compares...",
    "It is useful because...", "For the RAG system..."). Whatever real content
    remains (student opinions, dorm names, examples) is rejoined.
    """
    sentences = re.split(r"(?<=[.!?])\s+", line)
    kept = [s for s in sentences if not is_meta_commentary(s)]
    return " ".join(kept).strip()


def clean_text(text):
    """Clean one document's raw text and return tidy, readable text.

    Cleaning steps:
      - decode HTML entities (&amp;, &nbsp;, etc.)
      - remove HTML tags (<p>, <div>, ...)
      - collapse repeated whitespace inside each line
      - drop empty lines, boilerplate, and non-substantive lines
      - drop project meta-commentary sentences ("For the RAG system...")
      - preserve paragraph breaks (blank line between paragraphs)
    """
    # Turn &amp; -> &, &nbsp; -> space, etc. (do this before stripping tags).
    text = html.unescape(text)

    # Remove anything that looks like an HTML tag.
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize line endings so splitting on "\n" is reliable.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    kept_lines = []
    for line in text.split("\n"):
        # Collapse runs of spaces/tabs into a single space.
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line == "":
            # Keep a single blank line as a paragraph separator (no doubles).
            if kept_lines and kept_lines[-1] != "":
                kept_lines.append("")
            continue

        if is_boilerplate(line):
            continue

        # Remove project meta-commentary sentences; skip the line if nothing
        # substantive is left after that.
        line = remove_meta_commentary(line)
        if not is_substantive(line):
            continue

        kept_lines.append(line)

    # Join, then make sure we never have more than one blank line in a row.
    cleaned = "\n".join(kept_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Step 2b: Pull the header metadata (title / type / URL) out of the body
# ---------------------------------------------------------------------------
def parse_document(cleaned_text):
    """Separate the header metadata from the body of a cleaned document.

    Our raw files start with a small header like:
        Source title: ...
        Source type: ...
        URL: ...
    We lift those into metadata and return the remaining text as the body so
    they don't get repeated inside every chunk.
    """
    meta = {"source_title": None, "source_type": None, "url": None}
    body_lines = []

    for line in cleaned_text.split("\n"):
        low = line.lower()
        if low.startswith("source title:"):
            meta["source_title"] = line.split(":", 1)[1].strip()
        elif low.startswith("source type:"):
            meta["source_type"] = line.split(":", 1)[1].strip()
        elif low.startswith("url:"):
            meta["url"] = line.split(":", 1)[1].strip()
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    return meta, body


# ---------------------------------------------------------------------------
# Step 3: Save cleaned documents
# ---------------------------------------------------------------------------
def save_processed(filename, cleaned_text):
    """Write one cleaned document into documents/processed/."""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    out_path = os.path.join(PROCESSED_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)


# ---------------------------------------------------------------------------
# Step 4: Paragraph- and sentence-aware chunking
# ---------------------------------------------------------------------------
def split_sentences(paragraph):
    """Split a paragraph into sentences on . ! ? followed by whitespace.

    This is a simple splitter (no NLP library). It is good enough for our
    student-written prose and, crucially, it never cuts inside a word.
    """
    parts = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return [p.strip() for p in parts if p.strip()]


def to_sentence_units(body):
    """Turn a document body into a flat list of (sentence, paragraph_index).

    Keeping the paragraph index lets us re-join sentences with a blank line
    between paragraphs and a single space within a paragraph.
    """
    units = []
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    for para_index, para in enumerate(paragraphs):
        for sentence in split_sentences(para):
            units.append((sentence, para_index))
    return units


def render(units):
    """Join a list of (sentence, paragraph_index) units back into text.

    Sentences in the same paragraph are joined with a space; a paragraph
    change inserts a blank line so the chunk stays readable.
    """
    out = ""
    for i, (sentence, para_index) in enumerate(units):
        if i == 0:
            out = sentence
        else:
            same_paragraph = para_index == units[i - 1][1]
            out += (" " if same_paragraph else "\n\n") + sentence
    return out.strip()


def make_overlap(units):
    """Pick trailing WHOLE sentences to reuse as overlap in the next chunk.

    We walk backwards collecting complete sentences until we have at least
    OVERLAP_MIN characters, stopping before we exceed OVERLAP_MAX. Because we
    only ever take complete sentences, the next chunk can never begin with a
    broken word or a random mid-sentence fragment.

    If even the single trailing sentence is longer than OVERLAP_MAX, we return
    no overlap at all rather than dragging a huge sentence into the next chunk
    (that would bloat the chunk well past its target size).
    """
    chosen = []
    total = 0
    for unit in reversed(units):
        sentence = unit[0]
        # Stop once adding another whole sentence would exceed the max.
        if total + len(sentence) + 1 > OVERLAP_MAX:
            break
        chosen.insert(0, unit)
        total += len(sentence) + 1
        if total >= OVERLAP_MIN:
            break
    return chosen


def chunk_document(body):
    """Split one document body into overlapping, sentence-clean chunks.

    A chunk is built from two parts:
      - overlap : whole sentences carried over from the previous chunk
      - new     : fresh sentences added until we reach the target size
    Because chunks always start at a sentence boundary (either the start of
    the overlap or the start of a paragraph), they read as self-contained.
    """
    units = to_sentence_units(body)
    if not units:
        return []

    chunks = []                       # finished chunks, each a list of units
    overlap = []                      # leading overlap units of current chunk
    new = []                          # fresh units of current chunk

    for unit in units:
        current_len = len(render(overlap + new))
        candidate_len = len(render(overlap + new + [unit]))

        # Close the current chunk when adding the next sentence would push it
        # past the max, as long as we already have at least MIN_CHUNK_SIZE of
        # text. Closing here (rather than waiting) stops a single long sentence
        # from ballooning the chunk. We always split on a sentence boundary,
        # never inside a word.
        if new and candidate_len > TARGET_MAX and current_len >= MIN_CHUNK_SIZE:
            chunks.append(overlap + new)
            overlap = make_overlap(overlap + new)
            new = [unit]
        else:
            new.append(unit)

    if new:
        chunks.append(overlap + new)

    # Avoid a tiny trailing fragment: fold its FRESH sentences into the
    # previous chunk. We skip the fragment's overlap part (those sentences are
    # already the tail of the previous chunk) so nothing gets duplicated.
    if len(chunks) >= 2 and len(render(chunks[-1])) < MIN_CHUNK_SIZE:
        tail = chunks.pop()
        overlap_len = len(make_overlap(chunks[-1]))
        fresh_tail = tail[overlap_len:]
        chunks[-1] = chunks[-1] + fresh_tail

    return [render(c) for c in chunks]


def build_chunk_records(body, meta, source_filename):
    """Chunk a document body and attach metadata to each chunk."""
    records = []
    for i, text in enumerate(chunk_document(body)):
        records.append({
            "source": source_filename,
            "source_title": meta["source_title"],
            "source_type": meta["source_type"],
            "url": meta["url"],
            "chunk_id": f"{source_filename}::chunk_{i}",
            "char_length": len(text),
            "text": text,
        })
    return records


# ---------------------------------------------------------------------------
# Step 5: Run the whole pipeline and report
# ---------------------------------------------------------------------------
def looks_broken(text):
    """True if a chunk starts with a lowercase word (a sign of bad overlap).

    A clean, sentence-aware chunk should begin with a capital letter, a digit,
    or an opening quote. A leading lowercase letter usually means a word was
    cut in half by a raw character slice.
    """
    first = text.lstrip()
    return bool(first) and first[0].islower()


def main():
    documents = load_documents()

    cleaned_count = 0
    all_chunks = []

    for doc in documents:
        cleaned = clean_text(doc["text"])
        if not cleaned:
            # Nothing substantive survived cleaning; skip this file.
            continue
        cleaned_count += 1
        save_processed(doc["filename"], cleaned)

        meta, body = parse_document(cleaned)
        all_chunks.extend(build_chunk_records(body, meta, doc["filename"]))

    # Save all chunks to one JSON file.
    os.makedirs(os.path.dirname(CHUNKS_FILE), exist_ok=True)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    # --- Summary statistics ---
    lengths = [c["char_length"] for c in all_chunks]
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    min_len = min(lengths) if lengths else 0
    max_len = max(lengths) if lengths else 0

    print("=" * 60)
    print("INGESTION + CHUNKING SUMMARY")
    print("=" * 60)
    print(f"Documents loaded:   {len(documents)}")
    print(f"Documents cleaned:  {cleaned_count}")
    print(f"Chunks created:     {len(all_chunks)}")
    print(f"Chunk length (chars) -> min: {min_len}  max: {max_len}  avg: {avg_len:.0f}")
    print(f"Chunks saved to:    {CHUNKS_FILE}")

    # --- Validation / warnings ---
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    warnings = 0

    if len(all_chunks) < 40:
        warnings += 1
        print(f"WARNING: only {len(all_chunks)} chunks created (fewer than 40). "
              "This is expected for a small corpus; add more/longer sources to grow it.")

    broken = [c["chunk_id"] for c in all_chunks if looks_broken(c["text"])]
    if broken:
        warnings += 1
        print(f"WARNING: {len(broken)} chunk(s) start with a lowercase/broken-looking word:")
        for chunk_id in broken:
            print(f"  - {chunk_id}")

    tiny = [c["chunk_id"] for c in all_chunks if c["char_length"] < MIN_CHUNK_SIZE]
    if tiny:
        warnings += 1
        print(f"WARNING: {len(tiny)} chunk(s) are shorter than {MIN_CHUNK_SIZE} chars:")
        for chunk_id in tiny:
            print(f"  - {chunk_id}")

    if warnings == 0:
        print("All checks passed: no broken-word starts and no unexpected tiny chunks.")

    # --- 5 random representative chunks for inspection ---
    print()
    print("=" * 60)
    print("5 RANDOM SAMPLE CHUNKS")
    print("=" * 60)
    sample = random.sample(all_chunks, min(5, len(all_chunks)))
    print_chunks(sample)

    # --- 5 answer-bearing chunks (none contain source-summary phrases) ---
    # After cleaning, no chunk should contain the removed framing phrases; this
    # section verifies that and shows what the answer-bearing chunks look like.
    print()
    print("=" * 60)
    print("5 CHUNKS WITH NO SOURCE-SUMMARY PHRASES (answer-bearing)")
    print("=" * 60)
    answer_bearing = [c for c in all_chunks if not has_summary_phrase(c["text"])]
    print(f"{len(answer_bearing)} of {len(all_chunks)} chunks are free of source-summary phrases.")
    print_chunks(random.sample(answer_bearing, min(5, len(answer_bearing))))


# Plain-language phrases used only to verify (and show) that chunks no longer
# contain source-summary framing.
SUMMARY_CHECK_PHRASES = [
    "this reddit thread", "this thread", "this megathread", "this official",
    "this r/osu", "this wiki", "this source", "this document", "this page",
    "it is useful", "is useful because", "is useful for", "is useful as",
    "the page is useful", "for the rag system", "should be treated as",
    "can support answers",
]


def has_summary_phrase(text):
    """Return True if a chunk still contains any removed source-summary phrase."""
    low = text.lower()
    return any(phrase in low for phrase in SUMMARY_CHECK_PHRASES)


def print_chunks(chunks):
    """Print a list of chunk records for inspection."""
    for c in chunks:
        title = c["source_title"] or "(no title)"
        print(f"\n[{c['chunk_id']}]  ({c['char_length']} chars)")
        print(f"title: {title} | type: {c['source_type']} | url: {c['url']}")
        print("-" * 60)
        print(c["text"])


if __name__ == "__main__":
    main()
