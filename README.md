# RouteWise

**Token-efficient routing agent - AMD Developer Hackathon: Act II (Track 1)**

## What It Does

RouteWise analyzes incoming user queries and intelligently routes them to one of two models based on complexity:

- **Simple queries** -> routed to a fast, lightweight model (Qwen3.7 Plus) - low cost, low latency
- **Complex queries** -> routed to a powerful reasoning model (DeepSeek-V4-Pro) - higher cost, deeper reasoning

This avoids wasting compute/cost on simple questions while still giving complex questions the resources they need.

## How Routing Works

The classifier checks two things:

1. **Word count** - queries longer than 15 words are flagged as complex
2. **Keyword matching** - presence of words like "explain," "compare," "analyze," "why" suggests deeper reasoning is needed

If either condition is true, the query is routed as "complex."

## Example

| Query | Route | Model Used |
|---|---|---|
| "What is 2+2?" | Simple | Qwen3.7 Plus |
| "Explain how neural networks learn" | Complex | DeepSeek-V4-Pro |

## Tech Stack

- Python
- Fireworks AI API (serverless inference)
- AMD Developer Cloud

## Design Decisions

We initially tested a zero-shot AI classifier (Hugging Face `bart-large-mnli`) to decide simple vs complex queries, instead of manual rules. In testing, it was heavily biased toward classifying every query as "simple" (confidence scores consistently 55-65% simple, even for genuinely complex prompts like explaining neural networks or comparing programming languages). This would have defeated the purpose of routing, since complex queries would always go to the weaker model.

We measured actual token usage per query to validate our final approach:

| Query Type | Example | Tokens Used |
|---|---|---|
| Simple | "What is 2+2?" | 507 |
| Simple | "Capital of France?" | 131 |
| Complex | "Explain neural networks..." | 2732 |
| Complex | "Compare Python and Java..." | 1784 |

Based on this evidence, we chose our keyword + word-count heuristic as the production classifier, since it reliably distinguished simple and complex queries in testing.

## Known Limitations

- Keyword-based classification can misfire on short-but-nuanced queries (e.g., "Why do stars twinkle?" triggers "complex" due to the word "why," even though it's a fairly simple question)
- Future improvement: use a lightweight model or semantic similarity check for more accurate classification instead of hardcoded keywords

## Setup

1. Clone this repo
2. Create a `.env` file with your Fireworks API key (get your own key from fireworks.ai - never share or commit this):

```
FIREWORKS_API_KEY=your_key_here
```

3. Install dependencies:

```
pip install requests python-dotenv
```

4. Run:

```
python router.py
```

## Built By

Venkata Varshith - Team RouteWise
AMD Developer Hackathon: Act II, Track 1
