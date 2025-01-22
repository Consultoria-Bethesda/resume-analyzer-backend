from pypdf import PdfReader
import io
import logging
from fastapi import HTTPException
import time

logger = logging.getLogger(__name__)

def process_pdf(content: bytes, max_pages: int = 100) -> str:
    """
    Processa arquivo PDF com proteções contra loops infinitos e validações de segurança
    """
    try:
        # Proteção contra arquivos muito grandes
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="PDF file size exceeds maximum limit"
            )

        # Timeout global para todo o processamento
        start_time = time.time()
        MAX_PROCESSING_TIME = 30  # 30 segundos total

        pdf_reader = PdfReader(io.BytesIO(content))
        
        if len(pdf_reader.pages) > max_pages:
            raise HTTPException(
                status_code=400,
                detail=f"PDF exceeds maximum page limit of {max_pages}"
            )
        
        text = ""
        for page in pdf_reader.pages:
            # Verifica timeout global
            if time.time() - start_time > MAX_PROCESSING_TIME:
                logger.warning("PDF processing timeout reached")
                break

            try:
                page_text = page.extract_text()
                text += page_text
            except Exception as e:
                logger.error(f"Error extracting text from page: {str(e)}")
                continue
                
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=400, detail="Error processing PDF file")
