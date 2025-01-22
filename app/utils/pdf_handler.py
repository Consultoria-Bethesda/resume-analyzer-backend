from pypdf import PdfReader
import io
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def process_pdf(content: bytes, max_pages: int = 100) -> str:
    """
    Processa arquivo PDF com proteções contra loops infinitos
    """
    try:
        pdf_reader = PdfReader(io.BytesIO(content))
        
        # Proteção contra PDFs muito grandes
        if len(pdf_reader.pages) > max_pages:
            raise HTTPException(
                status_code=400,
                detail=f"PDF exceeds maximum page limit of {max_pages}"
            )
        
        text = ""
        for page in pdf_reader.pages:
            # Timeout para extração de texto
            try:
                page_text = page.extract_text(timeout=5)  # 5 segundos timeout por página
                text += page_text
            except Exception as e:
                logger.error(f"Error extracting text from PDF page: {str(e)}")
                continue
                
        return text
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=400, detail="Error processing PDF file")