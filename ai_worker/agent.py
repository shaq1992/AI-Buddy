import logging
import os
from infra.google_doc_ai import ocr_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_request(data: dict) -> dict:
    """
    Orchestrates the AI processing:
    1. OCR extraction (Google Doc AI)
    2. (Future) LLM Analysis
    """
    job_id = data.get("job_id", "unknown")
    file_path = data.get("file_path")

    logger.info(f"--- [Job: {job_id}] Processing Started ---")

    # 1. Validation
    if not file_path or not os.path.exists(file_path):
        error_msg = f"File not found at {file_path}"
        logger.error(error_msg)
        return {"job_id": job_id, "status": "failed", "error": error_msg}

    # 2. OCR Extraction
    try:
        logger.info(f"Sending {file_path} to Google Doc AI...")
        # Call the infra function
        extracted_text = ocr_document(file_path)
        
        logger.info(f"OCR Successful. Extracted {len(extracted_text)} characters.")
        
        # Log a snippet for verification
        logger.info(f"Snippet: {extracted_text[:100]}...")

        # 3. Return Result Data
        return {
            "job_id": job_id,
            "status": "completed",
            "extracted_text": extracted_text,
            "original_request": data
        }

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return {"job_id": job_id, "status": "failed", "error": str(e)}