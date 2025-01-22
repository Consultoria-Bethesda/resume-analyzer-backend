from app.utils.pdf_handler import process_pdf
from fastapi import UploadFile
import logging

logger = logging.getLogger(__name__)

async def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Extracts text from a PDF file using the pdf_handler module.
    
    Args:
        file (UploadFile): The uploaded PDF file
        
    Returns:
        str: Extracted text from the PDF
        
    Raises:
        HTTPException: If there's an error processing the PDF
    """
    try:
        content = await file.read()
        text = process_pdf(content)
        await file.seek(0)  # Reset file pointer for potential future reads
        return text
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise