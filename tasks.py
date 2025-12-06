import io
from celery import Celery
from PIL import Image
from minio.error import S3Error
from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, minio_client, MINIO_BUCKET, initialize_minio_bucket

# Initialize Celery App
celery_app = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configuration for image processing
RESIZE_DIMENSION = (800, 600)
THUMBNAIL_DIMENSION = (128, 128)
COMPRESSION_QUALITY = 85 # JPEG quality

# Ensure Minio bucket is initialized when the worker starts
initialize_minio_bucket()

@celery_app.task(bind=True)
def process_image(self, file_id: str, original_filename: str):
    """
    Background task to download an image from Minio, process it, and upload results.
    """
    try:
        # 1. Download the original image from Minio
        original_object_name = f"original/{file_id}/{original_filename}"
        print(f"Downloading {original_object_name}...")
        response = minio_client.get_object(MINIO_BUCKET, original_object_name)
        image_bytes = response.read()
        response.close()
        response.release_conn()

        # Open the image with Pillow
        img = Image.open(io.BytesIO(image_bytes))
        
        # Determine the base name for processed files
        base_name, ext = original_filename.rsplit('.', 1)
        
        processed_urls = {}

        # --- 2. Resize and Compress ---
        # Update task state to provide progress feedback
        self.update_state(state='PROGRESS', meta={'step': 'Resizing and Compressing'})
        
        # Resize
        img_resized = img.copy()
        img_resized.thumbnail(RESIZE_DIMENSION)
        
        # Compress (and save as JPEG for better compression)
        resized_compressed_name = f"{base_name}_resized_compressed.jpeg"
        resized_compressed_object_name = f"processed/{file_id}/{resized_compressed_name}"
        
        output_buffer = io.BytesIO()
        img_resized.save(output_buffer, format="JPEG", quality=COMPRESSION_QUALITY)
        output_buffer.seek(0)
        
        # Upload resized and compressed image
        minio_client.put_object(
            MINIO_BUCKET,
            resized_compressed_object_name,
            output_buffer,
            len(output_buffer.getvalue()),
            content_type='image/jpeg'
        )
        # The URL is a path that the API will use to serve the file
        processed_urls['resized_compressed'] = f"/files/{resized_compressed_object_name}"
        print(f"Uploaded {resized_compressed_object_name}")

        # --- 3. Generate a Thumbnail ---
        self.update_state(state='PROGRESS', meta={'step': 'Generating Thumbnail'})
        
        # Generate thumbnail
        img_thumbnail = img.copy()
        img_thumbnail.thumbnail(THUMBNAIL_DIMENSION)
        
        # Save as JPEG
        thumbnail_name = f"{base_name}_thumbnail.jpeg"
        thumbnail_object_name = f"processed/{file_id}/{thumbnail_name}"
        
        output_buffer = io.BytesIO()
        img_thumbnail.save(output_buffer, format="JPEG", quality=COMPRESSION_QUALITY)
        output_buffer.seek(0)
        
        # Upload thumbnail
        minio_client.put_object(
            MINIO_BUCKET,
            thumbnail_object_name,
            output_buffer,
            len(output_buffer.getvalue()),
            content_type='image/jpeg'
        )
        processed_urls['thumbnail'] = f"/files/{thumbnail_object_name}"
        print(f"Uploaded {thumbnail_object_name}")

        # 4. Return the result (URLs)
        return {
            'status': 'SUCCESS',
            'result': processed_urls
        }

    except S3Error as e:
        print(f"Minio Error: {e}")
        raise
    except Exception as e:
        print(f"Processing Error: {e}")
        raise