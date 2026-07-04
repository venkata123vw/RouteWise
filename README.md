# RouteWise
**Token-efficient hybrid routing agent — AMD Developer Hackathon: Act II (Track 1)**

## What It Does
RouteWise analyzes incoming queries and intelligently routes them to one of two models based on complexity — avoiding wasted compute on simple questions while giving complex ones the reasoning power they need.

- **Simple queries** → Qwen3.7 Plus (fast, low-cost, low-latency)
- **Complex queries** → DeepSeek-V4-Pro (powerful, deeper reasoning)

## Results

| Query | Route | Model | Tokens Used | Correct? |
|---|---|---|---|---|
| "What is 2+2?" | SIMPLE | Qwen3.7 Plus | 322 | ✅ |
| "Capital of France?" | SIMPLE | Qwen3.7 Plus | 131 | ✅ |
| "Explain how neural networks learn..." | COMPLEX | DeepSeek-V4-Pro | 1,986 | ✅ |
| "Compare Python and Java..." | COMPLEX | DeepSeek-V4-Pro | 1,621 | ✅ |
| "Why do stars twinkle?" | COMPLEX | DeepSeek-V4-Pro | 576 | ✅ |

**Simple queries average ~227 tokens. Complex queries average ~1,394 tokens. RouteWise saves ~7x tokens on simple queries by routing them away from the heavy model.**

## How Routing Works
The classifier checks two things:

1. **Word count** — queries longer than 15 words are flagged as complex
2. **Keyword matching** — presence of words like "explain," "compare," "analyze," "why" suggests deeper reasoning is needed

If either condition is true, the query is routed as complex.

## Design Decisions
We initially tested a zero-shot AI classifier (Hugging Face `bart-large-mnli`) to decide simple vs complex queries. In testing, it was heavily biased toward classifying every query as simple (confidence scores consistently 55–65%, even for genuinely complex prompts). This would have defeated the purpose of routing.

We measured actual token usage per query to validate our final approach and chose the keyword + word-count heuristic as the production classifier since it reliably distinguished query types in testing.

## Known Limitations
- Keyword-based classification can misfire on short-but-nuanced queries (e.g., "Why do stars twinkle?" triggers complex due to the word "why," even though it's a fairly simple question)
- Future improvement: use a lightweight embedding model or semantic similarity check for more accurate classification

## Tech Stack
- Python
- Fireworks AI API (serverless inference on AMD MI300X GPUs)
- AMD Developer Cloud
- Docker

## Setup

### Requirements
- Docker
- Fireworks AI API key ([get one at fireworks.ai](https://fireworks.ai))

### Run with Docker

1. Clone this repo:
```bash
git clone https://github.com/venkata123vw/RouteWise.git
cd RouteWise
2. Create a `.env` file with your Fireworks API key:
FIREWORKS_API_KEY=your_key_here
3. Build and run:
```bash
docker build -t routewise .
docker run --env-file .env routewise
```

### Expected Output
Query: What is 2+2?
Route decided: SIMPLE -> using model: accounts/fireworks/models/qwen3p7-plus
Response: 2 + 2 = 4
Tokens used: 322
Query: Explain how neural networks learn and why backpropagation works
Route decided: COMPLEX -> using model: accounts/fireworks/models/deepseek-v4-pro
Response: Neural networks learn by adjusting their internal parameters...
Tokens used: 1986

## Built By
Venkata Varshith — Team RouteWise  
AMD Developer Hackathon: Act II, Track 1
```

2. Create a `.env` file with your Fireworks API key:
