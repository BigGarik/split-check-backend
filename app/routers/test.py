from fastapi import APIRouter

router_test = APIRouter()


@router_test.get("/test")
def read_test():
    return {"message": "Test route working!"}
