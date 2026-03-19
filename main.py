from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy.orm import Session
from pydantic import BaseModel

import numpy as np
import pickle

from models import Student, AcademicRecord, Prediction, Intervention
from db import SessionLocal

# ================= APP =================
app = FastAPI()

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= STATIC + TEMPLATES =================
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ================= DB =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= LOAD MODEL =================
try:
    with open("dropout_model.pkl", "rb") as f:
        model = pickle.load(f)
except:
    model = None

# ================= SCHEMAS =================
class StudentCreate(BaseModel):
    name: str
    age: int
    gender: str
    income: int
    

class AcademicCreate(BaseModel):
    student_id: int
    attendance: float
    marks: float

class PredictionInput(BaseModel):
    attendance: float
    marks: float
    age: int
    gender: int
    income: int

class InterventionUpdate(BaseModel):
    action_taken: str

# ================= FRONTEND ROUTES =================

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/add", response_class=HTMLResponse)
def add_page(request: Request):
    return templates.TemplateResponse("add_student.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

# ================= API ROUTES =================

@app.post("/students")
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    new_student = Student(
        name=student.name,
        age=student.age,
        gender=student.gender,
        income=student.income,
        parent_education=student.parent_education
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student

@app.post("/academic")
def add_academic(record: AcademicCreate, db: Session = Depends(get_db)):
    db.add(AcademicRecord(
        student_id=record.student_id,
        attendance=record.attendance,
        marks=record.marks
    ))
    db.commit()
    return {"message": "Academic added"}

@app.post("/predict/{student_id}")
def predict(student_id: int, data: PredictionInput, db: Session = Depends(get_db)):

    features = np.array([[data.attendance, data.marks, data.age, data.gender, data.income]])

    if model:
        risk_score = model.predict_proba(features)[0][1]
    else:
        risk_score = (
            (1 - data.attendance / 100) * 0.4 +
            (1 - data.marks / 100) * 0.4 +
            (0.2 if data.income== 0 else 0)
        )

    risk_score = round(min(max(risk_score, 0), 1), 2)

    reasons = []
    if data.attendance < 60:
        reasons.append("Low attendance")
    if data.marks < 50:
        reasons.append("Poor performance")
    if data.income== 0:
        reasons.append("Financial issue")

    actions = []
    if "Low attendance" in reasons:
        actions.append("Parent meeting")
    if "Poor performance" in reasons:
        actions.append("Assign tutor")
    if "Financial issue" in reasons:
        actions.append("Provide scholarship")

    risk_level = "High" if risk_score > 0.7 else "Medium" if risk_score > 0.4 else "Low"

    db.add(Prediction(
        student_id=student_id,
        risk_score=risk_score,
        risk_level=risk_level,
        reason=", ".join(reasons)
    ))

    for act in actions:
        db.add(Intervention(
            student_id=student_id,
            action_suggested=act,
            status="pending"
        ))

    db.commit()

    return {
        "dropout_risk": risk_score,
        "risk_level": risk_level,
        "reasons": reasons,
        "suggested_actions": actions
    }

# ================= DASHBOARD DATA =================

@app.get("/students")
def get_students(db: Session = Depends(get_db)):
    results = db.query(Student, AcademicRecord, Prediction).join(
        AcademicRecord, Student.id == AcademicRecord.student_id
    ).join(
        Prediction, Student.id == Prediction.student_id
    ).all()

    data = []
    for s, a, p in results:
        data.append({
            "id": s.id,
            "name": s.name,
            "age": s.age,
            "attendance": a.attendance,
            "marks": a.marks,
            "risk": p.risk_level
        })

    return data

@app.get("/priority-students")
def priority_students(db: Session = Depends(get_db)):
    return db.query(Prediction).order_by(
        Prediction.risk_score.desc()
    ).limit(5).all()

@app.post("/intervention/{id}")
def update_intervention(id: int, data: InterventionUpdate, db: Session = Depends(get_db)):
    intervention = db.get(Intervention, id)
    intervention.action_taken = data.action_taken
    intervention.status = "completed"
    db.commit()
    return {"message": "Updated"}