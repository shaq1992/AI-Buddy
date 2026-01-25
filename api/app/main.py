import os
import shutil
import json
import logging
import asyncio
import pika
from threading import Thread
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

# --- Config ---
SHARED_VOLUME_PATH = "/shared_data"
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "ai-message-broker")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

# Exchanges & Queues
EXCHANGE_NAME = "ai_system_exchange"
REQUEST_ROUTING_KEY = "request"
RESULT_QUEUE = "result_queue"

# --- Background Consumer Logic ---
def start_result_consumer():
    """
    Listens to RabbitMQ 'result_queue' and saves results to disk.
    Run this in a separate thread.
    """
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        
        # Ensure queue exists
        channel.queue_declare(queue=RESULT_QUEUE, durable=True)

        def callback(ch, method, properties, body):
            try:
                data = json.loads(body)
                job_id = data.get("job_id")
                
                if job_id:
                    # Save result to Shared Volume
                    result_path = os.path.join(SHARED_VOLUME_PATH, f"{job_id}_result.json")
                    with open(result_path, "w") as f:
                        json.dump(data, f, indent=2)
                    
                    logger.info(f"Result for {job_id} saved to disk.")
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error saving result: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=RESULT_QUEUE, on_message_callback=callback)
        logger.info("Result Consumer started listening...")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Result Consumer crashed: {e}")

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch Consumer Thread
    consumer_thread = Thread(target=start_result_consumer, daemon=True)
    consumer_thread.start()
    yield
    # Shutdown logic (if any)

app = FastAPI(title="AI Job Manager", lifespan=lifespan)

# --- Helper: Publisher ---
def publish_job(payload: dict):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=REQUEST_ROUTING_KEY,
        body=json.dumps(payload)
    )
    connection.close()

# --- Endpoints ---

@app.post("/ingest")
async def ingest_job(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    problem_statement: str = Form(...),
    user_ideas: str = Form(...),
    user_techstack: str = Form(...),
    user_resume: UploadFile = File(...)
):
    # 1. Save File
    file_path = os.path.join(SHARED_VOLUME_PATH, f"{job_id}.pdf")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(user_resume.file, buffer)
    except Exception:
        raise HTTPException(status_code=500, detail="File save failed")

    # 2. Prepare Payload
    payload = {
        "job_id": job_id,
        "problem_statement": problem_statement,
        "user_ideas": user_ideas,
        "user_techstack": user_techstack,
        "file_path": file_path,
        "status": "queued"
    }

    # 3. Publish (Background Task)
    background_tasks.add_task(publish_job, payload)

    return {"job_id": job_id, "status": "queued", "message": "Job submitted successfully"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Check if the result file exists in the shared volume.
    """
    result_path = os.path.join(SHARED_VOLUME_PATH, f"{job_id}_result.json")
    
    if os.path.exists(result_path):
        try:
            with open(result_path, "r") as f:
                data = json.load(f)
            return data
        except Exception:
            return {"job_id": job_id, "status": "processing", "error": "File unreadable"}
    
    # If file doesn't exist, assume it's still processing
    # (In a real app, you'd check a DB to distinguish 'processing' from 'not found')
    return {"job_id": job_id, "status": "processing"}
