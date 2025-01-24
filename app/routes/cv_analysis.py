# Conteúdo atual do cv_analysis.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import asyncio  # Adicionando import do asyncio
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
from pypdf import PdfReader  # Mudado de PyPDF2 para pypdf
import docx
import io
from app.utils.keywords_filter import filter_relevant_keywords
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()

# Inicialize o cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def validate_content_type(content_type: str) -> bool:
    """Validação aprimorada do Content-Type"""
    if not content_type:
        return False
    valid_types = {
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    }
    return any(content_type.lower() == mime_type for mime_type in valid_types.keys())

async def validate_file_content(file: UploadFile) -> bool:
    """Nova função para validação do conteúdo do arquivo"""
    magic_numbers = {
        b'%PDF': '.pdf',
        b'\xD0\xCF\x11\xE0': '.doc',
        b'PK\x03\x04': '.docx'
    }
    header = await file.read(4)
    await file.seek(0)
    return any(header.startswith(magic) for magic in magic_numbers.keys())

async def read_resume(file: UploadFile) -> str:
    # Validação do Content-Type
    if not await validate_content_type(file.content_type):
        raise HTTPException(status_code=400, detail="Content-Type inválido")
    
    # Limite de tamanho do arquivo (ex: 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB em bytes
    content = await file.read(MAX_FILE_SIZE + 1)
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande")
    
    try:
        if file.filename.endswith('.pdf'):
            pdf_reader = PdfReader(io.BytesIO(content))
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
            
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {str(e)}")
        raise HTTPException(status_code=400, detail="Erro ao processar arquivo")

async def fetch_job_descriptions(urls: List[str]) -> List[str]:
    descriptions = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_single_job(session, url) for url in urls if url.strip()]
        descriptions = await asyncio.gather(*tasks, return_exceptions=True)
    return [desc for desc in descriptions if isinstance(desc, str) and desc.strip()]

async def fetch_single_job(session: aiohttp.ClientSession, url: str) -> str:
    job_site_parsers = {
        'gupy.io': parse_gupy_job,
        'linkedin.com': parse_linkedin_job,
        'indeed.com': parse_indeed_job,
        # Adicionar mais sites conforme necessário
    }
    
    try:
        domain = extract_domain(url)
        parser = job_site_parsers.get(domain, parse_generic_job)
        return await parser(session, url)
    except Exception as e:
        logger.error(f"Erro ao buscar vaga {url}: {str(e)}")
        return ""

async def get_embedding(text: str, model="text-embedding-3-small") -> list:
    """Gera embedding para um texto usando a API da OpenAI"""
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Erro ao gerar embedding: {str(e)}")
        raise

async def analyze_resume(resume_text: str, job_descriptions: List[str]) -> dict:
    try:
        # Gerar embeddings para o currículo e descrições das vagas
        resume_embedding = await get_embedding(resume_text)
        job_embeddings = [await get_embedding(desc) for desc in job_descriptions]
        
        # Calcular similaridade média com todas as descrições de vagas
        similarities = [
            cosine_similarity([resume_embedding], [job_emb])[0][0]
            for job_emb in job_embeddings
        ]
        avg_similarity = sum(similarities) / len(similarities)

        prompt = """Você é um especialista em análise de currículos para sistemas ATS (Applicant Tracking Systems). Siga estas etapas rigorosamente:

1. **Análise da Descrição da Vaga**:
   - Extraia termos-chave da descrição da vaga usando técnicas avançadas de NLP (lematização, reconhecimento de entidades nomeadas e análise de contexto).
   - Foque em:
     * Competências técnicas (ex: "Python", "AWS", "Scrum")
     * Atividades/responsabilidades (ex: "desenvolvimento de APIs", "gestão de equipe ágil")
     * Requisitos obrigatórios (ex: "graduação em Engenharia", "certificação PMP")
     * Soft skills contextualizadas (ex: "comunicação técnica", "resolução de problemas complexos")
   - Normalize os termos (ex: "Python 3.11" → "Python", "JS" → "JavaScript").

2. **Análise do Currículo**:
   - Processe o texto do currículo com:
     * Reconhecimento de padrões semânticos
     * Cross-referencing de sinônimos (ex: "JS" → "JavaScript")
     * Identificação de experiências quantificáveis (ex: "reduziu tempo de deploy em 40%")

3. **Comparação Crítica**:
   - Gere uma tabela comparativa com:
     [✅] Palavras-chave correspondentes (com evidências do texto)
     [⚠️] Habilidades relacionadas mas não explícitas
     [❌] Requisitos ausentes críticos

4. **Recomendações Estratégicas**:
   - Para cada ausência relevante:
     * Sugira onde incluir no currículo (experiência, resumo, habilidades)
     * Dê exemplos contextualizados

5. **Mensagem Motivacional**:
   - Gere uma mensagem personalizada com base na taxa de match

SIMILARIDADE SEMÂNTICA CALCULADA: {avg_similarity:.2f}

CURRÍCULO:
{resume_text}

DESCRIÇÕES DAS VAGAS:
{chr(10).join(job_descriptions)}

Formato de Saída (JSON):
{{
  "job_keywords": {{
    "technical_skills": [],
    "activities": [],
    "requirements": []
  }},
  "resume_matches": {{
    "exact_matches": [],
    "partial_matches": [],
    "missing_critical": []
  }},
  "semantic_similarity": {{
    "score": "{avg_similarity:.2f}",
    "matches": []
  }},
  "missing_keywords_with_recommendations": [],
  "match_percentage": "",
  "motivational_message": ""
}}"""

        logger.info("Enviando requisição para OpenAI")
        
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um especialista em ATS e análise de currículos. Forneça análises detalhadas focando em correspondências exatas e semânticas. Retorne APENAS o JSON solicitado, sem texto adicional."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={ "type": "json_object" }
        )

        logger.info("Resposta recebida da OpenAI")
        
        logger.debug(f"Resposta completa da OpenAI: {response.choices[0].message.content}")

        raw_analysis = json.loads(response.choices[0].message.content)
        
        # Verifica campos obrigatórios
        required_fields = [
            'job_keywords',
            'resume_matches',
            'semantic_similarity',
            'missing_keywords_with_recommendations',
            'match_percentage',
            'motivational_message'
        ]
        
        missing_fields = [field for field in required_fields if field not in raw_analysis]
        
        if missing_fields:
            logger.error(f"Campos ausentes na resposta: {missing_fields}")
            logger.error(f"Resposta recebida: {raw_analysis}")
            raise ValueError(f"Campos obrigatórios ausentes: {missing_fields}")

        return raw_analysis

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON da resposta: {e}")
        raise ValueError(f"Erro ao processar resposta: {str(e)}")
    except Exception as e:
        logger.error(f"Erro na análise do currículo: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro durante o processo de análise: {str(e)}"
        )

def normalize_text_for_comparison(text: str) -> str:
    """
    Normaliza o texto para comparação case-insensitive e remove espaços extras
    """
    # Remove caracteres especiais mantendo espaços
    import re
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    # Remove espaços extras
    return ' '.join(text.split())

def identify_resume_section(text: str, line_index: int) -> str:
    """
    Identifica a seção do currículo baseado no contexto
    """
    sections = {
        "resumo": ["resumo", "sobre mim", "perfil", "objetivo", "apresentação"],
        "experiência": ["experiência", "experiencias", "profissional", "trabalho", "carreira"],
        "formação": ["formação", "educação", "acadêmico", "escolaridade"],
        "habilidades": ["habilidades", "competências", "conhecimentos", "tecnologias", "skills"],
        "certificações": ["certificações", "certificados", "cursos", "qualificações"],
        "idiomas": ["idiomas", "línguas"],
        "projetos": ["projetos", "portfolio", "realizações"]
    }
    
    lines = text.split('\n')
    # Procura até 10 linhas acima para encontrar o cabeçalho da seção
    start_index = max(0, line_index)
    end_index = max(-1, line_index - 11)
    
    for i in range(start_index, end_index, -1):
        line_lower = lines[i].lower().strip()
        for section_name, keywords in sections.items():
            if any(keyword in line_lower for keyword in keywords):
                return section_name.title()
    
    # Se não encontrar seção específica, procura em todo o texto
    text_lower = text.lower()
    for section_name, keywords in sections.items():
        if any(keyword in text_lower for keyword in keywords):
            return section_name.title()
    
    return "Experiência"  # Default para experiência em vez de "Outros"

def validate_keyword_match(keyword: str, text: str) -> tuple[bool, str]:
    """
    Valida se há uma correspondência exata da palavra-chave no texto e retorna a seção
    """
    normalized_keyword = normalize_text_for_comparison(keyword)
    lines = text.split('\n')
    
    # Padrão para encontrar a palavra exata, considerando limites de palavra
    import re
    keyword_pattern = r'\b' + re.escape(normalized_keyword) + r'\b'
    
    for i, line in enumerate(lines):
        normalized_line = normalize_text_for_comparison(line)
        match = re.search(keyword_pattern, normalized_line)
        if match:
            # Verifica o contexto da linha para garantir que é uma correspondência válida
            words_in_line = normalized_line.split()
            keyword_words = normalized_keyword.split()
            
            # Verifica se todas as palavras da keyword estão presentes na linha na mesma ordem
            for j in range(len(words_in_line) - len(keyword_words) + 1):
                if words_in_line[j:j+len(keyword_words)] == keyword_words:
                    section = identify_resume_section(text, i)
                    return True, section
    
    return False, ""

def validate_analysis_results(analysis_result: dict, resume_text: str) -> dict:
    """
    Valida e corrige os resultados da análise
    """
    validated_present = []
    
    # Garantir que all_keywords contenha APENAS palavras-chave das vagas
    all_keywords = set(analysis_result['extracted_keywords']['all_keywords'])
    
    # Para cada palavra-chave das vagas, procurar no currículo
    for keyword in all_keywords:
        found, _ = validate_keyword_match(keyword, resume_text)
        if found:
            # Adiciona apenas a palavra-chave, sem indicação de seção
            validated_present.append(keyword)
    
    # Atualizar as palavras-chave presentes
    analysis_result['keywords']['present'] = validated_present
    
    # Atualizar as palavras-chave faltantes
    present_keywords = set(validated_present)
    missing_keywords = all_keywords - present_keywords
    
    # Adiciona apenas as palavras-chave faltantes, sem sugestão de seção
    analysis_result['keywords']['missing'] = list(missing_keywords)
    
    # Garantir que extracted_keywords.all_keywords mantenha TODAS as palavras-chave das vagas
    analysis_result['extracted_keywords']['all_keywords'] = list(all_keywords)
    
    return analysis_result

def suggest_section(keyword: str) -> str:
    """
    Sugere a seção mais apropriada para adicionar cada tipo de palavra-chave
    """
    keyword_lower = keyword.lower()
    
    # Mapeamento de palavras-chave para seções sugeridas
    section_mapping = {
        'technical': ['sql', 'python', 'java', 'docker', 'aws', 'azure', 'git'],
        'methodologies': ['scrum', 'kanban', 'agile', 'lean', 'xp'],
        'tools': ['jira', 'confluence', 'trello', 'miro', 'figma'],
        'business': ['product owner', 'stakeholder', 'backlog', 'kpi', 'roi'],
        'certifications': ['pmp', 'psm', 'safe', 'cspo'],
    }
    
    for section, keywords in section_mapping.items():
        if any(k in keyword_lower for k in keywords):
            if section == 'technical':
                return "Habilidades Técnicas"
            elif section == 'methodologies':
                return "Metodologias"
            elif section == 'tools':
                return "Ferramentas"
            elif section == 'business':
                return "Experiência Profissional"
            elif section == 'certifications':
                return "Certificações"
    
    return "Experiência Profissional"

def remove_duplicate_keywords(analysis_result: dict) -> dict:
    """
    Remove palavras-chave duplicadas mantendo a primeira ocorrência
    """
    def normalize_for_dedup(keyword: str) -> str:
        """Normaliza keyword para comparação de duplicatas"""
        # Remove caracteres especiais e converte para minúsculas
        text = re.sub(r'[^\w\s]', '', keyword.lower()).strip()
        
        # Lista reduzida de palavras a serem ignoradas quando sozinhas
        # Mantém termos técnicos e de negócio mesmo quando sozinhos
        ignore_single_words = {
            'framework', 'ferramenta', 'plataforma',
            'sistema', 'ambiente', 'módulo',
            'conhecimento', 'experiência'
        }
        
        # Se a keyword for uma única palavra e estiver na lista de ignoradas, retorna vazio
        if text in ignore_single_words:
            return ''
            
        # Lista expandida de termos compostos que devem ser mantidos intactos
        compound_terms = {
            # Termos de Produto e Negócio
            'product owner', 'product manager', 'product backlog', 'product vision',
            'visão do produto', 'qualidade do produto', 'jornada de usuários',
            'histórias de usuário', 'critérios de aceitação', 'indicadores de performance',
            'times ágeis', 'desenvolvimento ágil', 'metodologia ágil',
            
            # Termos Técnicos e Ferramentas
            'banco de dados', 'base de dados', 'sistema operacional',
            'desenvolvimento web', 'desenvolvimento mobile', 'desenvolvimento frontend',
            'desenvolvimento backend', 'desenvolvimento fullstack',
            'programação orientada a objetos', 'arquitetura de software',
            'arquitetura de sistemas', 'infraestrutura de ti',
            'infraestrutura cloud', 'serviços web', 'web services',
            'interface de usuário', 'experiência do usuário',
            
            # Termos de Gestão e Processos
            'gestão de projetos', 'gerenciamento de projetos',
            'gestão de produtos', 'gestão de equipes', 'liderança técnica',
            'metodologia scrum', 'framework scrum', 'método ágil',
            'processo ágil', 'rituais ágeis',
            
            # Termos de Negócio Específicos
            'sub adquirência', 'gateway de pagamento', 'anti fraude',
            'processamento de pagamentos', 'meios de pagamento',
            'indicadores de performance', 'kpis de negócio',
            'análise de dados', 'business intelligence'
        }
        
        # Termos técnicos e siglas que devem ser mantidos mesmo quando sozinhos
        technical_terms = {
            'sql', 'kpi', 'pmo', 'pos', 'cro', 'api', 'app', 'apps',
            'jira', 'trello', 'miro', 'figma', 'techfin', 'fintech',
            'backlog', 'scrum', 'kanban', 'devops', 'agile',
            'gateway', 'gateways', 'antifraude'
        }
        
        # Se é um termo técnico sozinho, retorna ele mesmo
        if text in technical_terms:
            return text
            
        # Se o texto normalizado for um termo composto conhecido, retorna ele mesmo
        text_normalized = ' '.join(text.split())  # normaliza espaços
        if text_normalized in compound_terms:
            return text_normalized
            
        # Remove palavras ignoradas do início do termo
        words = text_normalized.split()
        if words and words[0] in ignore_single_words:
            words = words[1:]
        
        result = ' '.join(words)
        
        # Se após normalização ficar vazio, retorna o texto original normalizado
        return result if result else text_normalized
    
    # Processar all_keywords mantendo a versão mais completa
    keyword_groups = {}
    for keyword in analysis_result['extracted_keywords']['all_keywords']:
        norm_key = normalize_for_dedup(keyword)
        if norm_key:
            if norm_key not in keyword_groups or len(keyword) > len(keyword_groups[norm_key]):
                keyword_groups[norm_key] = keyword
    
    analysis_result['extracted_keywords']['all_keywords'] = list(keyword_groups.values())
    
    # Processar keywords present
    present_groups = {}
    for entry in analysis_result['keywords']['present']:
        keyword = entry.split(" - Em:")[0].strip()
        section = entry.split(" - Em:")[1].strip()
        norm_key = normalize_for_dedup(keyword)
        if norm_key:
            if norm_key not in present_groups or len(keyword) > len(present_groups[norm_key][0]):
                present_groups[norm_key] = (keyword, section)
    
    analysis_result['keywords']['present'] = [
        f"{keyword} - Em: {section}" for keyword, section in present_groups.values()
    ]
    
    # Processar keywords missing
    missing_groups = {}
    for entry in analysis_result['keywords']['missing']:
        keyword = entry.split(" - Add em:")[0].strip()
        section = entry.split(" - Add em:")[1].strip()
        norm_key = normalize_for_dedup(keyword)
        if norm_key and norm_key not in present_groups:
            if norm_key not in missing_groups or len(keyword) > len(missing_groups[norm_key][0]):
                missing_groups[norm_key] = (keyword, section)
    
    analysis_result['keywords']['missing'] = [
        f"{keyword} - Add em: {section}" for keyword, section in missing_groups.values()
    ]
    
    return analysis_result

@router.post("/analyze")
async def analyze_cv(
    file: UploadFile = File(...),
    job_links: List[str] = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Iniciando análise para usuário: {current_user.email}")
        
        # Verificar créditos com lock para evitar condições de corrida
        user_credits = db.query(UserCredits).filter(
            UserCredits.user_id == current_user.id
        ).with_for_update().first()

        logger.info(f"Créditos antes da análise: {user_credits.remaining_analyses if user_credits else 0}")

        if not user_credits or user_credits.remaining_analyses < 1:
            logger.warning(f"Créditos insuficientes para usuário: {current_user.email}")
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
            
            # Verificar se a análise retornou resultados válidos
            if (
                isinstance(analysis, dict) and
                'error' not in analysis and
                'extracted_keywords' in analysis and
                'keywords' in analysis and
                len(analysis.get('extracted_keywords', {}).get('all_keywords', [])) > 0
            ):
                # Só deduz créditos se a análise foi bem-sucedida e retornou palavras-chave
                user_credits.remaining_analyses -= 1
                try:
                    db.commit()
                    logger.info(f"Crédito deduzido com sucesso. Restantes: {user_credits.remaining_analyses}")
                except Exception as e:
                    logger.error(f"Erro ao deduzir crédito: {str(e)}")
                    db.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail="Erro ao processar créditos"
                    )
                
                return analysis
            else:
                logger.error("Análise retornou resultado vazio ou inválido")
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail="A análise não retornou resultados válidos. Nenhum crédito foi consumido."
                )

        except Exception as e:
            logger.error(f"Erro durante o processo de análise: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Erro durante a análise: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro geral: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/test-analysis")
async def test_cv_analysis():
    test_results = []
    for resume, job in test_cases():
        result = await analyze_cv(resume, [job])
        test_results.append({
            "resume": resume,
            "job": job,
            "analysis": result
        })
    return test_results
