import os
import shutil
import json
import logging
import pika
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Document Ingestion API")

# Infrastructure Constants
SHARED_VOLUME_PATH = "/shared_data"
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "ai-message-broker")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
EXCHANGE_NAME = "ai_system_exchange"
ROUTING_KEY = "request"

def publish_to_rabbitmq(message: dict):
    """
    Connects to RabbitMQ and publishes the job message.
    """
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        
        # We assume exchange is already declared by the Broker container, 
        # but declaring it here passively ensures we don't crash if it's missing.
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', passive=True)
        
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=json.dumps(message)
        )
        connection.close()
        logger.info(f"Job {message.get('job_id')} published to RabbitMQ.")
        
    except Exception as e:
        logger.error(f"Failed to publish to RabbitMQ: {e}")
        # In a real production app, we might want to implement a retry mechanism here
        # or mark the job as 'failed' in the DB.

@app.post("/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    problem_statement: str = Form(...),
    user_ideas: str = Form(...),
    user_techstack: str = Form(...),
    user_resume: UploadFile = File(...)
):
    # 1. Validation
    if user_resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF allowed.")
    
    # 2. File Persistence (Shared Volume)
    # We use the job_id as the filename to ensure uniqueness and easy retrieval
    file_location = os.path.join(SHARED_VOLUME_PATH, f"{job_id}.pdf")
    
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(user_resume.file, buffer)
        logger.info(f"File saved to {file_location}")
    except Exception as e:
        logger.error(f"Disk I/O Error: {e}")
        raise HTTPException(status_code=500, detail="Could not save the uploaded file.")

    # 3. Construct Message Payload
    # We send the FILE PATH, not the file content
    payload = {
        "job_id": job_id,
        "problem_statement": problem_statement,
        "user_ideas": user_ideas,
        "user_techstack": user_techstack,
        "file_path": file_location,
        "status": "queued"
    }

    # 4. Offload Publishing to Background Task
    # This ensures the HTTP response is fast and not blocking on RabbitMQ network I/O
    background_tasks.add_task(publish_to_rabbitmq, payload)

    return {"job_id": job_id, "status": "queued"}