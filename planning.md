# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
Unofficial student knowledge about Ohio State University housing and dorm life
---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 |Ohio State Residence Halls directory | Official list of Columbus campus residence halls. | https://housing.osu.edu/roomsearch/ |
| 2 |Ohio State Incoming Students housing page | Official housing requirement and incoming-student housing overview. | https://housing.osu.edu/incoming-students/ |
| 3 |Ohio State Standard Housing Rates | Official housing rate information | https://housing.osu.edu/incoming-students/fees-contracts-policies/standard-housing-rates/ |
| 4 |Ohio State What To Bring | Official packing guide | https://housing.osu.edu/resources/what-to-bring/ |
| 5 | r/OSU Wiki: A Guide to Dorm Life | Student/community-maintained guide to dorm life | https://www.reddit.com/r/OSU/wiki/dorms/ |
| 6 | r/OSU thread: Best dorms at OSU | Student discussion about which dorms are considered best and why | https://www.reddit.com/r/OSU/comments/14eh4zt/best_dorms_at_osu/ |
| 7 | r/OSU thread: Best Dorms / Dorm Rankings? | Student discussion ranking dorms. | https://www.reddit.com/r/OSU/comments/1e7q64x/best_dorms_dorm_rankings/ |
| 8 | r/OSU thread: North vs South vs West Campus | Student discussion comparing campus areas. | https://www.reddit.com/r/OSU/comments/1khbaud/north_vs_south_vs_west_campus/ |
| 9 | r/OSU thread: Housing/Dorm Questions | Student Q&A about freshmen housing, suites, bathrooms, accommodations, and lottery-related expectations. | https://www.reddit.com/r/OSU/comments/1qvp9bm/housingdorm_questions/ |
| 10 | r/OSU On-Campus Housing Reselection Megathread 2023-24 | Housing lottery and room-selection discussion; useful for questions about selection uncertainty and student experiences. | https://www.reddit.com/r/OSU/comments/12bzc40/oncampus_housing_reselection_megathread_202324/ |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 800–1,200 characters per chunk

**Overlap:** 150–200 characters of overlap.

**Reasoning:**
My corpus is mixed. Some sources are short, opinion-based student posts or comments, while others are longer official pages or student media articles. For Reddit-style reviews and comments, the key evidence is often only one or two sentences, so very large chunks could mix unrelated opinions about different dorms. For official pages and longer guides, chunks need enough context to preserve the relationship between a rule, a dorm name, and the explanation around it.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** all-MiniLM-L6-v2 via sentence-transformers

**Top-k:** Retrieve the top 5 chunks per query

**Production tradeoff reflection:**
If top-k is too low, the system may miss a relevant source, especially when students use different wording. If top-k is too high, the LLM may receive conflicting or off-topic chunks and produce a vague answer. Semantic search is useful here because students may ask “Which dorms feel most social?” while the documents might say “best dorm culture,” “good atmosphere,” or “people were friendly.”

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | According to student discussions, which OSU dorms are often described as some of the best options on North Campus? | The system should mention dorms such as Scott, Blackburn, Houston, Torres, Bowen, Busch, and/or Nosker depending on sources|
| 2 | What do students say is the tradeoff with Neil and Worthington compared with newer North Campus dorms? | The system should say Neil and Worthington are praised for room features such as kitchen/full fridge/common space/bathroom, but students note their location less convenient for some students. |
| 3 | What does Ohio State officially say regular residence halls provide, and what should students coordinate with roommates? | The system should say regular residence halls include basics such as bed, desk, desk chair, window covering, trash, wardrobe, and refrigerator/microwave unit. |
| 4 | What do student sources say about the housing lottery or room selection process? | The system should explain that students discuss housing selection as uncertain/priority-based and that desirable dorms can go quickly. It should avoid guaranteeing a specific assignment unless supported by official context. |
| 5 | What is one reported drawback students mention about specific dorm areas or buildings? | The system should retrieve a specific student-reported drawback, such as complaints about fire alarms in Raney or older dorms lacking amenities or air conditioning. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Inconsistent student opinions: Reddit comments and student discussions may disagree.

2. Source attribution may be difficult for informal sources: Reddit threads often contain many comments on one page.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```text

   .----------------------.
  /  1. Document Ingestion \
 /--------------------------\
 |  Python loaders           |
 |  - requests               |
 |  - markdown/text files    |
 \--------------------------/
             |
             v
   .----------------------------.
  /  2. Cleaning + Preprocessing \
 /--------------------------------\
 |  Remove:                       |
 |  - navigation text             |
 |  - ads                         |
 |  - repeated UI text            |
 |  - empty lines                 |
 \--------------------------------/
             |
             v
   .----------------------------.
  /       3. Chunking             \
 /--------------------------------\
 |  Paragraph/comment-aware       |
 |  chunks                        |
 |                                |
 |  Target size: 800-1200 chars   |
 |  Overlap: 150-200 chars        |
 \--------------------------------/
             |
             v
   .-------------------------------.
  / 4. Embedding + Vector Store     \
 /-----------------------------------\
 |  Embedding model:                 |
 |  sentence-transformers            |
 |  all-MiniLM-L6-v2                 |
 |                                   |
 |  Vector database:                 |
 |  ChromaDB                         |
 \-----------------------------------/
             |
             v
   .----------------------------.
  /        5. Retrieval          \
 /--------------------------------\
 |  Semantic similarity search    |
 |  Retrieve top-k = 5 chunks     |
 \--------------------------------/
             |
             v
   .-------------------------------.
  /        6. Generation            \
 /-----------------------------------\
 |  Rules:                           |
 |  - answer only from retrieved     |
 |    context                        |
 |  - include source citations       |
 \-----------------------------------/
             |
             v
   .----------------------------.
  /     7. Query Interface       \
 /--------------------------------\
 |  CLI or simple web UI          |
 \--------------------------------/
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
I will give the Claude the Domain, Documents, and Chunking Strategy sections from this planning document and ask it to implement the document ingestion and chunking functions.

**Milestone 4 — Embedding and retrieval:**

I will use Claude to help implement embedding and ChromaDB retrieval. I will give Claude the Retrieval Approach section, the chunk metadata format, and the requirement that semantic search should return top relevant chunks for a user query.

**Milestone 5 — Generation and interface:**
I will use Claude to help build the grounded response generation and query interface. I will give Claude the Evaluation Plan, Architecture diagram to do it.
