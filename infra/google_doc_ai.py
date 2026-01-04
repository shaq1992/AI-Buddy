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
# --- Usage Example ---
if __name__ == "__main__":
    # Get the absolute path to the project root
    # (This makes it work regardless of where you run the command from)
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Correct Linux paths
    creds_path = os.path.join(base_path, "document-intelligence-481415-c71e576236f1.json")
    file_path = os.path.join(base_path, "Samples", "X00016469612.jpg")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    try:
        text = ocr_document(file_path)
        print("Extracted Text:\n", text)
    except Exception as e:
        print(f"Error: {e}")