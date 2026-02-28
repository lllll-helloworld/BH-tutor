# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn
import os
from typing import Optional
from pydantic import BaseModel

from llm_service import AnswerPayload, fetch_new_question, evaluate_student_answer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthPayload(BaseModel):
    username: str
    password: str

# ================= Web Page Routes =================

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    """Serve student main page"""
    html_path = os.path.join(os.path.dirname(__file__), "new.html")
    if not os.path.exists(html_path):
         return "❌ Cannot find new.html file, make sure it is in the same directory as main.py."
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/teacher", response_class=HTMLResponse)
def serve_teacher_frontend():
    """Serve teacher monitoring dashboard"""
    html_path = os.path.join(os.path.dirname(__file__), "teacher.html")
    if not os.path.exists(html_path):
         return "❌ Cannot find teacher.html file, make sure it is in the same directory as main.py."
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# ================= Existing API Routes =================

@app.post("/api/register")
def register(payload: AuthPayload):
    from database import create_user
    success, msg = create_user(payload.username, payload.password)
    if success:
        return {"status": "success", "message": msg}
    return {"status": "error", "message": msg}

@app.post("/api/login")
def login(payload: AuthPayload):
    from database import verify_user_login, get_user_info, get_average_score
    user_id = verify_user_login(payload.username, payload.password)
    if user_id:
        user_info = get_user_info(user_id)
        avg_score = get_average_score(user_id)
        return {
            "status": "success", 
            "data": {
                "user_id": user_id, 
                "username": user_info["username"], 
                "score": avg_score
            }
        }
    return {"status": "error", "message": "Incorrect username or password"}

# ✨ New: Get knowledge points for custom subject
@app.get("/api/topics")
def get_topics(subject: str):
    """
    Receive subject name from frontend, call LLM to automatically generate 5 core knowledge points
    """
    from llm_service import global_system
    try:
        topics = global_system.generate_topics_for_subject(subject)
        if topics and len(topics) > 0:
            return {"status": "success", "data": topics}
        else:
            return {"status": "error", "message": "Failed to generate knowledge points, please retry"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/question")
def get_question(user_id: int, subject: str = "Python Programming", topic: Optional[str] = None, initial_score: Optional[int] = None):
    result = fetch_new_question(user_id, subject, topic, initial_score)
    return result

@app.post("/api/submit")
def receive_answer(payload: AnswerPayload):
    result = evaluate_student_answer(payload)
    return result

@app.get("/api/stats")
def get_stats(user_id: int):
    from database import get_user_info, get_wrong_questions_details, get_all_topic_scores, get_average_score
    info = get_user_info(user_id)
    if not info:
         return {"status": "error", "message": "User not found"}
         
    wrong_q = get_wrong_questions_details(user_id)
    topic_scores = get_all_topic_scores(user_id)
    avg_score = get_average_score(user_id)
    
    category_counts = {}
    for w in wrong_q:
        cat = w['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
    return {
        "status": "success",
        "data": {
            "score": avg_score,
            "topic_scores": topic_scores,
            "category_counts": category_counts,
            "wrong_questions": wrong_q
        }
    }

# ================= Teacher API =================

@app.get("/api/admin/dashboard")
def get_dashboard():
    from database import get_all_users_overview
    try:
        data = get_all_users_overview()
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Use 0.0.0.0 to allow LAN access
    uvicorn.run(app, host="0.0.0.0", port=8000)