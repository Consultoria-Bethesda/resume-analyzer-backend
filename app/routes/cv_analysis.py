from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.user_credits import UserCredits
from app.middleware.auth import get_current_user
import logging
import json
from openai import OpenAI
from app.config.settings import settings
import aiohttp
from bs4 import BeautifulSoup
import PyPDF2
import docx
import io

logger = logging.getLogger(__name__)
router = APIRouter()

# Inicialize o cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def read_resume(file: UploadFile) -> str:
    content = await file.read()
    
    if file.filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    elif file.filename.endswith(('.doc', '.docx')):
        doc = docx.Document(io.BytesIO(content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    else:
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")

async def fetch_job_descriptions(urls: List[str]) -> List[str]:
    descriptions = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            if url and url.strip():
                try:
                    clean_url = url.strip()
                    if not clean_url.startswith(('http://', 'https://')):
                        clean_url = 'https://' + clean_url
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    async with session.get(clean_url, headers=headers, allow_redirects=True) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
                                tag.decompose()
                            
                            if 'gupy.io' in clean_url:
                                job_description = soup.find('div', {'data-testid': 'job-description'})
                                if job_description:
                                    text = job_description.get_text(separator=' ', strip=True)
                                else:
                                    text = soup.find('main').get_text(separator=' ', strip=True) if soup.find('main') else ''
                            else:
                                text = soup.get_text(separator=' ', strip=True)
                            
                            text = ' '.join(text.split())
                            if text:
                                descriptions.append(text)
                            else:
                                logger.error(f"Texto vazio para URL: {clean_url}")
                                descriptions.append("")
                        else:
                            logger.error(f"Erro ao acessar URL {clean_url}: Status {response.status}")
                            descriptions.append("")
                except Exception as e:
                    logger.error(f"Erro ao buscar descrição da vaga: {str(e)}")
                    descriptions.append("")
    
    valid_descriptions = [desc for desc in descriptions if desc.strip()]
    if not valid_descriptions:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível obter a descrição das vagas. Por favor, verifique se os links são válidos e acessíveis."
        )
    
    return descriptions

async def analyze_resume(resume_text: str, job_descriptions: List[str]) -> dict:
    try:
        prompt = f"""
Analise o currículo fornecido em comparação com as descrições das vagas e forneça uma análise detalhada no formato JSON abaixo.
Seja específico e detalhado em cada seção.

IMPORTANTE:
- Identifique o nome e cargo atual do candidato
- Extraia TODAS as palavras-chave das vagas, considerando a descrição da vaga obtida em requisitos, requerimentos, qualificações, responsabilidades e atribuições, e IGNORAR palavras-chave presentes em informações adicionais ou benefícios
- Compare as palavras-chave com o currículo exiba corretamente no item que identifica quais palavras estão presentes, NÃO mostre junto com as palavras-chave identificadas nas vagas enviadas.
- Forneça recomendações específicas e acionáveis
- Mantenha os termos exatamente como aparecem

Retorne APENAS o JSON abaixo preenchido:

{{
"introduction": "Análise detalhada do currículo de [NOME] para as vagas de [CARGO]. [Breve resumo do perfil e adequação]",
"extracted_keywords": {{
"all_keywords": [
"Lista completa de TODAS as palavras-chave e termos relevantes encontrados nas descrições das vagas (mantenha EXATAMENTE como aparecem)"
]
}},
"keywords": {{
"present": [
"[termo exato] - Em: [seção específica do currículo onde foi encontrado]"
],
"missing": [
"[termo exato] - Add em: [seção sugerida para adicionar]"
]
}},
"recommendations": [
"Lista de recomendações específicas e acionáveis para melhorar o currículo"
],
"conclusion": "Conclusão objetiva sobre a adequação do currículo às vagas e principais pontos de melhoria"
}}

CURRÍCULO:
{resume_text}

DESCRIÇÕES DAS VAGAS:
{json.dumps(job_descriptions)}
"""

        logger.info("Enviando requisição para OpenAI")
        
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um especialista em ATS e análise de currículos com vasta experiência em recrutamento e seleção. Forneça análises detalhadas e recomendações práticas. Retorne APENAS o JSON solicitado, sem texto adicional."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={ "type": "json_object" }
        )

        logger.info("Resposta recebida da OpenAI")
        logger.info(f"Conteúdo da resposta: {response.choices[0].message.content}")

        try:
            analysis_result = json.loads(response.choices[0].message.content)
            logger.info("JSON decodificado com sucesso")
            
            required_keys = ["introduction", "extracted_keywords", "keywords", "recommendations", "conclusion"]
            if all(key in analysis_result for key in required_keys):
                return analysis_result
            else:
                logger.error("JSON incompleto - faltam chaves obrigatórias")
                missing_keys = [key for key in required_keys if key not in analysis_result]
                logger.error(f"Chaves faltantes: {missing_keys}")
                return {
                    "error": True,
                    "introduction": "Análise incompleta do currículo.",
                    "extracted_keywords": {"all_keywords": []},
                    "keywords": {"present": [], "missing": []},
                    "recommendations": ["A análise não pôde ser completada. Por favor, tente novamente."],
                    "conclusion": "Não foi possível concluir a análise completamente."
                }

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {str(e)}")
            logger.error(f"Conteúdo que causou erro: {response.choices[0].message.content}")
            return {
                "error": True,
                "introduction": "Erro ao processar a análise do currículo.",
                "extracted_keywords": {"all_keywords": []},
                "keywords": {"present": [], "missing": []},
                "recommendations": ["Houve um erro ao processar sua análise. Por favor, tente novamente."],
                "conclusion": "A análise não pôde ser concluída devido a um erro técnico."
            }

    except Exception as e:
        logger.error(f"Erro geral na análise: {str(e)}")
        return {
            "error": True,
            "introduction": "Não foi possível processar a análise do currículo.",
            "extracted_keywords": {"all_keywords": []},
            "keywords": {"present": [], "missing": []},
            "recommendations": ["Por favor, tente novamente. Se o erro persistir, entre em contato com o suporte."],
            "conclusion": "Não foi possível concluir a análise."
        }

@router.post("/analyze")
async def analyze_cv(
    file: UploadFile = File(...),
    job_links: List[str] = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user_credits = db.query(UserCredits).filter(
            UserCredits.user_id == current_user.id
        ).first()

        if not user_credits or user_credits.remaining_analyses < 1:
            raise HTTPException(
                status_code=402,
                detail="Créditos insuficientes. Por favor, adquira mais créditos."
            )

        cleaned_links = []
        for link in job_links:
            if link and isinstance(link, str) and link.strip():
                clean_link = link.strip()
                if not clean_link.startswith(('http://', 'https://')):
                    clean_link = 'https://' + clean_link
                cleaned_links.append(clean_link)
        
        logger.info(f"Links processados: {cleaned_links}")

        if not cleaned_links:
            raise HTTPException(
                status_code=400,
                detail="É necessário fornecer pelo menos um link de vaga para análise"
            )

        if len(cleaned_links) > 2:
            raise HTTPException(
                status_code=400,
                detail="Máximo de 2 links de vagas permitidos por análise"
            )

        try:
            resume_text = await read_resume(file)
            logger.info("Currículo lido com sucesso")
            
            job_descriptions = await fetch_job_descriptions(cleaned_links)
            logger.info("Descrições das vagas obtidas com sucesso")
            
            analysis = await analyze_resume(resume_text, job_descriptions)
            logger.info("Análise realizada com sucesso")
            
            user_credits.remaining_analyses -= 1
            db.commit()
            logger.info(f"Créditos deduzidos com sucesso para usuário {current_user.email}")
            
            return analysis

        except Exception as e:
            logger.error(f"Erro durante o processo de análise: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro inesperado. Por favor, tente novamente mais tarde."
        )