from dotenv import load_dotenv
import os
import requests

load_dotenv()
fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
hf_api_key = os.getenv("HF_API_KEY")

fireworks_url = "https://api.fireworks.ai/inference/v1/chat/completions"
hf_url = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"

fireworks_headers = {
    "Authorization": f"Bearer {fireworks_api_key}",
    "Content-Type": "application/json"
}

hf_headers = {
    "Authorization": f"Bearer {hf_api_key}"
}


# ---- OPTION 1: Rule-based classifier (keyword + word count) ----
def classify_query_rules(query):
    query_lower = query.lower()
    word_count = len(query.split())

    complex_keywords = [
        "explain", "why", "analyze", "compare", "design",
        "philosophical", "reasoning", "evaluate", "summarize",
        "strategy", "architecture", "optimize"
    ]

    has_complex_keyword = any(word in query_lower for word in complex_keywords)

    if word_count > 15 or has_complex_keyword:
        return "complex"
    else:
        return "simple"


# ---- OPTION 2: AI-based classifier (Hugging Face zero-shot) ----
def classify_query_ai(query):
    payload = {
        "inputs": query,
        "parameters": {
            "candidate_labels": ["simple question", "complex question"]
        }
    }

    response = requests.post(hf_url, headers=hf_headers, json=payload)
    result = response.json()

    try:
        # result is a LIST like [{"label": "...", "score": ...}, ...]
        top_label = result[0]["label"]
        if "simple" in top_label:
            return "simple"
        else:
            return "complex"
    except (KeyError, IndexError, TypeError):
        print("Hugging Face classification failed, falling back to rule-based.")
        return classify_query_rules(query)


# ---- Pick which model to use based on route ----
def get_model_for_route(route):
    if route == "simple":
        return "accounts/fireworks/models/qwen3p7-plus"
    else:
        return "accounts/fireworks/models/deepseek-v4-pro"


# ---- Call Fireworks API with the chosen model ----
def call_model(model, query):
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": query}
        ]
    }
    response = requests.post(fireworks_url, headers=fireworks_headers, json=data)
    return response.json()


# ---- The actual routing agent ----
USE_AI_CLASSIFIER = False

def route_query(query):
    if USE_AI_CLASSIFIER:
        route = classify_query_ai(query)
    else:
        route = classify_query_rules(query)

    model = get_model_for_route(route)

    print(f"\nQuery: {query}")
    print(f"Route decided: {route.upper()} -> using model: {model}")

    result = call_model(model, query)

    try:
        answer = result["choices"][0]["message"]["content"]
        tokens_used = result["usage"]["total_tokens"]
        print(f"Response: {answer}")
        print(f"Tokens used: {tokens_used}")
    except KeyError:
        print("Error from API:", result)


# ---- Test it ----
test_queries = [
    "What is 2+2?",
    "What's the capital of France?",
    "Explain how neural networks learn and why backpropagation works",
    "Compare Python and Java for beginners in terms of learning curve",
    "Why do stars twinkle?"
]

for q in test_queries:
    route_query(q)