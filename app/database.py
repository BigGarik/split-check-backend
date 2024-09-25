import os

import nats
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from redis import asyncio as aioredis

load_dotenv()

redis_client = aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)

db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
# db_port = int(os.getenv('DB_PORT'))
database = os.getenv('DATABASE')

DATABASE_URL = "postgresql://{user}:{password}@{host}/{db}".format(
    user=db_user, password=db_password, host=db_host, db=database
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Функция для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
