from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
import shutil
import os


app = FastAPI()

# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="static")

# app.include_router(payment_router, prefix="/payment")
# app.include_router(webhook_router, prefix="/payment")


UPLOAD_DIRECTORY = "images/"


@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    if not file:
        return JSONResponse(content={"message": "No file sent"}, status_code=400)

    if not file.content_type.startswith("image/"):
        return JSONResponse(content={"message": "File is not an image"}, status_code=400)

    if not os.path.exists(UPLOAD_DIRECTORY):
        os.makedirs(UPLOAD_DIRECTORY)

    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return JSONResponse(content={"message": f"Successfully uploaded {file.filename}"}, status_code=200)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
