import os, json, re
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from conversation_manager import ConversationManager
from product_retriever import ProductRetriever

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-before-sharing")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DATA_PATH = os.getenv("DATA_PATH", "amazon.csv")
retriever = ProductRetriever(DATA_PATH)
conversation = ConversationManager()

@app.route("/")
def home():
    return render_template("index.html", product_count=retriever.product_count,
                           dataset_ready=retriever.ready)

@app.route("/api/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    history = session.get("history", [])
    state = session.get("state", conversation.empty_state())
    history.append({"role": "user", "content": message})

    try:
        decision = conversation.next_turn(history, state)
        new_state = conversation.merge_state(state, decision.get("state", {}), decision.get("clear_fields", []))
        ready = bool(decision.get("ready_to_search", False))

        # Guardrail: don't search without at least a recognizable product category.
        if ready and not new_state.get("category"):
            ready = False
            decision["question"] = "What type of product are you looking for?"

        products = retriever.search(new_state, limit=None) if ready else []
        if ready:
            if products:
                assistant_message = decision.get("response") or "I've got enough to work with. Here are the closest matches I found."
            else:
                assistant_message = "I have enough information to search, but no products matched all those filters. I could not find a record matching the current hard filters. You can broaden the product type, brand or price range, or remove a filter."
        else:
            assistant_message = decision.get("question") or decision.get("response") or "Could you share one more detail that would help narrow the product search?"

        history.append({"role": "assistant", "content": assistant_message})
        session["history"] = history[-16:]
        session["state"] = new_state

        return jsonify({
            "assistant": assistant_message,
            "state": new_state,
            "ready": ready,
            "products": products,
            "product_count": len(products),
            "llm_status": conversation.status,
            "retrieval_status": retriever.status
        })
    except Exception as exc:
        app.logger.exception("Chat request failed")
        return jsonify({"error": "The assistant hit an error. Check the terminal and your API configuration.", "detail": str(exc)}), 500

@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "dataset_ready": retriever.ready,
        "products_loaded": retriever.product_count,
        "llm_configured": conversation.configured,
        "llm_status": conversation.status
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
