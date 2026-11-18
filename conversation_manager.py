import os, json, re, requests
from copy import deepcopy
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are the conversation brain of an AI shopping concierge for an Amazon India product dataset.
You must have a natural, adaptive conversation. Do NOT follow a fixed questionnaire or ask a fixed number of questions.

Return ONLY valid JSON matching this schema:
{
  "state": {
    "category": {"value": string|null, "source": "explicit|inferred|unknown"},
    "budget_min": {"value": number|null, "source": "explicit|inferred|unknown"},
    "budget_max": {"value": number|null, "source": "explicit|inferred|unknown"},
    "brand_preference": {"value": string|null, "source": "explicit|inferred|unknown"},
    "features": [{"value": string, "source": "explicit|inferred"}],
    "purpose": {"value": string|null, "source": "explicit|inferred|unknown"},
    "min_rating": {"value": number|null, "source": "explicit|inferred|unknown"},
    "min_rating_count": {"value": number|null, "source": "explicit|inferred|unknown"},
    "quality_preference": {"value": string|null, "source": "explicit|inferred|unknown"},
    "answered_topics": [string]
  },
  "ready_to_search": boolean,
  "question": string|null,
  "response": string|null,
  "reason_for_next_action": string
}

CORE BEHAVIOUR:
1. Read the entire conversation AND the existing state. Extract every requirement the customer has already provided, including details given in the first message.
2. Merge new answers into existing state. Never ask for something already answered. If the customer changes or removes an answer, update or clear that value. Treat the latest customer message as an instruction to edit the existing brief when it says remove, ignore, change, increase, decrease, instead, or no preference.
3. Decide dynamically what single clarification would most improve matching. Ask only ONE question at a time, in natural conversational language.
4. Do not force five answers. Search as soon as there is enough information to produce useful matches.
5. If the customer says "any brand", "open to anything", "no preference", record brand_preference.value="any" and mark brand as answered. Never ask brand again.
6. If the customer says "good quality", that is a preference, not a measurable database field. You may ask whether they prioritize higher star ratings or a larger number of reviews. Then map their answer to rating and/or rating_count. Do not claim the dataset has a general quality score.
7. Purpose questions are allowed only when relevant to the product category and can potentially be checked against product_name/about_product. Example for headphones: ask "Mostly for music, work calls, or both?" If the answer is calls, search for supporting description terms such as microphone, mic, ENC, calling. If no supporting evidence exists, do not claim call quality or suitability.
8. Only ask about criteria that can be matched or reasonably checked against the available data:
   - category -> category/product_name
   - budget range -> discounted_price (both minimum and maximum)
   - brand -> product_name/about_product (brand is inferred from text; no dedicated brand column)
   - features/use-case evidence -> product_name/about_product
   - quality -> rating/rating_count
9. Do not ask about durability, comfort, workout suitability, battery life, or other attributes unless the customer explicitly asks and the dataset description can substantiate it. Never invent these claims.
10. Keep the conversation concise and warm. Avoid robotic lists of questions.
11. A user saying "mostly music, but sometimes calls" answers purpose. Do not ask purpose again.
12. If category + a useful filter are already known, generally search. You may ask a relevant clarification first if it meaningfully improves the shortlist (for example purpose for headphones, or brand openness where the user expressed no preference yet).
13. Do not infer a brand from an assistant suggestion. Customer-provided preference must be explicitly stated by the customer.
14. Do not invent numerical thresholds. "Good ratings" can be translated to 4.0 stars as a transparent operational interpretation, source=explicit only if the customer confirms a numeric threshold; otherwise source=inferred.
15. When ready_to_search=true, question must be null. When asking a question, ready_to_search must be false.
16. If the customer explicitly asks to remove a filter, clear it; do not preserve the old value.
17. Interpret price phrases such as above, over, more than, at least, from, between, under, below, up to, maximum, minimum, no budget and any price as price constraints or edits, never as product features.
18. Interpret remove rating, ignore rating, no rating filter, remove brand, any brand, remove ANC and similar phrases as edits to the existing brief.
19. If the customer has supplied a very specific request already (e.g. "Sony wireless earphones under ₹3,000, above 4 stars"), do not ask unnecessary follow-ups; search immediately.
"""

DEFAULT_STATE = {
    "category": {"value": None, "source": "unknown"},
    "budget_min": {"value": None, "source": "unknown"},
    "budget_max": {"value": None, "source": "unknown"},
    "brand_preference": {"value": None, "source": "unknown"},
    "features": [],
    "purpose": {"value": None, "source": "unknown"},
    "min_rating": {"value": None, "source": "unknown"},
    "min_rating_count": {"value": None, "source": "unknown"},
    "quality_preference": {"value": None, "source": "unknown"},
    "answered_topics": []
}

class ConversationManager:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        self.configured = bool(self.api_key)
        self.status = f"OpenRouter · {self.model}" if self.configured else "Demo fallback (API key not configured)"

    def empty_state(self):
        return deepcopy(DEFAULT_STATE)

    def _call_model(self, history, state):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                "EXISTING REQUIREMENT STATE:\n" + json.dumps(state, ensure_ascii=False) +
                "\n\nFULL CONVERSATION:\n" + json.dumps(history, ensure_ascii=False) +
                "\n\nReturn the updated state and decide the next conversational action."}
        ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Findly AI Shopping Concierge"
        }
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.25,
            "response_format": {"type": "json_object"}
        }
        response = requests.post(self.endpoint, headers=headers, json=body, timeout=45)
        response.raise_for_status()
        data = response.json()
        raw = data["choices"][0]["message"]["content"]
        if isinstance(raw, list):
            raw = "".join(part.get("text", "") for part in raw)
        return json.loads(raw)

    def next_turn(self, history, state):
        latest = history[-1]["content"] if history else ""
        if self.configured:
            try:
                decision = self._call_model(history, state)
                return self._explicit_corrections(latest, decision)
            except Exception as exc:
                print("OpenRouter request failed; using local fallback:", exc)
        return self._explicit_corrections(latest, self._fallback(latest, state, history))

    def merge_state(self, old, incoming, clear_fields=None):
        merged = deepcopy(DEFAULT_STATE)
        if isinstance(old, dict):
            for key in merged:
                if key in old:
                    merged[key] = old[key]
        if isinstance(incoming, dict):
            for key in ["category", "budget_min", "budget_max", "brand_preference", "purpose",
                        "min_rating", "min_rating_count", "quality_preference"]:
                item = incoming.get(key)
                if isinstance(item, dict) and item.get("value") is not None:
                    merged[key] = {"value": item.get("value"), "source": item.get("source", "explicit")}
            if isinstance(incoming.get("features"), list):
                by_value = {str(x.get("value", "")).lower(): x for x in merged["features"] if isinstance(x, dict)}
                for item in incoming["features"]:
                    if isinstance(item, dict) and item.get("value"):
                        by_value[str(item["value"]).lower()] = item
                merged["features"] = list(by_value.values())
            if isinstance(incoming.get("answered_topics"), list):
                merged["answered_topics"] = list(dict.fromkeys(merged["answered_topics"] + incoming["answered_topics"]))
        # Explicit user corrections override stale values returned by the LLM.
        for field in (clear_fields or []):
            if field in ["category", "budget_min", "budget_max", "brand_preference", "purpose",
                         "min_rating", "min_rating_count", "quality_preference"]:
                merged[field] = {"value": None, "source": "unknown"}
            elif field == "features":
                merged["features"] = []
        return merged

    def _explicit_corrections(self, message, decision):
        """Deterministically handle explicit edits and price bounds in the latest turn."""
        msg = (message or "").lower().replace(",", "")
        decision = decision if isinstance(decision, dict) else {}
        state = decision.setdefault("state", {})
        clear = set(decision.get("clear_fields", []))
        amount = r"(\d+(?:\.\d+)?)\s*(k|thousand)?"

        def amount_value(number, unit):
            return float(number) * (1000 if (unit or "").lower() in ("k", "thousand") else 1)

        between = re.search(r"\bbetween\s*₹?\s*" + amount + r"\s*(?:and|to|-)\s*₹?\s*" + amount, msg)
        if between:
            state["budget_min"] = {"value": amount_value(between.group(1), between.group(2)), "source": "explicit"}
            state["budget_max"] = {"value": amount_value(between.group(3), between.group(4)), "source": "explicit"}
            clear.discard("budget_min"); clear.discard("budget_max")
        else:
            lower = re.search(r"\b(?:above|over|more than|greater than|at least|starting at|from)\s*₹?\s*" + amount, msg)
            upper = re.search(r"\b(?:under|below|less than|up to|upto|maximum|max)\s*₹?\s*" + amount, msg)
            if lower:
                state["budget_min"] = {"value": amount_value(lower.group(1), lower.group(2)), "source": "explicit"}
                clear.discard("budget_min")
                clear.add("budget_max")  # A new one-sided lower bound replaces an older range.
            if upper:
                state["budget_max"] = {"value": amount_value(upper.group(1), upper.group(2)), "source": "explicit"}
                clear.discard("budget_max")
                clear.add("budget_min")  # A new one-sided upper bound replaces an older range.

        if any(x in msg for x in ["no budget", "any price", "price works", "budget doesn't matter", "budget does not matter", "no price limit", "without budget"]):
            clear.update(["budget_min", "budget_max"])
        if any(x in msg for x in ["remove rating", "remove the rating", "remove ratings", "ignore rating", "ignore the rating", "no rating filter", "without rating", "rating doesn't matter", "rating does not matter", "don't filter by rating", "do not filter by rating"]):
            clear.update(["min_rating", "min_rating_count", "quality_preference"])
        if "remove brand" in msg:
            clear.add("brand_preference")
        elif any(x in msg for x in ["any brand", "no brand preference", "brand doesn't matter", "brand does not matter"]):
            state["brand_preference"] = {"value": "any", "source": "explicit"}
            clear.discard("brand_preference")
        if any(x in msg for x in ["remove anc", "without anc", "remove noise cancellation", "without noise cancellation"]):
            clear.add("features")

        # Prevent purpose phrases and malformed price tokens from becoming mandatory text filters.
        if isinstance(state.get("features"), list):
            blocked = {"calls", "call", "music", "multipurpose", "multi-purpose", "multiple purposes"}
            state["features"] = [f for f in state["features"] if not (
                isinstance(f, dict) and (
                    str(f.get("value", "")).lower() in blocked
                    or re.match(r"price_(?:above|below|under|over)_", str(f.get("value", "")).lower())
                )
            )]
        decision["clear_fields"] = list(clear)
        # Removing a restrictive filter after a failed search should immediately retry.
        if any(x in msg for x in ["remove rating", "remove the rating", "remove ratings", "ignore rating", "ignore the rating", "no rating filter", "without rating", "rating doesn't matter", "rating does not matter"]):
            current_category = state.get("category", {})
            if isinstance(current_category, dict) and current_category.get("value"):
                decision["ready_to_search"] = True
                decision["question"] = None
                decision["response"] = "I've removed the rating requirement. Let me search again."
        return decision

    def _fallback(self, message, old_state, history):
        """Basic deterministic fallback for setup/demo resilience. Live LLM mode is preferred."""
        state = deepcopy(old_state or DEFAULT_STATE)
        msg = message.lower()
        def set_value(key, value, source="explicit"):
            state[key] = {"value": value, "source": source}
        # category detection
        categories = ["wireless earphones", "earphones", "earbuds", "headphones", "running shoes",
                      "shoes", "laptop", "smartphone", "mobile phone", "phone", "speaker",
                      "smartwatch", "watch", "keyboard", "mouse", "monitor", "camera", "tablet"]
        for term in sorted(categories, key=len, reverse=True):
            if term in msg:
                set_value("category", term)
                break
        # Price bounds are parsed centrally in _explicit_corrections.
        for brand in ["sony", "boat", "boAt", "jbl", "samsung", "apple", "realme", "oneplus", "noise", "boult", "hp", "dell", "lenovo", "asus", "logitech", "adidas", "nike"]:
            if brand.lower() in msg:
                set_value("brand_preference", brand)
                break
        if any(x in msg for x in ["any brand", "any brands", "open to anything", "open to any", "no preference"]):
            set_value("brand_preference", "any")
            state["answered_topics"].append("brand")
        # rating / quality
        rating = re.search(r"(\d(?:\.\d)?)\s*\+?\s*(?:star|stars|rating)", msg)
        if rating:
            set_value("min_rating", float(rating.group(1)))
        elif "good rating" in msg or "good ratings" in msg or "highly rated" in msg:
            set_value("min_rating", 4.0, "inferred")
        if any(x in msg for x in ["mostly music", "for music", "work calls", "taking calls", "both music", "calls"]):
            purpose = "mostly music with occasional calls" if ("music" in msg and "call" in msg) else ("work calls" if "call" in msg else "music")
            set_value("purpose", purpose)
            state["answered_topics"].append("purpose")
            if "call" in msg:
                state["features"].append({"value": "microphone", "source": "inferred"})
        if "excellent ratings" in msg or "prioritise ratings" in msg or "prioritize ratings" in msg:
            set_value("quality_preference", "prioritise higher star rating")
            if state["min_rating"]["value"] is None:
                set_value("min_rating", 4.0, "inferred")
            state["answered_topics"].append("quality")
        if "more reviews" in msg or "larger number of reviews" in msg:
            set_value("quality_preference", "prioritise review volume")
            state["answered_topics"].append("quality")
        # Keep feature terms customer actually mentioned
        features = ["wireless", "bluetooth", "noise cancelling", "noise cancellation", "waterproof", "usb-c", "fast charging"]
        for feature in features:
            if feature in msg:
                state["features"].append({"value": feature, "source": "explicit"})
        # dedupe feature values
        seen = set()
        state["features"] = [x for x in state["features"] if not (x["value"].lower() in seen or seen.add(x["value"].lower()))]
        state["answered_topics"] = list(dict.fromkeys(state["answered_topics"]))

        # A purpose question is a relevant first clarification for audio products when not already answered.
        category = (state.get("category") or {}).get("value") or ""
        has_budget = (state.get("budget_max") or {}).get("value") is not None
        has_category = bool(category)
        has_brand = (state.get("brand_preference") or {}).get("value") is not None
        has_purpose = (state.get("purpose") or {}).get("value") is not None
        has_quality = (state.get("min_rating") or {}).get("value") is not None or (state.get("quality_preference") or {}).get("value") is not None

        if has_category and any(x in category for x in ["earphone", "earbud", "headphone"]) and not has_purpose:
            question = "Got it! Are you looking for earphones primarily for music, work calls, or both?"
            ready = False
        elif has_category and has_budget and not has_brand and not has_quality:
            question = "Would you prefer a well-known brand, or are you open to discovering lesser-known brands if the ratings are good?"
            ready = False
        elif has_category and has_budget and has_brand and not has_quality:
            question = "Would you rather prioritise excellent customer ratings or a larger number of customer reviews?"
            ready = False
        elif has_category and (has_budget or has_brand or has_quality or state.get("features")):
            question, ready = None, True
        elif not has_category:
            question, ready = "What type of product are you looking for?", False
        else:
            question, ready = "Do you have a budget or preferred brand in mind?", False

        return {
            "state": state,
            "ready_to_search": ready,
            "question": question,
            "response": "I've understood the details you've shared.",
            "reason_for_next_action": "Local fallback logic; configure OpenRouter for adaptive LLM decisions."
        }
