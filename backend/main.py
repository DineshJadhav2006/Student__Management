from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
# ✅ Backend imports
from backend.routes import router
from backend.database import Base, engine

# ✅ Create DB tables
Base.metadata.create_all(bind=engine)

# ✅ FastAPI app initialization
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# ✅ Include all API routes
app.include_router(router)

# ✅ Mount static folders (for CSS, JS, Images)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# ✅ Mount reports folder to serve student PDFs via URL
app.mount("/reports", StaticFiles(directory="generated_reports"), name="reports")

# ✅ Jinja2 templates setup
templates = Jinja2Templates(directory="frontend/templates")

# ✅ Route: Login Page
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return templates.TemplateResponse("index.html", {"request": request})


# @app.get("/logout")
# async def logout(request: Request):
#     request.session.clear()
#     return RedirectResponse(url="/login", status_code=302)