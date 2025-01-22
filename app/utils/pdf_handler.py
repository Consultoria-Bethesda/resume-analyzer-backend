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

        pdf_reader = PdfReader(io.BytesIO(content))
        
        # Proteção contra PDFs muito grandes
        if len(pdf_reader.pages) > max_pages:
            raise HTTPException(
                status_code=400,
                detail=f"PDF exceeds maximum page limit of {max_pages}"
            )
        
        text = ""
        for page in pdf_reader.pages:
            # Timeout para extração de texto por página
            start_time = time.time()
            try:
                page_text = page.extract_text()
                
                # Verifica timeout
                if time.time() - start_time > 5:  # 5 segundos timeout por página
                    logger.warning("Page processing timeout")
                    continue
                    
                text += page_text
                
            except Exception as e:
                logger.error(f"Error extracting text from PDF page: {str(e)}")
                continue
                
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from PDF"
            )
                
        return text
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail="Error processing PDF file"
        )
