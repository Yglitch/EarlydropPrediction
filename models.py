from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, TIMESTAMP, Text
from db import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    income_level = Column(String)
    parent_education = Column(String)


class AcademicRecord(Base):
    __tablename__ = "academic_records"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    attendance = Column(Float)
    marks = Column(Float)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    risk_score = Column(Float)
    risk_level = Column(String)
    reason = Column(Text)

class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    action_suggested = Column(Text)
    action_taken = Column(Text, nullable=True)
    status = Column(String)