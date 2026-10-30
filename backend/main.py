import os
import json
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.session_manager import session_manager
from backend.ai_engine import ai_engine

app = FastAPI(
    title="Airborne Aviation AI Assistant API",
    description="24/7 DGCA Pilot Training AI Assistant with 30-minute daily cap and WhatsApp/Phone escalation",
    version="1.0.0"
)

# Enable CORS for cross-origin website embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LEADS_FILE = Path("data/leads.json")
if not LEADS_FILE.parent.exists():
    LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
if not LEADS_FILE.exists():
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

class SessionInitRequest(BaseModel):
    student_id: str

class SessionHeartbeatRequest(BaseModel):
    student_id: str
    elapsed_seconds: Optional[int] = 15

class ChatRequest(BaseModel):
    student_id: str
    message: str

class LeadRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = ""
    query: Optional[str] = ""
    student_id: Optional[str] = ""

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Airborne Aviation 24/7 AI Assistant",
        "timestamp": time.time()
    }

@app.post("/api/session/init")
def init_session(req: SessionInitRequest):
    session = session_manager.get_session(req.student_id)
    return session

@app.post("/api/session/heartbeat")
def session_heartbeat(req: SessionHeartbeatRequest):
    session = session_manager.record_activity(req.student_id, req.elapsed_seconds or 15)
    return session

@app.post("/api/session/reset")
def reset_session(req: SessionInitRequest):
    session_manager.reset_student(req.student_id)
    return session_manager.get_session(req.student_id)

@app.post("/api/chat")
def chat(req: ChatRequest):
    student_id = req.student_id.strip()
    message = req.message.strip()

    if not student_id or not message:
        raise HTTPException(status_code=400, detail="student_id and message are required")

    # Check session usage cap: 30 minutes (1800s) per student per day
    session = session_manager.get_session(student_id)
    if session["is_capped"]:
        escalation_data = ai_engine.generate_escalation_data(
            message,
            "Daily AI interaction allowance of 30 minutes reached"
        )
        return {
            "answer": (
                "⏱️ **Daily AI Limit Reached (30 Minutes)**\n\n"
                "You have utilized your 30 minutes of free AI flight counseling for today! "
                "Our 24/7 Senior Flight Training Advisors are available right now to answer any remaining questions. "
                "Please connect with us on **WhatsApp** or call our **Helpline** below for priority admission and loan support."
            ),
            "chips": ["Connect on WhatsApp", "Call Admissions Desk", "Request Call Back"],
            "escalation": escalation_data,
            "session": session,
            "is_capped": True
        }

    # Record 15 seconds interaction time per query turn
    session = session_manager.record_activity(student_id, elapsed_seconds=15)

    # Process query with Aviation AI Engine
    ai_result = ai_engine.answer_query(message)

    return {
        "answer": ai_result["answer"],
        "chips": ai_result.get("chips", []),
        "escalation": ai_result.get("escalation", {}),
        "session": session,
        "is_capped": session["is_capped"]
    }

@app.post("/api/leads")
def capture_lead(req: LeadRequest):
    lead = {
        "name": req.name,
        "phone": req.phone,
        "email": req.email,
        "query": req.query,
        "student_id": req.student_id,
        "timestamp": time.time(),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            leads = json.load(f)
        leads.append(lead)
        with open(LEADS_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "success": True,
        "message": "Senior Flight Instructor will call you within 15 minutes!",
        "lead": lead
    }

@app.get("/api/knowledge")
def get_knowledge_base():
    return ai_engine.kb

# Serve widget and static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/widget.js")
def get_widget_js():
    return FileResponse("static/widget.js", media_type="application/javascript")

@app.get("/widget.css")
def get_widget_css():
    return FileResponse("static/widget.css", media_type="text/css")

@app.get("/embed-demo")
def embed_demo():
    return FileResponse("static/embed-demo.html")

@app.get("/")
def home():
    return FileResponse("static/index.html")
