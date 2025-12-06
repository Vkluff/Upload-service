import os
from minio import Minio

# --- Configuration ---
# Minio (S3-compatible storage)
MINIO_HOST = os.getenv("MINIO_HOST", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = "image-uploads"

# Celery (Worker/Broker)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
# Celery connection strings use the environment variables
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# --- Minio Client Initialization ---
def get_minio_client():
    """Initializes and returns a Minio client."""
    # The host is split into address and port for the Minio client
    host, port = MINIO_HOST.split(':')
    client = Minio(
        f"{host}:{port}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False # Use secure=True for production with SSL
    )
    return client

def initialize_minio_bucket():
    """Creates the Minio bucket if it does not exist."""
    client = get_minio_client()
    found = client.bucket_exists(MINIO_BUCKET)
    if not found:
        client.make_bucket(MINIO_BUCKET)
        print(f"Created bucket '{MINIO_BUCKET}'")
    else:
        print(f"Bucket '{MINIO_BUCKET}' already exists")

# Export the client for use in other modules
minio_client = get_minio_client()