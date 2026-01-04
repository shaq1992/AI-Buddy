# Multi-Container AI Document Processing System

This project is a microservices-based architecture for processing documents using AI. It consists of a FastAPI gateway, a RabbitMQ message broker, and (upcoming) AI Workers, all running in Docker on WSL 2.

## 📋 Prerequisites

* Docker Desktop installed and running (WSL 2 backend recommended).
* Terminal with Docker CLI access.
* **Sample PDF:** You need at least one PDF file to test the upload.

---

## 🛠️ Step 1: Infrastructure Setup (Do This First)

Before building the containers, we must manually create the shared network and storage volume. This allows the isolated containers to communicate and share files.

1.  **Create the Shared Network:**
    ```bash
    docker network create ai-network
    ```

2.  **Create the Shared Volume:**
    ```bash
    docker volume create ai_shared_data
    ```

---

## 🐰 Step 2: Build & Run RabbitMQ

The message broker handles the queuing of document processing jobs.

### 1. Build the Image
Navigate to the `rabbitmq` directory and build the custom image with baked-in definitions.

```bash
cd rabbitmq
docker build -t ai-rabbitmq:v1 .
2. Run the Container
Run the container, attaching it to the ai-network.

Bash

docker run -d \
  --name ai-message-broker \
  --network ai-network \
  -p 5672:5672 \
  -p 15672:15672 \
  ai-rabbitmq:v1
3. Verify Health
Open your browser to: http://localhost:15672

Username: guest | Password: guest

Check: Ensure the queues (request_queue, result_queue) listed in your definitions.json appear in the "Queues" tab.

🔌 Step 3: Build & Run the API
The API accepts files and pushes job metadata to RabbitMQ.

1. Build the Image
We use a manual build step to tag the image as api:v1.0.0 (as required by the compose file).

Bash

cd ../api
docker build -t api:v1.0.0 .
2. Run with Docker Compose
Use the docker-compose.yml inside the api folder to orchestrate the run.

Bash

docker-compose up -d
3. Verify Health
Check Logs: Ensure connection to RabbitMQ was successful.

Bash

docker logs -f ai_api
Look for: Application startup complete.

Check Swagger UI:

Open http://localhost:8000/docs

You should see the /ingest endpoint.

✅ Step 4: End-to-End Test
Test if the API successfully saves the file and queues the job.

Option A: Using Curl (Linux/Mac/WSL) Create a dummy PDF and send it.

Bash

# 1. Create a dummy PDF (if you don't have one)
echo "dummy content" > test_doc.pdf

# 2. Send the request
curl -X 'POST' \
  'http://localhost:8000/ingest' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'job_id=test-job-001' \
  -F 'problem_statement=Extract key skills' \
  -F 'user_ideas=Use OCR and LLM' \
  -F 'user_techstack=Python, Docker' \
  -F 'user_resume=@test_doc.pdf;type=application/pdf'
Option B: Using Swagger UI

Go to http://localhost:8000/docs.

Expand the POST /ingest endpoint.

Click Try it out.

Fill in the text fields (job_id, problem_statement, etc.).

Upload a real PDF file in the user_resume field.

Click Execute.

Expected Result
API Response:

JSON

{
  "job_id": "test-job-001",
  "status": "queued"
}
RabbitMQ:

Go to Management UI (localhost:15672).

Click on Queues -> request_queue.

You should see "Ready" messages count increase by 1.
