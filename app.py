from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient

from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

# ---------------- FLASK SETUP ---------------- #

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "DELETE", "OPTIONS"]
    }
})

# ---------------- MONGODB ---------------- #

try:
    mongo_client = MongoClient("mongodb://localhost:27017/")
    db = mongo_client["campus-genie"]

    chat_history_collection = db["chat_history"]

    mongo_client.admin.command("ping")

    print("[OK] MongoDB Connected Successfully")

except Exception as e:
    print("[ERROR] MongoDB Error:", e)
    raise

# ---------------- OPENROUTER ---------------- #

import os
from openai import OpenAI

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY environment variable is not set."
    )

MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "qwen/qwen2.5-vl-32b-instruct:free"
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
# ---------------- EMBEDDINGS ---------------- #

embedding_function = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# ---------------- LOAD FAISS ---------------- #

persist_directory = "./faiss_index"

if not os.path.exists(persist_directory):
    raise FileNotFoundError(
        "[ERROR] 'faiss_index' folder not found"
    )

vectorstore = FAISS.load_local(
    persist_directory,
    embeddings=embedding_function,
    allow_dangerous_deserialization=True
)

print("[OK] FAISS Loaded Successfully")


# ---------------- LLM FUNCTION ---------------- #

def llm(prompt):

    try:

        response = client.chat.completions.create(

            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.7,
            max_tokens=300,

            extra_headers={
                "HTTP-Referer": "http://localhost:4000",
                "X-Title": "Campus Genie"
            }

        )

        return response.choices[0].message.content

    except Exception as e:

        print("OpenRouter Error:", str(e))

        return "Sorry, I'm unable to answer right now."


# ---------------- CHATBOT RESPONSE ---------------- #

def get_response(query, chat_history):

    # Search FAISS
    search_results = vectorstore.similarity_search(
        query,
        k=4
    )

    # Combine context
    context = "\n\n".join([
        result.page_content
        for result in search_results
    ])

    # Previous chat
    history_text = "\n".join([
        msg.content
        for msg in chat_history
    ])

    # Prompt
    prompt = f"""
Answer the question using the given context.

Context:
{context}

Chat History:
{history_text}

Question:
{query}

Answer:
"""

    # Generate answer
    answer = llm(prompt)

    # Update memory
    chat_history.extend([
        HumanMessage(content=query),
        AIMessage(content=answer)
    ])

    return answer


# ---------------- CHAT API ---------------- #

@app.route("/api/chat", methods=["POST"])
def chat():

    try:
        data = request.json

        query = data.get("query")
        user_id = data.get("userId", "guest")

        if not query:
            return jsonify({
                "error": "Query is required"
            }), 400

        # Load previous chat history
        history_records = list(
            chat_history_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", 1)
        )

        chat_history = []

        for record in history_records:

            chat_history.append(
                HumanMessage(content=record["query"])
            )

            chat_history.append(
                AIMessage(content=record["response"])
            )

        # Get chatbot response
        response = get_response(query, chat_history)

        # Save to MongoDB
        chat_history_collection.insert_one({
            "user_id": user_id,
            "query": query,
            "response": response,
            "timestamp": datetime.now()
        })

        return jsonify({
            "response": response
        })

    except Exception as e:

        print("[ERROR] Chat Error:", str(e))

        return jsonify({
            "error": str(e)
        }), 500


# ---------------- GET CHAT HISTORY ---------------- #

@app.route("/api/chat/history/<user_id>", methods=["GET"])
def get_chat_history(user_id):

    try:

        history = list(
            chat_history_collection.find(
                {"user_id": user_id}
            ).sort("timestamp", -1)
        )

        formatted_history = []

        for item in history:

            formatted_history.append({
                "_id": str(item["_id"]),
                "query": item["query"],
                "response": item["response"],
                "timestamp": item["timestamp"].isoformat()
            })

        return jsonify(formatted_history)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ---------------- CLEAR CHAT HISTORY ---------------- #

@app.route("/api/chat/history/<user_id>", methods=["DELETE"])
def clear_chat_history(user_id):

    try:

        result = chat_history_collection.delete_many({
            "user_id": user_id
        })

        return jsonify({
            "message": "Chat history cleared",
            "deleted_count": result.deleted_count
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return "🚀 AI Chatbot Backend Running"


# ---------------- RUN APP ---------------- #

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )