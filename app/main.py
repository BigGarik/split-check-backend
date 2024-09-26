import logging

from fastapi import Depends, FastAPI, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import schemas, models
from app.auth import get_current_user, authenticate_user, create_access_token
from app.crud import get_user_by_email
from app.database import engine, get_db
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.nats import connect_to_nats
from app.routers.test import router_test
from app.routers.webapp import router_webapp
from app.routers.ws import router_ws, ws_manager


logging.getLogger('passlib').setLevel(logging.ERROR)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(root_path="/split_check")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://biggarik.ru"],  # Замените на конкретные домены в продакшене
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем маршруты
# app.include_router(webhook_router, prefix="/payment")
app.include_router(router_test)
app.include_router(router_webapp)
app.include_router(router_ws)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.on_event("startup")
async def startup_event():
    await connect_to_nats()


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/test_ws")
async def test_ws_page(request: Request):
    return templates.TemplateResponse("ws.html", {"request": request})


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db=db, user=user)


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    print(user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    response = {"access_token": access_token, "token_type": "bearer"}
    return response


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
