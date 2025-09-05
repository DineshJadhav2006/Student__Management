from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from starlette.middleware.sessions import SessionMiddleware
from backend.database import get_db
from backend.models import Student, Marks, Attendance

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, app_id: str = Form(...), name: str = Form(...)):
    request.session["app_id"] = app_id
    return RedirectResponse(url="/student/dashboard", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

@app.get("/mentor/student_report/{app_id}", response_class=HTMLResponse)
def mentor_view_student(app_id: str, request: Request, db: Depends(get_db)):
    student = db.query(Student).filter_by(app_id=app_id).first()
    marks = db.query(Marks).filter_by(app_id=app_id).all()
    attendance = db.query(Attendance).filter_by(app_id=app_id).all()
    return templates.TemplateResponse("student_report.html", {
        "request": request,
        "student": student,
        "marks": marks,
        "attendance": attendance
    })

if __name__ == "__main__":
    uvicorn.run("frontend.app:app", host="127.0.0.1", port=8000, reload=True)
