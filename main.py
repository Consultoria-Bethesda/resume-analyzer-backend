from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import openai
import json
import logging
import aiohttp
from bs4 import BeautifulSoup
import PyPDF2
import docx
import io

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da chave de API da OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_keyword(keyword: str) -> str:
    """Formata a palavra-chave para um formato mais conciso e mantém correspondência exata."""
    try:
        if ' - Encontrada em: ' in keyword:
            term, location = keyword.split(' - Encontrada em: ')
            # Remove 'Palavra-chave' e aspas simples/duplas
            term = term.replace('Palavra-chave ', '').strip('"\'')
            # Pega apenas a primeira palavra da localização (RESUMO, SKILLS, etc)
            location = location.split()[0].strip('"\'')
            return f"{term} - Em: {location}"
        elif ' - Sugestão: Adicionar em ' in keyword:
            term, location = keyword.split(' - Sugestão: Adicionar em ')
            term = term.replace('Palavra-chave ', '').strip('"\'')
            location = location.split()[0].strip('"\'')
            return f"{term} - Add em: {location}"
        return keyword.strip('"\'')
    except Exception:
        return keyword

async def read_resume(file: UploadFile) -> str:
    """Lê e extrai o texto do currículo."""
    try:
        content = await file.read()
        text = ""

        if file.filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() for page in pdf_reader.pages)
        elif file.filename.endswith(('.doc', '.docx')):
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        else:
            raise ValueError("Formato de arquivo não suportado")

        return text
    except Exception as e:
        logger.error(f"Erro ao ler o currículo: {str(e)}")
        raise

async def fetch_job_descriptions(urls: List[str]) -> Dict[str, str]:
    """Busca as descrições das vagas das URLs fornecidas."""
    job_descriptions = {}
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            if not url.strip():
                continue
                
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Adapte estes seletores conforme necessário
                        job_description = soup.find('div', {'class': 'job-description'})
                        if job_description:
                            job_descriptions[url] = job_description.get_text()
                        else:
                            # Fallback: pega todo o texto do body
                            job_descriptions[url] = soup.body.get_text()
            except Exception as e:
                logger.error(f"Erro ao buscar vaga {url}: {str(e)}")
                job_descriptions[url] = ""

    return job_descriptions

def validate_response(response_text: str) -> Dict[str, Any]:
    """Valida a resposta JSON e extrai os dados mesmo se estiver parcialmente completa."""
    try:
        # Procura por um JSON válido na resposta
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            # Extrai a parte do JSON até onde está completa
            json_str = response_text[start_idx:end_idx]
            
            try:
                # Primeiro, tenta processar o JSON como está
                data = json.loads(json_str)
                
                # Se chegou aqui, temos um JSON válido
                # Extrai os dados disponíveis
                introduction = data.get('introduction', '')
                all_keywords = data.get('extracted_keywords', {}).get('all_keywords', [])
                keywords = data.get('keywords', {})
                present_keywords = keywords.get('present', [])
                
                # Para missing_keywords, remove o último item se estiver incompleto
                missing_keywords = keywords.get('missing', [])
                if missing_keywords and any(k.endswith(('Palavra', 'Sug')) for k in missing_keywords):
                    missing_keywords = missing_keywords[:-1]
                
                # Formata as palavras-chave para serem mais concisas
                present_keywords = [format_keyword(k) for k in present_keywords]
                missing_keywords = [format_keyword(k) for k in missing_keywords]
                
                # Retorna os dados estruturados
                return {
                    "introduction": introduction,
                    "extracted_keywords": {
                        "all_keywords": all_keywords
                    },
                    "keywords": {
                        "present": present_keywords,
                        "missing": missing_keywords
                    },
                    "recommendations": [
                        "Adicione as palavras-chave ausentes",
                        "Destaque as palavras-chave presentes",
                        "Adicione mais detalhes sobre experiências"
                    ],
                    "conclusion": "Analise as palavras-chave e faça os ajustes sugeridos."
                }
                
            except json.JSONDecodeError:
                # Se o JSON está incompleto, tenta extrair manualmente
                introduction_match = '"introduction": "([^"]+)"'
                all_keywords_start = '"all_keywords": ['
                all_keywords_end = ']'
                present_start = '"present": ['
                present_end = ']'
                missing_start = '"missing": ['
                missing_end = ']'
                
                # Extrai introduction
                introduction = ''
                if '"introduction"' in json_str:
                    introduction = json_str.split('"introduction": "')[1].split('"')[0]
                
                # Extrai all_keywords
                all_keywords = []
                if all_keywords_start in json_str:
                    keywords_section = json_str.split(all_keywords_start)[1].split(all_keywords_end)[0]
                    all_keywords = [k.strip(' "') for k in keywords_section.split(',') if k.strip(' "')]
                
                # Extrai present keywords
                present_keywords = []
                if present_start in json_str:
                    present_section = json_str.split(present_start)[1].split(present_end)[0]
                    present_keywords = [k.strip(' "') for k in present_section.split(',') if k.strip(' "')]
                
                # Extrai missing keywords
                missing_keywords = []
                if missing_start in json_str:
                    missing_section = json_str.split(missing_start)[1].split(missing_end)[0]
                    missing_keywords = [k.strip(' "') for k in missing_section.split(',') if k.strip(' "')]
                    # Remove o último item se estiver incompleto
                    if missing_keywords and any(k.endswith(('Palavra', 'Sug')) for k in missing_keywords):
                        missing_keywords = missing_keywords[:-1]
                
                # Formata as palavras-chave
                present_keywords = [format_keyword(k) for k in present_keywords]
                missing_keywords = [format_keyword(k) for k in missing_keywords]
                
                return {
                    "introduction": introduction,
                    "extracted_keywords": {
                        "all_keywords": all_keywords
                    },
                    "keywords": {
                        "present": present_keywords,
                        "missing": missing_keywords
                    },
                    "recommendations": [
                        "Adicione as palavras-chave ausentes",
                        "Destaque as palavras-chave presentes",
                        "Adicione mais detalhes sobre experiências"
                    ],
                    "conclusion": "Analise as palavras-chave e faça os ajustes sugeridos."
                }
    
    except Exception as e:
        logger.error(f"Erro na validação da resposta: {str(e)}")
        logger.error(f"Resposta original: {response_text}")
    
    # Se não conseguiu processar, retorna resposta vazia estruturada
    return create_fallback_response()

def create_fallback_response() -> Dict[str, Any]:
    """Cria uma resposta de fallback em caso de erro."""
    return {
        "introduction": "Análise do currículo para as vagas.",
        "extracted_keywords": {
            "all_keywords": []
        },
        "keywords": {
            "present": [],
            "missing": []
        },
        "recommendations": [
            "Adicione palavras-chave relevantes",
            "Destaque suas experiências"
        ],
        "conclusion": "Revise seu currículo considerando as sugestões."
    }

async def analyze_resume(resume_text: str, job_descriptions: List[str]) -> Dict[str, Any]:
    """Analisa o currículo em relação às descrições das vagas."""
    
    # Construímos a parte das descrições das vagas
    job_descriptions_text = ""
    for i, description in enumerate(job_descriptions):
        job_descriptions_text += f"VAGA {i+1}:\n{description}\n\n"

    # Define o prompt revisado
    prompt = f'''
Analise as descrições das vagas e o currículo fornecido. Retorne APENAS o JSON abaixo preenchido:

{{
"introduction": "Análise resumida do currículo de [nome] para as vagas de [cargo]. [Breve análise da adequação do perfil, destacando 2-3 pontos fortes e 1-2 pontos de melhoria]",
"extracted_keywords": {{
"all_keywords": [
"TODAS as palavras-chave extraídas das descrições das vagas (EXATAMENTE como aparecem)"
]
}},
"keywords": {{
"present": [
"[termo exato] - Em: [seção]"
],
"missing": [
"[termo exato] - Add em: [seção]"
]
}},
"recommendations": [
"Adicione as palavras-chave ausentes",
"Destaque as palavras-chave presentes",
"Adicione mais detalhes sobre experiências"
],
"conclusion": "Conclusão breve"
}}

CURRÍCULO:
{resume_text}

DESCRIÇÕES DAS VAGAS:
{job_descriptions_text}

IMPORTANTE:
- Na introdução, faça uma análise resumida da adequação do perfil
- Extraia TODAS as palavras-chave das vagas EXATAMENTE como aparecem
- Compare com o currículo usando correspondência EXATA
- Use formato conciso (ex: "Python - Em: Skills")
- Mantenha a grafia e capitalização exatas
- Retorne APENAS o JSON
'''

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um especialista em ATS. Retorne APENAS o JSON solicitado, sem texto adicional."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # Log da resposta para debug
        logger.info(f"Resposta da OpenAI: {response.choices[0].message.content}")

        # Valida e retorna a resposta
        return validate_response(response.choices[0].message.content)

    except Exception as e:
        logger.error(f"Erro na análise do currículo: {str(e)}")
        return create_fallback_response()

@app.post("/generate/pdf")
async def analyze_resume_and_jobs(
    resume: UploadFile = File(...),
    job_urls: str = Form(...)
) -> Dict[str, Any]:
    """Endpoint principal para análise do currículo."""
    try:
        # Lê o currículo
        resume_text = await read_resume(resume)
        
        # Processa as URLs das vagas
        job_urls = json.loads(job_urls)
        job_descriptions = await fetch_job_descriptions(job_urls)

        # Analisa o currículo com as descrições das vagas
        analysis = await analyze_resume(resume_text, list(job_descriptions.values()))
        
        # Log do resultado final
        logger.info(f"Análise final: {json.dumps(analysis, indent=2)}")
        
        return analysis

    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)