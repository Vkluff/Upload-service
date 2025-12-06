Asynchronous Image Processing Service

🚀 Project Overview

This project implements a robust, production-ready backend service for handling asynchronous image uploads and processing. It solves the common problem of long-running tasks in web applications by offloading the heavy lifting (resizing, compression, thumbnail generation) to a dedicated task queue, ensuring a fast and responsive user experience.

The service is fully containerized using Docker Compose, making it easy to set up and run locally.

✨ Features

•
Asynchronous Processing: Users receive an immediate response while image processing happens in the background.

•
File Upload: Dedicated /upload endpoint for receiving image files.

•
Object Storage: Uses Minio (S3-compatible) for scalable and durable file storage.

•
Background Tasks: Celery worker handles the image processing pipeline.

•
Image Manipulation: Resizes, compresses, and generates thumbnails using the Pillow library.

•
Status Tracking: Dedicated /upload/{id}/status endpoint to monitor job progress.

•
Result Retrieval: Dedicated /upload/{id}/result endpoint to fetch URLs of processed images.

🛠️ Technology Stack

Component
Technology
Role
Web Framework
FastAPI
High-performance API endpoints.
Task Queue
Celery
Distributed task queue for asynchronous work.
Message Broker/Backend
Redis
Used by Celery for task queuing and result storage.
Object Storage
Minio
S3-compatible storage for all image files.
Image Processing
Pillow (PIL)
Python library for image manipulation.
Containerization
Docker Compose
Orchestration for the multi-service environment.


📦 Project Structure

The core components of the service are:

Plain Text


image-processor-service/
├── docker-compose.yml  # Defines all services (API, Worker, Redis, Minio)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Defines the Python environment for API and Worker
├── config.py           # Shared configuration for Minio and Celery connections
├── app.py              # FastAPI application with API endpoints
├── tasks.py            # Celery worker with image processing logic
└── README.md           # This file


⚙️ Setup and Installation

Prerequisites

You must have the following installed on your system:

•
Docker

•
Docker Compose (usually included with Docker Desktop)

Steps

1.
Clone the Repository (or create the directory):

Bash


git clone <repository-url>
cd image-processor-service


(If you are creating the project manually, ensure all files are placed in the image-processor-service directory.)



2.
Build and Run the Services: The docker-compose.yml file orchestrates the entire environment.

Bash


docker compose up --build -d


This command will:

•
Build the Python image using the Dockerfile.

•
Start the redis, minio, api, and worker containers.



3.
Verify Services: Check that all four services are running correctly.

Bash


docker compose ps


All containers should show a status of Up.



4.
View Logs (Optional): To monitor the output of the API and Worker in real-time:

Bash


docker compose logs -f


(Press Ctrl+C to exit the logs.)



🧪 Usage and Testing

We will use curl to interact with the API endpoints. The API is exposed on http://localhost:8000.

1. Download a Sample Image

First, get a file to upload.

Bash


wget -O sample.jpg https://picsum.photos/800/600


2. Upload the Image (/upload )

This command sends the image and starts the processing task.

Bash


curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.jpg;type=image/jpeg"


Expected Output (JSON ): The API returns a task_id and URLs for status and results. Copy the task_id.

JSON


{
  "id": "...",
  "task_id": "a1b2c3d4-...",
  "filename": "sample.jpg",
  "status_url": "/upload/a1b2c3d4-.../status",
  "result_url": "/upload/a1b2c3d4-.../result",
  "message": "File uploaded successfully. Processing started in the background."
}


3. Check Status (/upload/{id}/status)

Replace <YOUR_TASK_ID> with the ID you copied.

Bash


TASK_ID="<YOUR_TASK_ID>"
curl -X GET "http://localhost:8000/upload/${TASK_ID}/status"


The status will change from PENDING -> PROGRESS -> SUCCESS.

4. Retrieve Results (/upload/{id}/result )

Once the status is SUCCESS, fetch the final processed URLs.

Bash


curl -X GET "http://localhost:8000/upload/${TASK_ID}/result"


Expected Output (JSON ):

JSON


{
  "status": "SUCCESS",
  "result": {
    "resized_compressed": "/files/processed/a1b2c3d4-.../sample_resized_compressed.jpeg",
    "thumbnail": "/files/processed/a1b2c3d4-.../sample_thumbnail.jpeg"
  }
}


5. Access Processed File (/files/{path:path})

Use the URL path from the result to download the processed file (e.g., the thumbnail).

Bash


THUMBNAIL_PATH="/files/processed/a1b2c3d4-.../sample_thumbnail.jpeg"
curl -o final_thumbnail.jpeg "http://localhost:8000${THUMBNAIL_PATH}"


Bash






🧹 Cleanup

To stop and remove all containers and networks:

Bash


docker compose down


To also remove the volumes (Minio and Redis data ):

Bash


docker compose down -v





