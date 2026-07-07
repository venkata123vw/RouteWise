# RouteWise

**Confidence-Aware Budget Router — AMD Developer Hackathon: Act II (Track 1)**

RouteWise is a token-efficient hybrid routing agent that intelligently dispatches queries to the right AI model — saving compute and cost without sacrificing answer quality.

---

## The Problem

Running every query through a powerful (expensive) model wastes money. Running everything through a lightweight model sacrifices quality. RouteWise solves this by routing intelligently — and knowing when it got it wrong.

---

## How It Works

Every query passes through a 4-stage pipeline:

```
Query
  │
  ▼
┌─────────────────────────────┐
│  Stage 1: AI Classifier     │  Qwen3.7 Plus classifies:
│  simple or complex?         │  simple → cheap model
│                             │  complex → powerful model
└─────────────────────────────┘
  │
  ▼
┌─────────────────────────────┐
│  Stage 2: Budget Gate       │  Tracks spend in real time.
│  enough budget remaining?   │  Skips query if budget exhausted.
└─────────────────────────────┘
  │
  ▼
┌─────────────────────────────┐
│  Stage 3: Model Call        │  Routes to:
│                             │  Simple  → Qwen3.7 Plus
│                             │  Complex → DeepSeek-V4-Pro
└─────────────────────────────┘
  │
  ▼
┌─────────────────────────────┐
│  Stage 4: Confidence Score  │  Analyzes the response locally.
│  was the answer good enough?│  Low confidence → escalates
│                             │  to DeepSeek automatically.
└─────────────────────────────┘
```

### Confidence Scoring

Instead of asking the model to rate itself (which triggers unreliable thinking-mode output in both Qwen and DeepSeek on Fireworks), RouteWise scores confidence by analyzing the response it already received — no extra API call needed:

| Condition | Score |
|---|---|
| Baseline | 8/10 |
| Uncertainty phrase detected ("I'm not sure", "I cannot"...) | -3 |
| Short answer on a complex-routed query | -2 |
| Simple model handled a complex-keyword query | -1 |
| Complex model was used | +1 |

If confidence < 7, the query automatically escalates to DeepSeek-V4-Pro.

---

## Results

**10/10 queries correctly routed. 0 unnecessary escalations. Budget used: $0.030 / $0.05 (39% remaining).**

| Query | Route | Model | Tokens | Confidence | Correct? |
|---|---|---|---|---|---|
| "What is 2+2?" | SIMPLE | Qwen3.7 Plus | 208 | 8/10 | ✅ |
| "Capital of France?" | SIMPLE | Qwen3.7 Plus | 132 | 8/10 | ✅ |
| "What year did WW2 end?" | SIMPLE | Qwen3.7 Plus | 302 | 8/10 | ✅ |
| "Hi" | SIMPLE | Qwen3.7 Plus | 267 | 8/10 | ✅ |
| "Define recursion" | SIMPLE | Qwen3.7 Plus | 1,556 | 8/10 | ✅ |
| "Why do stars twinkle?" | COMPLEX | DeepSeek-V4-Pro | 858 | 9/10 | ✅ |
| "Explain quantum entanglement..." | COMPLEX | DeepSeek-V4-Pro | 2,697 | 9/10 | ✅ |
| "Explain neural networks + backprop" | COMPLEX | DeepSeek-V4-Pro | 2,226 | 9/10 | ✅ |
| "Compare Python and Java..." | COMPLEX | DeepSeek-V4-Pro | 2,000 | 9/10 | ✅ |
| "Analyze SQL vs NoSQL..." | COMPLEX | DeepSeek-V4-Pro | 2,624 | 9/10 | ✅ |

Simple queries average **293 tokens**. Complex queries average **2,241 tokens**. RouteWise saves ~**7x tokens** on simple queries by routing them away from the heavy model.

---

## Token Efficiency at Scale

If a system runs 10,000 queries/day with a 50/50 simple/complex split:

| Approach | Daily tokens | Daily cost (est.) |
|---|---|---|
| Always DeepSeek-V4-Pro | ~25,000,000 | ~$67.50 |
| RouteWise hybrid routing | ~12,500,000 | ~$33.75 |
| **Saving** | **~12,500,000** | **~$33.75/day** |

---

## Design Decisions

**Why local confidence scoring instead of self-reported confidence?**

We initially attempted to ask the model to rate its own answer 1-10. During testing, both Qwen3.7 Plus and DeepSeek-V4-Pro on Fireworks responded with thinking-mode preamble (`"We are asked to rate..."`) rather than a number, regardless of prompt engineering or temperature settings. This made self-reported confidence unreliable.

We switched to response-analysis scoring — examining the actual answer for uncertainty signals, length, and keyword mismatch. This approach is faster (no extra API call), more reliable, and fully explainable.

**Why rule-based fallback for the classifier?**

The AI classifier (Qwen3.7 Plus) handles classification well but can fail under rate limiting. The rule-based fallback ensures the router always produces a routing decision, even if the classifier API call fails.

---

## Known Limitations

- Confidence scoring is heuristic — a short but correct answer (e.g. "4") on a simple route is treated correctly, but edge cases exist
- Budget tracking uses estimated token counts for gate checks; actual spend may slightly exceed budget on the final query
- Rate limiting on the Fireworks free tier requires delays between calls, slowing batch processing

---

## Tech Stack

- Python
- Fireworks AI API (serverless inference on AMD MI300X GPUs)
- AMD Developer Cloud
- Docker

---

## Setup

### Requirements
- Docker
- Fireworks AI API key ([get one at fireworks.ai](https://fireworks.ai))

### Run with Docker

1. Clone this repo:
```bash
git clone https://github.com/venkata123vw/RouteWise.git
cd RouteWise
```

2. Create a `.env` file:
```
FIREWORKS_API_KEY=your_key_here
```

3. Build and run:
```bash
docker build -t routewise .
docker run --env-file .env routewise
```

### Expected Output

```
==============================================================
Query      : What is 2+2?
Classifier : AI -> SIMPLE
Budget     : $0.05000 remaining (100% left)
Model      : qwen3p7-plus

Response   : 4
Confidence : 8/10 [ACCEPTED]

Tokens     : 208 | Cost: $0.000187 | Saved: $0.000374

==============================================================
Query      : Explain how neural networks learn and why backpropagation works
Classifier : AI -> COMPLEX
Budget     : $0.03818 remaining (76% left)
Model      : deepseek-v4-pro

Response   : Neural networks learn by adjusting their internal parameters...
  [Confidence] Complex model used -> +1
Confidence : 9/10 [ACCEPTED]

Tokens     : 2226 | Cost: $0.006010

==============================================================
SESSION SUMMARY
==============================================================
Total queries    : 10
Simple routed    : 5
Complex routed   : 5
Escalated        : 0  <- rescued from low-confidence answers
Total tokens     : 12870
Total cost       : $0.030312
Total saved      : $0.004437  (vs always using DeepSeek)
Budget used      : $0.03031 / $0.05
Budget remaining : $0.01969 (39% left)
Avg tokens/query : 1287
==============================================================
```

---

## Built By

Venkata Varshith — Team RouteWise
AMD Developer Hackathon: Act II, Track 1
