import io
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from celery.result import AsyncResult
from minio.error import S3Error
from config import minio_client, MINIO_BUCKET, initialize_minio_bucket
from tasks import process_image

app = FastAPI(title="Image Processing Service")

# Ensure Minio bucket is initialized when the API starts
@app.on_event("startup")
def startup_event():
    initialize_minio_bucket()

@app.get("/")
async def root():
    return {"message": "Image Processing Service is running. Use /upload to start."}

@app.post("/upload", status_code=202)
async def upload_file(file: UploadFile = File(...)):
    """
    Handles file upload, saves the original file to Minio, and queues a Celery task.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    # 1. Generate a unique ID for the file and task
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    # Object name structure: original/{file_id}/{filename}
    object_name = f"original/{file_id}/{original_filename}"

    try:
        # 2. Read file content into a buffer
        file_content = await file.read()
        file_size = len(file_content)
        file_buffer = io.BytesIO(file_content)

        # 3. Upload the original file to Minio
        minio_client.put_object(
            MINIO_BUCKET,
            object_name,
            file_buffer,
            file_size,
            content_type=file.content_type
        )

        # 4. Dispatch the background task
        task = process_image.delay(file_id, original_filename)

        # 5. Return the task ID and status URL
        return JSONResponse({
            "id": file_id,
            "task_id": task.id,
            "filename": original_filename,
            "status_url": f"/upload/{file_id}/status",
            "result_url": f"/upload/{file_id}/result",
            "message": "File uploaded successfully. Processing started in the background."
        })

    except S3Error as e:
        print(f"Minio Error: {e}")
        raise HTTPException(status_code=500, detail="Could not save file to storage.")
    except Exception as e:
        print(f"Internal Error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during upload.")

@app.get("/upload/{file_id}/status")
async def get_status(file_id: str):
    """
    Provides the current status of the background processing task.
    """
    task = AsyncResult(file_id)
    
    # Celery task states: PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    if task.state == 'PENDING':
        status_code = 200
        detail = "Processing is pending."
    elif task.state == 'PROGRESS':
        status_code = 200
        # task.info contains the progress meta-data set by the worker
        detail = task.info.get('step', 'Processing in progress.')
    elif task.state == 'SUCCESS':
        status_code = 200
        detail = "Processing complete. Use the result URL to get the processed file links."
    elif task.state == 'FAILURE':
        status_code = 500
        detail = "Processing failed."
    else:
        status_code = 200
        detail = f"Current state: {task.state}"

    return JSONResponse({
        "task_id": file_id,
        "status": task.state,
        "detail": detail,
        "result": task.info if task.state == 'PROGRESS' else None
    }, status_code=status_code)

@app.get("/upload/{file_id}/result")
async def get_result(file_id: str):
    """
    Provides the result (processed file URLs) of a completed task.
    """
    task = AsyncResult(file_id)
    
    if task.state != 'SUCCESS':
        # If the task is not successful, return a 404 to indicate the result is not ready
        raise HTTPException(status_code=404, detail=f"Task is not complete. Current status: {task.state}")

    # The result is a dictionary containing the processed URLs
    return JSONResponse(task.result)

@app.get("/files/{path:path}")
async def get_file(path: str):
    """
    Serves processed files directly from Minio.
    """
    try:
        # Get the object from Minio
        response = minio_client.get_object(MINIO_BUCKET, path)
        
        # Stream the file content back to the client
        return StreamingResponse(
            content=response.stream(32*1024), # Stream in chunks
            media_type=response.headers.get('Content-Type', 'application/octet-stream'),
            headers={
                "Content-Length": response.headers.get('Content-Length'),
                "Content-Disposition": f"attachment; filename=\"{path.split('/')[-1]}\""
            }
        )
    except S3Error as e:
        if e.code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="File not found.")
        print(f"Minio Error: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve file from storage.")
    except Exception as e:
        print(f"Internal Error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
