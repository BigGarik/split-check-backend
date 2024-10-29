
from dotenv import load_dotenv
from fastapi import APIRouter


load_dotenv()

router = APIRouter(prefix="/profile", tags=["profile"])
