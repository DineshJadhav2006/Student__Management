# mentor_routes.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import mysql.connector

router = APIRouter()
templates = Jinja2Templates(directory="templates")

db = mysql.connector.connect(
    host="localhost", user="root", password="", database="student_db"
)
cursor = db.cursor(dictionary=True)

@router.get("/mentor/manage_students")
def manage_students(request: Request):
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    return templates.TemplateResponse("mentor_manage_students.html", {"request": request, "students": students})

@router.post("/mentor/add_student")
def add_student(request: Request, app_id: str = Form(...), name: str = Form(...)):
    cursor.execute("INSERT INTO students (app_id, name) VALUES (%s, %s)", (app_id, name))
    db.commit()
    return RedirectResponse(url="/mentor/manage_students", status_code=303)

@router.get("/mentor/delete_student/{app_id}")
def delete_student(app_id: str):
    cursor.execute("DELETE FROM students WHERE app_id = %s", (app_id,))
    db.commit()
    return RedirectResponse(url="/mentor/manage_students", status_code=303)




























































