
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from db import supabase
from agent import run_agent


app = FastAPI(title="Creozen GenAI - Research Paper Assistant")


# Local development defaults. Configure ALLOWED_ORIGINS in production
# with the exact Vercel frontend origin.
origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        (
            "http://localhost:5173,"
            "http://127.0.0.1:5173,"
            "http://localhost:5174,"
            "http://127.0.0.1:5174"
        ),
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/")
def root():
    return {
        "message": "Welcome to Creozen GenAI - Research Paper Assistant",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Please enter a question.",
        )

    if not req.session_id.strip():
        raise HTTPException(
            status_code=400,
            detail="A session ID is required.",
        )

    # Load recent conversation history.
    try:
        result = (
            supabase.table("chat_history")
            .select("role,content")
            .eq("session_id", req.session_id)
            .order("id", desc=True)
            .limit(6)
            .execute()
        )

        rows = result.data or []
        history = list(reversed(rows))

    except Exception:
        print("Chat history retrieval failed.")
        raise HTTPException(
            status_code=500,
            detail="Could not load chat history. Please try again.",
        )

    # Generate the answer.
    try:
        answer, sources, steps = run_agent(req.message, history)

    except Exception as exc:
        print("Agent error:", exc)
        error_text = str(exc).upper()

        if "429" in error_text or "RATE LIMIT" in error_text:
            raise HTTPException(
                status_code=429,
                detail=(
                    "The AI provider's rate limit or quota was reached. "
                    "Please try again later."
                ),
            )

        if "503" in error_text or "UNAVAILABLE" in error_text:
            raise HTTPException(
                status_code=503,
                detail=(
                    "The AI provider is temporarily unavailable. "
                    "Please try again later."
                ),
            )

        raise HTTPException(
            status_code=500,
            detail="AI service error. Please try again later.",
        )

    # Save the conversation. Preserve the answer if saving fails.
    try:
        supabase.table("chat_history").insert([
            {
                "session_id": req.session_id,
                "role": "user",
                "content": req.message,
            },
            {
                "session_id": req.session_id,
                "role": "assistant",
                "content": answer,
            },
        ]).execute()

    except Exception as exc:
        print("Chat history save error:", exc)

    return {
        "answer": answer,
        "sources": sources,
        "steps": steps,
    }
