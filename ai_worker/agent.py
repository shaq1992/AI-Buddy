import logging
import os
import asyncio
from infra.google_doc_ai import ocr_document
# Import the new core logic
from core.simple_critic import analyze_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_request(data: dict) -> dict:
    """
    Orchestrates the AI processing:
    1. OCR extraction (Google Doc AI)
    2. AI Critic Analysis (Agent Framework + Gemini)
    """
    # Since the worker_engine calls this synchronously, we run the async agent code 
    # using asyncio.run() for this version.
    return asyncio.run(_process_request_async(data))

async def _process_request_async(data: dict) -> dict:
    job_id = data.get("job_id", "unknown")
    file_path = data.get("file_path")
    
    # Extract User Context Fields
    problem = data.get("problem_statement", "No problem provided")
    ideas = data.get("user_ideas", "No ideas provided")
    techstack = data.get("user_techstack", "No techstack provided")

    logger.info(f"--- [Job: {job_id}] Processing Started ---")

    # 1. Validation
    if not file_path or not os.path.exists(file_path):
        error_msg = f"File not found at {file_path}"
        logger.error(error_msg)
        return {"job_id": job_id, "status": "failed", "error": error_msg}

    try:
        # 2. OCR Extraction (Infra Layer)
        logger.info(f"Sending {file_path} to Google Doc AI...")
        extracted_text = ocr_document(file_path)
        logger.info(f"OCR Successful. Extracted {len(extracted_text)} characters.")

        # 3. AI Agent Analysis (Core Layer)
        logger.info("Handing off to Critic Agent...")
        critique = await analyze_request(
            problem=problem,
            user_ideas=ideas,
            user_techstack=techstack,
            resume_text=extracted_text
        )
        
        logger.info("Critic Agent finished successfully.")

        # 4. Return Result Data
        return {
            "job_id": job_id,
            "status": "completed",
            "extracted_text_snippet": extracted_text[:200], # Don't return full text to save bandwidth
            "ai_critique": critique, # The Agent's output
            "original_request": data
        }

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return {"job_id": job_id, "status": "failed", "error": str(e)}
