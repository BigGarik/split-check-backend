from fastapi import Depends, FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app import crud, schemas, models, auth
from app.auth import verify_token
from app.database import engine, get_db
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.routers.test import router_test
from app.routers.webapp import router_webapp
from app.routers.ws import router_ws

models.Base.metadata.create_all(bind=engine)

app = FastAPI(root_path="/split_check")

# Подключаем маршруты
# app.include_router(webhook_router, prefix="/payment")
app.include_router(router_test)
app.include_router(router_webapp)
app.include_router(router_ws)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
