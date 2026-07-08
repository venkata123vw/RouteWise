from dotenv import load_dotenv
import os
import requests

load_dotenv()
fireworks_api_key = os.getenv("FIREWORKS_API_KEY")

fireworks_url = "https://api.fireworks.ai/inference/v1/chat/completions"

fireworks_headers = {
    "Authorization": f"Bearer {fireworks_api_key}",
    "Content-Type": "application/json"
}

# ---- Models ----
SIMPLE_MODEL  = "accounts/fireworks/models/qwen3p7-plus"
COMPLEX_MODEL = "accounts/fireworks/models/deepseek-v4-pro"

# ---- Cost per token (USD) ----
COST_PER_TOKEN = {
    "simple":  0.0000009,
    "complex": 0.0000027
}

# ---- Confidence threshold ----
CONFIDENCE_THRESHOLD = 7

# ---- Budget (USD) ----
TOTAL_BUDGET = 0.50

# ---- Session state ----
session = {
    "total_queries":    0,
    "simple_count":     0,
    "complex_count":    0,
    "escalated_count":  0,
    "total_tokens":     0,
    "total_cost":       0.0,
    "total_saved":      0.0,
    "budget_remaining": TOTAL_BUDGET,
    "log": []
}


# ----------------------------------------------------------------
# STEP 1: AI CLASSIFIER
# Uses lightweight model to decide simple vs complex
# ----------------------------------------------------------------
def classify_query(query):
    data = {
        "model": SIMPLE_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Classify the user query as either 'simple' or 'complex'.\n"
                    "Simple: factual, short, single-step, or common knowledge.\n"
                    "Complex: requires reasoning, comparison, explanation, or multi-step thinking.\n"
                    "Reply with exactly one word: simple or complex."
                )
            },
            {"role": "user", "content": query}
        ],
        "max_tokens": 5
    }
    try:
        response = requests.post(fireworks_url, headers=fireworks_headers, json=data)
        result = response.json()
        label = result["choices"][0]["message"]["content"].strip().lower()
        if "complex" in label:
            return "complex"
        elif "simple" in label:
            return "simple"
        else:
            return classify_query_rules(query)
    except Exception:
        return classify_query_rules(query)


# Fallback rule-based classifier
def classify_query_rules(query):
    query_lower = query.lower()
    word_count = len(query.split())
    complex_keywords = [
        "explain", "why", "analyze", "compare", "design",
        "reasoning", "evaluate", "summarize", "strategy",
        "architecture", "optimize", "tradeoff", "how does",
        "mechanism", "mathematically", "difference between"
    ]
    has_complex_keyword = any(kw in query_lower for kw in complex_keywords)
    return "complex" if (word_count > 15 or has_complex_keyword) else "simple"


# ----------------------------------------------------------------
# STEP 2: CALL MODEL
# ----------------------------------------------------------------
def call_model(model, query):
    data = {
        "model": model,
        "messages": [{"role": "user", "content": query}]
    }
    response = requests.post(fireworks_url, headers=fireworks_headers, json=data)
    return response.json()


# ----------------------------------------------------------------
# STEP 3: LOCAL CONFIDENCE SCORING
# Analyzes the response without an extra API call.
#
# Scoring logic:
#   Start at 8 (assume decent answer)
#   -3 if answer contains uncertainty phrases
#   -2 if short answer on a complex-routed query
#   -1 if simple model handled a complex-keyword query
#   +1 if complex model was used
# ----------------------------------------------------------------
def score_confidence(route, query, answer):
    score = 8

    answer_lower = answer.lower()
    word_count = len(answer.split())

    uncertainty_phrases = [
        "i'm not sure", "i am not sure", "i don't know",
        "i cannot", "i can't", "not certain", "unclear",
        "it depends", "you may want to verify", "consult a",
        "i would recommend checking", "i'm unable"
    ]
    if any(phrase in answer_lower for phrase in uncertainty_phrases):
        score -= 3
        print(f"  [Confidence] Uncertainty phrase detected -> -3")

    if word_count < 10 and route != "simple":
        score -= 2
        print(f"  [Confidence] Short answer on complex query ({word_count} words) -> -2")

    complex_keywords = [
        "explain", "mathematically", "analyze", "compare",
        "tradeoff", "mechanism", "architecture"
    ]
    query_lower = query.lower()
    has_complex_keyword = any(kw in query_lower for kw in complex_keywords)
    if route == "simple" and has_complex_keyword:
        score -= 1
        print(f"  [Confidence] Simple model on complex keyword query -> -1")

    if route == "complex":
        score += 1
        print(f"  [Confidence] Complex model used -> +1")

    return max(1, min(10, score))


# ----------------------------------------------------------------
# STEP 4: BUDGET CHECK
# ----------------------------------------------------------------
def budget_check(estimated_tokens, route):
    estimated_cost = estimated_tokens * COST_PER_TOKEN[route]
    return session["budget_remaining"] >= estimated_cost


def update_budget(tokens, route):
    cost = tokens * COST_PER_TOKEN[route]
    session["budget_remaining"] -= cost
    session["total_cost"] += cost
    session["total_tokens"] += tokens
    return cost


# ----------------------------------------------------------------
# MAIN ROUTING AGENT
# ----------------------------------------------------------------
def route_query(query):
    print(f"\n{'='*62}")
    print(f"Query      : {query}")

    # --- Classify ---
    route = classify_query(query)
    model = SIMPLE_MODEL if route == "simple" else COMPLEX_MODEL
    model_name = model.split("/")[-1]

    budget_pct = (session["budget_remaining"] / TOTAL_BUDGET) * 100
    print(f"Classifier : AI -> {route.upper()}")
    print(f"Budget     : ${session['budget_remaining']:.5f} remaining ({budget_pct:.0f}% left)")

    # --- Budget gate ---
    if not budget_check(500, route):
        print("BUDGET EXHAUSTED - skipping query.")
        return

    # --- First model call ---
    print(f"Model      : {model_name}")
    result = call_model(model, query)

    try:
        answer = result["choices"][0]["message"]["content"]
        tokens = result["usage"]["total_tokens"]
    except (KeyError, TypeError):
        print(f"API Error  : {result}")
        return

    cost = update_budget(tokens, route)

    full_cost = tokens * COST_PER_TOKEN["complex"]
    saved = full_cost - cost if route == "simple" else 0.0
    session["total_saved"] += saved

    display = answer[:250] + "..." if len(answer) > 250 else answer
    print(f"\nResponse   : {display}")

    # --- Confidence scoring ---
    confidence = score_confidence(route, query, answer)
    confident = confidence >= CONFIDENCE_THRESHOLD

    escalated = False
    final_model = model_name

    if confident:
        print(f"Confidence : {confidence}/10 [ACCEPTED]")
    else:
        print(f"Confidence : {confidence}/10 [LOW] - escalating to DeepSeek...")

        if not budget_check(800, "complex"):
            print("Not enough budget to escalate - using original answer.")
        else:
            escalated_result = call_model(COMPLEX_MODEL, query)
            try:
                final_answer = escalated_result["choices"][0]["message"]["content"]
                esc_tokens = escalated_result["usage"]["total_tokens"]
            except (KeyError, TypeError):
                print(f"Escalation Error: {escalated_result}")
            else:
                esc_cost = update_budget(esc_tokens, "complex")
                esc_confidence = score_confidence("complex", query, final_answer)
                esc_display = final_answer[:250] + "..." if len(final_answer) > 250 else final_answer

                print(f"Model      : deepseek-v4-pro (escalated)")
                print(f"Response   : {esc_display}")
                print(f"Confidence : {esc_confidence}/10 [ESCALATED - ACCEPTED]")
                print(f"Tokens     : {esc_tokens} | Cost: ${esc_cost:.6f}")
                final_model = "deepseek-v4-pro"
                escalated = True
                session["escalated_count"] += 1

    # --- Update session counts ---
    session["total_queries"] += 1
    if route == "simple":
        session["simple_count"] += 1
    else:
        session["complex_count"] += 1

    print(f"\nTokens     : {tokens} | Cost: ${cost:.6f}", end="")
    if saved > 0:
        print(f" | Saved: ${saved:.6f}", end="")
    print()

    session["log"].append({
        "query":     query,
        "route":     route,
        "model":     final_model,
        "escalated": escalated,
        "tokens":    tokens,
        "cost":      cost,
        "saved":     saved,
    })


# ----------------------------------------------------------------
# SESSION SUMMARY
# ----------------------------------------------------------------
def print_summary():
    print(f"\n{'='*62}")
    print("SESSION SUMMARY")
    print(f"{'='*62}")
    print(f"Total queries    : {session['total_queries']}")
    print(f"Simple routed    : {session['simple_count']}")
    print(f"Complex routed   : {session['complex_count']}")
    print(f"Escalated        : {session['escalated_count']}  <- rescued from low-confidence answers")
    print(f"Total tokens     : {session['total_tokens']}")
    print(f"Total cost       : ${session['total_cost']:.6f}")
    print(f"Total saved      : ${session['total_saved']:.6f}  (vs always using DeepSeek)")
    print(f"Budget used      : ${TOTAL_BUDGET - session['budget_remaining']:.5f} / ${TOTAL_BUDGET:.2f}")
    print(f"Budget remaining : ${session['budget_remaining']:.5f} ({(session['budget_remaining']/TOTAL_BUDGET)*100:.0f}% left)")
    if session["total_queries"] > 0:
        avg = session["total_tokens"] / session["total_queries"]
        print(f"Avg tokens/query : {avg:.0f}")
    if session["escalated_count"] > 0:
        print(f"\nEscalation log (queries rescued from low-confidence answers):")
        for entry in session["log"]:
            if entry["escalated"]:
                print(f"   -> \"{entry['query'][:55]}\"")
    print(f"{'='*62}")


# ----------------------------------------------------------------
# TEST QUERIES
# ----------------------------------------------------------------
test_queries = [
    # Clearly simple
    "What is 2+2?",
    "What's the capital of France?",
    "What year did World War 2 end?",
    "Hi",

    # Edge cases
    "Define recursion",
    "Why do stars twinkle?",
    "Explain quantum entanglement mathematically",

    # Clearly complex
    "Explain how neural networks learn and why backpropagation works",
    "Compare Python and Java for beginners in terms of learning curve",
    "Analyze the tradeoffs between SQL and NoSQL databases for a high-traffic web application",
]

for q in test_queries:
    route_query(q)

print_summary()