import json
import os
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
import shutil
import uuid

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from external_services.api_anthropic import recognize_check

app = FastAPI()

# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="static")

# app.include_router(payment_router, prefix="/payment")
# app.include_router(webhook_router, prefix="/payment")


UPLOAD_DIRECTORY = "images"


@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    uuid_dir = uuid.uuid4()
    upload_directory = os.path.join(UPLOAD_DIRECTORY, str(uuid_dir))
    if not file:
        return JSONResponse(content={"message": "No file sent"}, status_code=400)

    if not file.content_type.startswith("image/"):
        return JSONResponse(content={"message": "File is not an image"}, status_code=400)

    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)

    file_path = os.path.join(upload_directory, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    response = recognize_check(upload_directory)

    uuid_str = str(uuid_dir)

    response_data = {
        "message": f"Successfully uploaded {file.filename}",
        "uuid": uuid_str,
        "response": response
    }

    final_json_string = json.dumps(response_data, ensure_ascii=False, indent=2)

    print(final_json_string)
    return JSONResponse(content=final_json_string, status_code=200)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
