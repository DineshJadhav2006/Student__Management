from pydantic import BaseModel

class StudentLogin(BaseModel):
    app_id: str
    name: str

class MarksInput(BaseModel):
    app_id: str
    subject: str
    obtained: int
    total: int
    month: str

class AttendanceInput(BaseModel):
    app_id: str
    subject: str
    month: str
    status: str

class MentorCreate(BaseModel):
    email: str
    password: str
