import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
 
load_dotenv()
 
from db import supabase
from agent import run_agent
 
app = FastAPI(title="Admissions Assistant API")
 
origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
class ChatRequest(BaseModel):
    session_id: str
    message: str
 
 
@app.get("/health")
def health():
    return {"status": "ok"}
 
 
@app.post("/chat")
def chat(req: ChatRequest):
    rows = (
        supabase.table("chat_history")
        .select("role,content")
        .eq("session_id", req.session_id)
        .order("id", desc=True)
        .limit(6)
        .execute()
        .data
    )
    history = list(reversed(rows))
 
    try:
        answer, sources, steps = run_agent(req.message, history)
    except Exception as e:
        print("Agent error:", e)
        raise HTTPException(status_code=500, detail="AI service error")
 
    supabase.table("chat_history").insert(
        [
            {"session_id": req.session_id, "role": "user",
             "content": req.message},
            {"session_id": req.session_id, "role": "assistant",
             "content": answer},
        ]
    ).execute()
 
    return {"answer": answer, "sources": sources, "steps": steps}
