import os
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from dotenv import load_dotenv
load_dotenv()
def ocr_document(
    file_path: str, 
) -> str:
    """
    Performs OCR on a local PDF or Image file using Google Cloud Document AI.

    Args:
        file_path: Path to the local file (e.g., 'invoice.pdf' or 'image.png').

    Returns:
        The full text extracted from the document.
    """

    # 1. Set the Endpoint based on location
    project_id = os.getenv("GOOGLE_OCR_PROJECT_ID")
    location = os.getenv("GOOGLE_OCR_LOCATION")
    processor_id = os.getenv("GOOGLE_OCR_PROCESSOR_ID")
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # 2. Determine Mime Type based on extension
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".pdf":
        mime_type = "application/pdf"
    elif extension in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif extension == ".png":
        mime_type = "image/png"
    elif extension == ".tiff":
        mime_type = "image/tiff"
    else:
        raise ValueError(f"Unsupported file extension: {extension}")

    # 3. Read the file
    with open(file_path, "rb") as image:
        image_content = image.read()

    # 4. configure the process request
    name = client.processor_path(project_id, location, processor_id)
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    # 5. Process the document
    result = client.process_document(request=request)
    document = result.document

    return document.text

# --- Usage Example ---
if __name__ == "__main__":
    # Ensure you have set the GOOGLE_APPLICATION_CREDENTIALS env var (see Step 2)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\Shaq\Documents\receipts_document_intelligence\document-intelligence-481415-c71e576236f1.json"
    FILE_PATH = r"C:\Users\Shaq\Documents\receipts_document_intelligence\sroie_50_samples\SROIE2019\train\img\X00016469612.jpg"

    try:
        text = ocr_document(FILE_PATH)
        print("Extracted Text:\n", text)
    except Exception as e:
        print(f"Error: {e}")