from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.database import SessionLocal
import backend.models as models
from jinja2 import Environment, FileSystemLoader
from fastapi import APIRouter, UploadFile, File, Request
import pandas as pd
import mysql.connector
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
import pdfkit
from backend.database import get_db, get_db_connection
from backend import models
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Utility: DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    return pwd_context.hash(password)

# ------------------------
# Login Pages
# ------------------------
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# ------------------------
# Student Login
# ------------------------
from collections import defaultdict

from collections import defaultdict
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

@router.post("/login/student", response_class=HTMLResponse)
def login_student(
    request: Request,
    app_id: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    student = db.query(models.Student).filter_by(app_id=app_id, name=name).first()
    if not student:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })

    # Marks fetching and credit score logic
    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    monthly_data = {}
    for mark in marks:
        month = mark.month
        if month not in monthly_data:
            monthly_data[month] = {'subjects': [], 'total_credit': 0, 'subject_count': 0}
        credit = round((mark.obtained / mark.total) * 10, 2)
        monthly_data[month]['subjects'].append({
            'subject': mark.subject,
            'obtained': mark.obtained,
            'total': mark.total,
            'credit': credit
        })
        monthly_data[month]['total_credit'] += credit
        monthly_data[month]['subject_count'] += 1

    for month, data in monthly_data.items():
        data['average_credit'] = round(data['total_credit'] / data['subject_count'], 2)

    # Attendance summary calculation
    attendance = db.query(models.Attendance).filter_by(app_id=app_id).all()
    attendance_summary = defaultdict(lambda: {'present': 0, 'absent': 0})
    for record in attendance:
        if record.date:
            month = record.date.strftime("%B")
            status = record.status.lower()
            if status == "present":
                attendance_summary[month]['present'] += 1
            elif status == "absent":
                attendance_summary[month]['absent'] += 1

    attendance_percentages = {}
    for month, counts in attendance_summary.items():
        total = counts['present'] + counts['absent']
        percent = round((counts['present'] / total) * 100, 2) if total > 0 else 0
        attendance_percentages[month] = percent

    # Pass data to dashboard
    return templates.TemplateResponse("student_dashboard.html", {
        "request": request,
        "student": student,
        "monthly_data": monthly_data,
        "attendance": attendance,
        "attendance_percentages": attendance_percentages,
        "student_attendance": [
            {"month": month, "attendance_percent": percent}
            for month, percent in attendance_percentages.items()
        ]
    })


# ------------------------
# Admin Login
# ------------------------
@router.post("/login/admin", response_class=HTMLResponse)
def login_admin(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter_by(username=username).first()
    if admin and verify_password(password, admin.password):
        mentors = db.query(models.Mentor).all()
        students = db.query(models.Student).all()
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "admin": admin,
            "mentors": mentors,
            "students": students
        })
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.post("/admin/add_mentor")
def add_mentor(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    hashed_pwd = hash_password(password)
    new_mentor = models.Mentor(email=email, password=hashed_pwd)
    db.add(new_mentor)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    mentors = db.query(models.Mentor).all()
    students = db.query(models.Student).all()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "mentors": mentors,
        "students": students
    })

# ------------------------
# Mentor Login
# ------------------------
@router.post("/login/mentor", response_class=HTMLResponse)
def login_mentor(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    mentor = db.query(models.Mentor).filter_by(email=email).first()
    if mentor and verify_password(password, mentor.password):
        request.session['mentor_email'] = mentor.email  # ✅ Store in session
        students = db.query(models.Student).all()
        data = []
        for student in students:
            marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()
            total_obtained = sum([m.obtained for m in marks])
            total_possible = sum([m.total for m in marks])
            credit_score = round((total_obtained / total_possible) * 10, 2) if total_possible else 0
            data.append({
                "app_id": student.app_id,
                "name": student.name,
                "credit": credit_score
            })
        return templates.TemplateResponse("mentor_dashboard.html", {
            "request": request,
            "mentor": mentor,
            "students": data
        })
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/mentor/dashboard", response_class=HTMLResponse)
def mentor_dashboard(request: Request, db: Session = Depends(get_db)):
    mentor_email = request.session.get('mentor_email')  # ✅ Retrieve from session
    if not mentor_email:
        return RedirectResponse(url="/login", status_code=302)

    mentor = db.query(models.Mentor).filter_by(email=mentor_email).first()
    students = db.query(models.Student).all()
    data = []
    for student in students:
        marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()
        attendance = db.query(models.Attendance).filter_by(app_id=student.app_id).all()
        total_obtained = sum([m.obtained for m in marks])
        total_possible = sum([m.total for m in marks])
        credit_score = round((total_obtained / total_possible) * 10, 2) if total_possible else 0
        data.append({
            "app_id": student.app_id,
            "name": student.name,
            "marks": marks,
            "attendance": attendance,
            "credit": credit_score
        })
    return templates.TemplateResponse("mentor_dashboard.html", {
        "request": request,
        "mentor": mentor,
        "students": data
    })


# ------------------------
# API for Charts
# ------------------------
@router.get("/student/data")
def get_student_data(app_id: str, db: Session = Depends(get_db)):
    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    marks_data = [{"month": m.month, "obtained": m.obtained} for m in marks]
    credit_data = [{"month": m.month, "score": min(10, m.obtained / m.total * 10)} for m in marks]
    attendance = db.query(models.Attendance).filter_by(app_id=app_id).all()
    present = sum(1 for a in attendance if a.status.lower() == "present")
    absent = sum(1 for a in attendance if a.status.lower() == "absent")
    return {
        "marks": marks_data,
        "credits": credit_data,
        "attendance": {"present": present, "absent": absent}
    }

# ------------------------
# PDF Report
# ------------------------
@router.get("/student/report/pdf")
def generate_pdf_report(app_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    attendance = db.query(models.Attendance).filter_by(app_id=app_id).all()
    env = Environment(loader=FileSystemLoader("frontend/templates"))
    template = env.get_template("report.html")
    html_content = template.render(student=student, marks=marks, attendance=attendance)
    pdfkit.from_string(html_content, "student_report.pdf")
    return FileResponse("student_report.pdf", filename="student_report.pdf", media_type="application/pdf")


@router.get("/mentor/view_report/{app_id}", response_class=HTMLResponse)
def mentor_view_report(request: Request, app_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    attendance = db.query(models.Attendance).filter_by(app_id=app_id).all()

    if not student:
        return templates.TemplateResponse("mentor_dashboard.html", {
            "request": request,
            "error": "Student not found."
        })

    monthly_data = {}
    for mark in marks:
        if mark.month not in monthly_data:
            monthly_data[mark.month] = {'subjects': [], 'total_credit': 0, 'subject_count': 0}
        credit = round((mark.obtained / mark.total) * 10, 2)
        monthly_data[mark.month]['subjects'].append({
            'subject': mark.subject,
            'obtained': mark.obtained,
            'total': mark.total,
            'credit': credit
        })
        monthly_data[mark.month]['total_credit'] += credit
        monthly_data[mark.month]['subject_count'] += 1

    for month, data in monthly_data.items():
        data['average_credit'] = round(data['total_credit'] / data['subject_count'], 2)

    return templates.TemplateResponse("mentor_student_report.html", {
        "request": request,
        "student": student,
        "monthly_data": monthly_data,
        "attendance": attendance
    })

from fastapi import HTTPException

@router.get("/mentor/marks/{app_id}", response_class=HTMLResponse)
def get_student_marks(request: Request, app_id: str, db: Session = Depends(get_db)):
    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse(url="/login", status_code=302)

    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    
    # ✅ Extract unique months for dropdown
    months = sorted(set(mark.month for mark in marks))

    return templates.TemplateResponse("mentor_edit_marks.html", {
        "request": request,
        "student": student,
        "marks": marks,
        "months": months   # ✅ Send this to template
    })
    

    

@router.post("/mentor/marks/update", response_class=HTMLResponse)
def update_student_marks(
    request: Request,
    app_id: str = Form(...),
    subjects: list[str] = Form(...),
    obtained: list[int] = Form(...),
    total: list[int] = Form(...),
    months: list[str] = Form(...),
    db: Session = Depends(get_db)
):
    db.query(models.Marks).filter_by(app_id=app_id).delete()
    db.commit()

    for i in range(len(subjects)):
        new_mark = models.Marks(
            app_id=app_id,
            subject=subjects[i],
            obtained=obtained[i],
            total=total[i],
            month=months[i]
        )
        db.add(new_mark)
    db.commit()
    return RedirectResponse(url="/mentor/dashboard", status_code=302)


# Student Update Dashboard (GET)
@router.get("/mentor/student_update", response_class=HTMLResponse)
def mentor_student_update(request: Request, db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    return templates.TemplateResponse("mentor_student_update.html", {"request": request, "students": students})

# Add New Student (POST)
@router.post("/mentor/add_student")
def mentor_add_student(app_id: str = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    new_student = models.Student(app_id=app_id, name=name)
    db.add(new_student)
    db.commit()
    return RedirectResponse(url="/mentor/student_update", status_code=303)

# Delete Student (POST)
@router.post("/mentor/delete_student")
def mentor_delete_student(app_id: str = Form(...), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if student:
        db.delete(student)
        db.commit()
    return RedirectResponse(url="/mentor/student_update", status_code=303)

# Page to Add Marks for Student
@router.get("/mentor/add_marks/{app_id}", response_class=HTMLResponse)
def mentor_add_marks_page(request: Request, app_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    return templates.TemplateResponse("add_marks.html", {"request": request, "student": student})

# Handle Add Marks POST
@router.post("/mentor/add_marks")
def mentor_add_marks(app_id: str = Form(...), subject: str = Form(...), month: str = Form(...), obtained: int = Form(...), total: int = Form(...), db: Session = Depends(get_db)):
    new_mark = models.Marks(app_id=app_id, subject=subject, month=month, obtained=obtained, total=total)
    db.add(new_mark)
    db.commit()
    return RedirectResponse(url=f"/mentor/add_marks/{app_id}", status_code=303)


import os
from dotenv import load_dotenv
load_dotenv()

import pymysql

# .env फाइल लोड करा
load_dotenv("C:/Users/dinesh jadhav/Desktop/student_credit_system/backend/.env")

# Environment Variables मिळवा
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),
        cursorclass=pymysql.cursors.DictCursor
    )
from fastapi import UploadFile, File, Request
import pandas as pd
import io

import io
import pandas as pd

import pymysql
import os

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),
        cursorclass=pymysql.cursors.DictCursor
    )

@router.post("/upload_marks_excel")
async def upload_marks_excel(
    request: Request,
    marks_file: UploadFile = File(...),
    selected_month: str = Form(...),
    selected_year: int = Form(...)
):
    import io
    import pandas as pd
    from backend.database import get_db_connection
    from fastapi.responses import HTMLResponse, RedirectResponse

    contents = await marks_file.read()

    try:
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        return HTMLResponse(content=f"Failed to read Excel file: {e}", status_code=400)

    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ Get valid app_ids from students table
    cursor.execute("SELECT app_id FROM students")
    valid_app_ids = set(row['app_id'] for row in cursor.fetchall())

    for index, row in df.iterrows():
        # ✅ Check for valid roll_no / app_id
        if 'app_id' not in row or pd.isna(row['app_id']):
            print(f"Skipping row {index+1}: missing app_id")
            continue

        app_id = str(row['app_id']).strip().upper()

        if app_id not in valid_app_ids:
            print(f"Skipping row {index+1}: invalid app_id '{app_id}'")
            continue

        for column in df.columns:
            if column.lower() not in ["app_id", "name", "total"]:
                subject = column.strip()
                cell_value = row[column]

                # ✅ Skip if subject is "-"
                if isinstance(cell_value, str) and cell_value.strip() == "-":
                    print(f"Skipping subject {subject} for {app_id} — not applicable")
                    continue

                try:
                    if isinstance(cell_value, str) and "/" in cell_value:
                        obtained_str, total_str = cell_value.split("/")
                        obtained = int(obtained_str.strip())
                        total = int(total_str.strip())
                    elif isinstance(cell_value, (int, float)):
                        obtained = int(cell_value)
                        total = 100
                    else:
                        print(f"Skipping subject {subject} for {app_id}: invalid format")
                        continue
                except:
                    print(f"Error parsing mark at row {index+1}, subject {subject}, value: {cell_value}")
                    continue

                try:
                    cursor.execute("""
                        INSERT INTO marks (app_id, subject, obtained, total, month)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        app_id,
                        subject,
                        obtained,
                        total,
                        selected_month
                    ))
                    print(f"Inserted: {app_id} - {subject} - {obtained}/{total}")
                except Exception as e:
                    print(f"DB insert failed at row {index+1}, subject {subject}: {e}")
                    continue

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url="/mentor/dashboard", status_code=302)







from collections import defaultdict
from sqlalchemy import extract

@router.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard(request: Request, db: Session = Depends(get_db)):
    app_id = request.session.get("app_id")
    if not app_id:
        return RedirectResponse(url="/", status_code=303)

    student = db.query(models.Student).filter_by(app_id=app_id).first()
    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    attendance = db.query(models.Attendance).filter_by(app_id=app_id).all()

    # Attendance Percentage Calculation per Month
    attendance_summary = defaultdict(lambda: {'present': 0, 'absent': 0})

    for record in attendance:
        month = record.date.strftime("%B")  # e.g., June
        if record.status.lower() == "present":
            attendance_summary[month]['present'] += 1
        elif record.status.lower() == "absent":
            attendance_summary[month]['absent'] += 1

    attendance_percentages = {}
    for month, counts in attendance_summary.items():
        total = counts['present'] + counts['absent']
        percent = round((counts['present'] / total) * 100, 2) if total > 0 else 0
        attendance_percentages[month] = percent

    return templates.TemplateResponse("student_dashboard.html", {
        "request": request,
        "student": student,
        "marks": marks,
        "attendance_percentages": attendance_percentages,
    })

@router.post("/upload_marks_excel")
async def upload_marks_excel(request: Request, month: str = Form(...), marks_file: UploadFile = File(...)):
    import io
    import pandas as pd
    from backend.database import get_db_connection

    contents = await marks_file.read()
    df = pd.read_excel(io.BytesIO(contents))  # Read Excel file
    
    df.rename(columns={"roll_no": "app_id"}, inplace=True)


    conn = get_db_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        app_id = str(row['app_id'])

        for subject in df.columns[1:]:  # Skip first column (app_id)
            raw_marks = row[subject]
            if pd.notna(raw_marks) and isinstance(raw_marks, str) and '/' in raw_marks:
                try:
                    obtained_str, total_str = raw_marks.split('/')
                    obtained = int(obtained_str.strip())
                    total = int(total_str.strip())

                    cursor.execute("""
                        INSERT INTO marks (app_id, subject, obtained, total, month)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (app_id, subject, obtained, total, month))
                except ValueError:
                    print(f"❌ Invalid marks format for {app_id} - {subject}: {raw_marks}")
                    continue

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url="/mentor/dashboard", status_code=302)


@router.get("/mentor/students/all", response_class=HTMLResponse)
def view_all_students(request: Request, db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    student_list = []

    for student in students:
        marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()
        total_obtained = sum([m.obtained for m in marks])
        total_possible = sum([m.total for m in marks])
        credit = round((total_obtained / total_possible) * 10, 2) if total_possible else 0
        student_list.append({
            "app_id": student.app_id,
            "name": student.name,
            "credit": credit
        })

    return templates.TemplateResponse("mentor_all_students.html", {
        "request": request,
        "students": student_list
    })



@router.get("/mentor/students/top", response_class=HTMLResponse)
def view_top_students(request: Request, db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    student_data = []
    for student in students:
        marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()
        total_obtained = sum(m.obtained for m in marks)
        total_possible = sum(m.total for m in marks)
        credit = round((total_obtained / total_possible) * 10, 2) if total_possible else 0
        student_data.append({
            "app_id": student.app_id,
            "name": student.name,
            "credit": credit
        })

    # Sort and pick top 5
    sorted_students = sorted(student_data, key=lambda x: x["credit"], reverse=True)[:5]

    return templates.TemplateResponse("mentor_top_students.html", {
        "request": request,
        "students": sorted_students
    })



@router.get("/mentor/students/low", response_class=HTMLResponse)
def view_low_students(request: Request, db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    result = []

    for student in students:
        marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()

        monthly_credits = {}
        for mark in marks:
            if mark.total and mark.obtained:
                month = mark.month
                credit = round((mark.obtained / mark.total) * 10, 2)
                if month not in monthly_credits:
                    monthly_credits[month] = []
                monthly_credits[month].append(credit)

        # प्रत्येक महिन्याचा average credit काढा
        month_avg_credits = []
        for credits in monthly_credits.values():
            avg = round(sum(credits) / len(credits), 2)
            month_avg_credits.append(avg)

        # अंतिम credit = सर्व महिन्यांच्या credit चं सरासरी
        final_credit = round(sum(month_avg_credits) / len(month_avg_credits), 2) if month_avg_credits else 0

        result.append({"student": student, "credit": final_credit})
        print(f"{student.app_id} → Monthly Credits: {month_avg_credits}, Final Credit: {final_credit}")

    low_students = [r for r in result if r["credit"] < 7.0]

    return templates.TemplateResponse("mentor_low_students.html", {"request": request, "students": low_students})




@router.post("/upload_attendance_excel")
async def upload_attendance_excel(
    request: Request,
    attendance_file: UploadFile = File(...),
    selected_month: str = Form(...),
    selected_year: int = Form(...)
):
    try:
        contents = await attendance_file.read()
        df = pd.read_excel(io.BytesIO(contents))

        db = get_db_connection()
        cursor = db.cursor()

        for index, row in df.iterrows():
            app_id = row['roll_no']
            for col in df.columns[2:]:
                status = row[col]
                if status in ['Present', 'Absent']:
                    try:
                        day = int(col)
                        date_str = f"{selected_year}-{datetime.strptime(selected_month, '%B').month:02d}-{day:02d}"
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                        # ⛔ Skip Sundays
                        if date_obj.weekday() == 6:
                            continue
                    except:
                        continue
                    
                    cursor.execute("""
                        INSERT INTO attendance (app_id, status, date, month)
                        VALUES (%s, %s, %s, %s)
                    """, (app_id, status, date_obj, selected_month))

        db.commit()
        cursor.close()
        db.close()

        return RedirectResponse(url="/mentor/dashboard", status_code=303)
    
    except Exception as e:
        return HTMLResponse(content=f"<h3>Attendance upload failed: {str(e)}</h3>")
    









@router.get("/mentor/dashboard", response_class=HTMLResponse)
def mentor_dashboard(request: Request, db: Session = Depends(get_db)):
    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse(url="/login", status_code=302)

    mentor = db.query(models.Mentor).filter_by(email=mentor_email).first()
    students = db.query(models.Student).all()

    data = []
    for student in students:
        marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()
        total_obtained = sum([m.obtained for m in marks])
        total_possible = sum([m.total for m in marks])
        credit_score = round((total_obtained / total_possible) * 10, 2) if total_possible else 0
        data.append({
            "app_id": student.app_id,
            "name": student.name,
            "credit": credit_score
        })

    # ✅ Month list
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

    return templates.TemplateResponse("mentor_dashboard.html", {
        "request": request,
        "mentor": mentor,
        "students": data,
        "months": months  # ✅ THIS IS REQUIRED
    })








def get_grade(credit: float) -> str:
    if credit >= 9.0:
        return "A+"
    elif credit >= 8.0:
        return "A"
    elif credit >= 7.0:
        return "B+"
    elif credit >= 6.0:
        return "B"
    elif credit >= 5.0:
        return "C+"
    elif credit >= 4.0:
        return "C"
    else:
        return "D"

@router.get("/student/credit_summary/monthwise/{app_id}")
def get_monthwise_credit_summary(app_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    if not marks:
        raise HTTPException(status_code=404, detail="No marks found for this student")

    monthly_data = {}

    for mark in marks:
        month = mark.month
        if not month:
            continue

        if month not in monthly_data:
            monthly_data[month] = {
                "subjects": [],
                "total_credit": 0,
                "count": 0
            }

        # Calculate credit and grade
        credit = round((mark.obtained / mark.total) * 10, 2) if mark.total > 0 else 0
        grade = get_grade(credit)

        monthly_data[month]["subjects"].append({
            "subject": mark.subject,
            "credit": credit,
            "grade": grade
        })
        monthly_data[month]["total_credit"] += credit
        monthly_data[month]["count"] += 1

    # Calculate average credit per month
    for month in monthly_data:
        count = monthly_data[month]["count"]
        avg_credit = round(monthly_data[month]["total_credit"] / count, 2) if count > 0 else 0
        monthly_data[month]["average_credit"] = avg_credit
        # Clean up intermediate fields
        del monthly_data[month]["total_credit"]
        del monthly_data[month]["count"]

    return {
        "app_id": student.app_id,
        "name": student.name,
        "education": "FYBSc CS",  # Optional: Replace or fetch dynamically
        "monthwise_credits": monthly_data
    }

# 2. Yearwise Credit Summary Route
@router.get("/student/credit_summary/yearwise/{app_id}/{year}")
def get_yearwise_credit_summary(app_id: str, year: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = db.query(models.Marks).filter(
        models.Marks.app_id == app_id,
        models.Marks.month.contains(year)
    ).all()

    credit_list = []
    total_credit = 0
    subject_count = 0

    for mark in marks:
        credit = round((mark.obtained / mark.total) * 10, 2)
        credit_list.append({
            "subject": mark.subject,
            "credit": credit,
            "month": mark.month
        })
        total_credit += credit
        subject_count += 1

    average_credit = round(total_credit / subject_count, 2) if subject_count > 0 else 0

    return {
        "app_id": student.app_id,
        "name": student.name,
        "year": year,
        "credits": credit_list,
        "total_credit": average_credit
    }

# 3. Student Credit Summary (All Subjects Combined)
@router.get("/student/credit_summary/{app_id}")
def get_credit_summary(app_id: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = db.query(models.Marks).filter_by(app_id=app_id).all()
    credit_list = []
    total_credit = 0
    subject_count = 0

    for mark in marks:
        if mark.total and mark.total > 0:
            credit = round((mark.obtained / mark.total) * 10, 2)
            credit_list.append({
                "subject": mark.subject,
                "credit": credit
            })
            total_credit += credit
            subject_count += 1

    average_credit = round(total_credit / subject_count, 2) if subject_count > 0 else 0

    return {
        "app_id": student.app_id,
        "name": student.name,
        "credits": credit_list,
        "total_credit": average_credit
    }



from collections import defaultdict

def calculate_grade(credit):
    if credit >= 9:
        return "A+"
    elif credit >= 8:
        return "A"
    elif credit >= 7:
        return "B+"
    elif credit >= 6:
        return "B"
    elif credit >= 5:
        return "C+"
    elif credit >= 4:
        return "C"
    else:
        return "D"

@router.get("/student/pdf_report/month/{app_id}/{month}")
def generate_monthwise_pdf(app_id: str, month: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = db.query(models.Marks).filter(
        models.Marks.app_id == app_id,
        models.Marks.month.ilike(f"%{month.split()[0]}%")
    ).all()

    if not marks:
        raise HTTPException(status_code=404, detail="No marks found for the selected month.")

    credit_list = []
    total_credit = 0

    for mark in marks:
        if mark.obtained is not None and mark.total > 0:
            credit = round((mark.obtained / mark.total) * 10, 2)
            grade = calculate_grade(credit)
            credit_list.append({
                "subject": mark.subject,
                "credit": credit,
                "grade": grade
            })
            total_credit += credit

    total_subjects = len(credit_list)
    average_credit = round(total_credit / total_subjects, 2) if total_subjects else 0

    date_today = datetime.now().strftime("%d/%m/%Y")

    # Render HTML using Jinja2
    env = Environment(
        loader=FileSystemLoader("frontend/templates"),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template("performance_template.html")
    html_content = template.render(
        student_name=student.name,
        role=f"Month: {month}",
        education="FYBSc CS",  # Or dynamic if needed
        date=date_today,
        subjects=credit_list,
        total=average_credit
    )

    # Generate PDF
    output_dir = "generated_reports"
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = f"{output_dir}/{app_id}_{month}_report.pdf"

    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdfkit.from_string(html_content, pdf_path, configuration=config)

    return FileResponse(pdf_path, media_type='application/pdf', filename=f"{student.name}_{month}_Report.pdf")


@router.get("/student/pdf_report/year/{app_id}/{year}")
def generate_yearwise_pdf(app_id: str, year: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = db.query(models.Marks).filter(
        models.Marks.app_id == app_id,
        models.Marks.month.contains(year)
    ).all()

    subject_credit_map = defaultdict(list)

    for mark in marks:
        if mark.total and mark.total > 0:
            credit = round((mark.obtained / mark.total) * 10, 2)
            subject_credit_map[mark.subject].append(credit)

    def calculate_grade(credit):
        if credit >= 9:
            return "A+"
        elif credit >= 8:
            return "A"
        elif credit >= 7:
            return "B+"
        elif credit >= 6:
            return "B"
        else:
            return "C"

    credit_list = []
    total_credit = 0
    for subject, credits in subject_credit_map.items():
        avg_credit = round(sum(credits) / len(credits), 2)
        grade = calculate_grade(avg_credit)
        credit_list.append({
            "subject": subject,
            "credit": avg_credit,
            "grade": grade
        })
        total_credit += avg_credit

    total_display = round(total_credit, 1)
    date_today = datetime.now().strftime("%d/%m/%Y")

    env = Environment(
        loader=FileSystemLoader("frontend/templates"),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template("performance_template.html")
    html_content = template.render(
        student_name=student.name,
        role=f"Year: {year}",
        education="FYBSc CS",
        date=date_today,
        subjects=credit_list,
        total=total_display
    )

    pdf_path = f"generated_reports/{app_id}_{year}_report.pdf"
    os.makedirs("generated_reports", exist_ok=True)

    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    pdfkit.from_string(html_content, pdf_path, configuration=config)

    return FileResponse(pdf_path, media_type='application/pdf', filename=f"{student.name}_{year}_Report.pdf")

@router.get("/reports/{filename}")
def serve_pdf(filename: str):
    file_path = os.path.join("generated_reports", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/pdf', filename=filename)
    return {"error": "File not found"}


from fastapi import Form, Request, Depends, HTTPException
import urllib.parse
import requests
from fastapi.responses import RedirectResponse
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_email_with_attachment(to_email, subject, body, file_path):
    from_email = "dj514726@gmail.com"  # 🔁 Replace with your Gmail
    from_password = "ikmy xzph mcri nxvm"  # 🔁 Use App Password (not real password)

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with open(file_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
        part['Content-Disposition'] = f'attachment; filename=\"{os.path.basename(file_path)}\"'
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, from_password)
        server.send_message(msg)

@router.post("/mentor/send_to_parent")
def send_to_parent_from_modal(app_id: str = Form(...), month: str = Form(...), year: str = Form(...), db: Session = Depends(get_db)):
    full_month = f"{month} {year}"
    encoded_month = urllib.parse.quote(full_month)

    # Generate PDF
    pdf_url = f"http://127.0.0.1:8000/student/pdf_report/month/{app_id}/{encoded_month}"
    response = requests.get(pdf_url)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Could not generate report")

    file_path = f"generated_reports/{app_id}_{month}_{year}_report.pdf"
    with open(file_path, "wb") as f:
        f.write(response.content)

    student = db.query(models.Student).filter_by(app_id=app_id).first()
    if not student or not student.parents_gmail:
        raise HTTPException(status_code=404, detail="Parent email not found")

    subject = f"{student.name} - Monthly Report ({month} {year})"
    body = f"Dear Parent,\n\nAttached is the performance report for {month} {year}.\n\nRegards,\nMentor Team"

    send_email_with_attachment(student.parents_gmail, subject, body, file_path)

    return RedirectResponse(url="/mentor/dashboard", status_code=302)
    return {"message": "Email sent to parent successfully"}

@router.post("/mentor/send_bulk_reports")
def send_bulk_reports(month: str = Form(...), year: str = Form(...), db: Session = Depends(get_db)):
    from .models import Student  # adjust as per your structure
    import urllib.parse

    full_month = f"{month} {year}"
    encoded_month = urllib.parse.quote(full_month)

    students = db.query(Student).all()

    for student in students:
        if not student.parents_gmail:
            continue  # skip if email not available

        pdf_url = f"http://127.0.0.1:8000/student/pdf_report/month/{student.app_id}/{encoded_month}"
        response = requests.get(pdf_url)

        if response.status_code == 200:
            file_path = f"generated_reports/{student.app_id}_{month}_{year}_report.pdf"
            with open(file_path, "wb") as f:
                f.write(response.content)

            subject = f"{student.name} - Monthly Report ({month} {year})"
            body = f"Dear Parent,\n\nAttached is the performance report for {month} {year}.\n\nRegards,\nMentor Team"

            send_email_with_attachment(student.parents_gmail, subject, body, file_path)

    return RedirectResponse(url="/mentor/dashboard", status_code=302)


    return RedirectResponse(url="/mentor/dashboard", status_code=302)

# ------------------------
# Admin Routes
# ------------------------
@router.post("/admin/delete_mentor/{mentor_id}")
def admin_delete_mentor(mentor_id: int, db: Session = Depends(get_db)):
    mentor = db.query(models.Mentor).filter_by(id=mentor_id).first()
    if mentor:
        db.delete(mentor)
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=303)

from fastapi.responses import JSONResponse

@router.get("/admin/student_result/{student_id}")
def admin_student_result(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter_by(id=student_id).first()
    if not student:
        return JSONResponse(content={"result": "Student not found."}, status_code=404)
    # Example: fetch marks and attendance summary
    marks = db.query(models.Marks).filter_by(app_id=student.app_id).all()
    attendance = db.query(models.Attendance).filter_by(app_id=student.app_id).all()
    result = f"Name: {student.name}\nApplication ID: {student.app_id}\n"
    if marks:
        result += "\nMarks:\n"
        for m in marks:
            result += f"{m.subject} ({m.month}): {m.obtained}/{m.total}\n"
    if attendance:
        present = sum(1 for a in attendance if a.status.lower() == 'present')
        absent = sum(1 for a in attendance if a.status.lower() == 'absent')
        result += f"\nAttendance: Present {present}, Absent {absent}\n"
    return JSONResponse(content={"result": result})










































