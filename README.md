# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." --> My system covers unofficial student knowledge about Ohio State University housing and dorm life. This knowledge is valuable because official university housing pages explain policies, rates, requirements, and building options, but they do not fully capture the informal student perspective.
     

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
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

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**  
My final target chunk size was 300–450 characters, with a minimum chunk size of about 180 characters. The final chunks ranged from about 183 to 641 characters.

**Overlap:**  
I used 50–75 characters of overlap.

**Why these choices fit your documents:**  
My documents are short student discussions and official housing summaries. I first tried larger chunks, but retrieval often returned broad source-summary chunks that described what a page was about rather than directly answering the question. I then lowered the chunk size and removed source-summary text, which then made the chunks improved the usefulness of retrieval results.


**Final chunk count:**  
The final pipeline produced 32 chunks across 10 documents. Although this count is lower than expected, I kept the document count at 10 and prioritized chunk quality over increasing the number of chunks.

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. --> 

**Model used:** I used all-MiniLM-L6-v2 from the sentence-transformers library. This model runs locally and does not require paid API access

**Production tradeoff reflection:** A larger embedding model might better capture student language, slang, and dorm-specific terms, but it could be slower or more expensive.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:** The generation step uses Groq. The system prompt instructs the model to answer only from the retrieved context and not use outside knowledge about Ohio State, dorms, Reddit, or housing. The model is also instructed to say: “I don’t have enough information ...” when the retrieved chunks do not contain enough information.


**How source attribution is surfaced in the response:** After the LLM generates an answer, the app appends a source list based on the retrieved chunks. This means the system does not rely only on the model to remember to cite sources.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 |Which OSU dorms are often described as some of the best options on North Campus? |The system should mention dorms such as Scott, Blackburn, Houston, Torres, Bowen, Busch, and/or Nosker depending on sources |According to student discussions, the newer North Campus dorms, including Mendoza and Torres, are often described as strong options. |Relevant |Accurate |
| 2 |What do students say is the tradeoff with Neil and Worthington compared with newer North Campus dorms? |The system should say Neil and Worthington are praised for room features such as kitchen/full fridge/common space/bathroom, but students note their location less convenient for some students. |Students say the tradeoff with Neil and Worthington is that they have better room amenities, such as a full fridge, kitchen with a stove, common space, and a bathroom, but are located far south, which can be inconvenient for classes, unless the student is a medical student | Relevant|Accurate |
| 3 | What does Ohio State officially say regular residence halls provide, and what should students coordinate with roommates? | The system should say regular residence halls include basics such as bed, desk, desk chair, window covering, trash, wardrobe, and refrigerator/microwave unit. |Regular residence halls provide beds, desks, desk chairs, window coverings, trash cans or recycle bins, closets or wardrobe units, and refrigerator/microwave units.|Relevant|Accurate|
| 4 | What do student sources say about the housing lottery or room selection process? | The system should explain that students discuss housing selection as uncertain/priority-based and that desirable dorms can go quickly. It should avoid guaranteeing a specific assignment unless supported by official context. |Student sources suggest that dorm availability during the housing lottery or room selection process depends on the lottery number.|Relevant|Accurate|
| 5 | What is one reported drawback students mention about specific dorm areas or buildings? | The system should retrieve a specific student-reported drawback, such as complaints about fire alarms in Raney or older dorms lacking amenities or air conditioning. |One reported drawback is that Neil and Worthington dorms are not close to most classes because they are located another street down|Relevant|Accurate|

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** Which dorm is the best for freshmen?

**What the system returned:** I do not have enough information to determine the best overall dorm for freshmen. The context provides various student-reported opinions on different dorms, highlighting their strengths and weaknesses, but does not provide a comprehensive or official ranking.

**Root cause (tied to a specific pipeline stage):** This failed because the question is too broad and subjective for the current corpus.

**What you would change to fix it:** I would collect more documents with broader dorm reviews instead of relying only on semantic similarity.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** The planning spec helped because it forced me to decide the domain, document types, chunking strategy, retrieval approach, and evaluation questions before writing the full pipeline. 

**One way your implementation diverged from the spec, and why:** My implementation diverged from the original chunking plan. I first expected to use larger chunks around 800-1200 characters, but early retrieval results were too broad and often returned chunks that described the source instead of directly answering the question.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* I gave the AI my Milestone 3 requirements, my domain, my planning.md chunking strategy, and the structure of my document folder.
- *What it produced:* It produced an ingestion and chunking script that loaded .txt files, cleaned them, chunked them, saved documents/chunks.json.
- *What I changed or overrode:* I did not accept the first version as final. The early chunks started in the middle of words and included source-summary text. I directed the AI to make the chunking sentence-aware, lower the chunk size, and remove some phrases.

**Instance 2**

- *What I gave the AI:* I gave the AI my Milestone 4 requirements, including the embedding model, ChromaDB, cosine distance, metadata requirements, and three retrieval test queries
- *What it produced:* It produced a retrieval script using `all-MiniLM-L6-v2`, ChromaDB, normalized embeddings.
- *What I changed or overrode:* I noticed that Rank 1 was not always the most answer-bearing result and that some lower-ranked chunks were only loosely related. I directed the AI to change retrieval to fetch 8 candidates, filter by distance <= 0.45, and keep the best 4 chunks for generation.
