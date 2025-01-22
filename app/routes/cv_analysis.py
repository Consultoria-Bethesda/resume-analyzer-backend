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
Analise o currículo e as descrições das vagas seguindo EXATAMENTE estas regras:

REGRAS DE EXTRAÇÃO DE PALAVRAS-CHAVE:
1. Extraia APENAS palavras-chave técnicas e profissionais relevantes das vagas, incluindo:
   - Requisitos técnicos e comportamentais
   - Ferramentas e tecnologias
   - Metodologias e frameworks
   - Responsabilidades e atribuições principais
   - Conhecimentos específicos do domínio
   - Certificações e qualificações relevantes
   - Habilidades técnicas e soft skills
   - Experiências específicas requeridas

2. NÃO inclua como palavras-chave:
   - Benefícios e remuneração
   - Modalidade de trabalho (remoto, híbrido, etc)
   - Localização e horário
   - Informações sobre contratação
   - Outros benefícios e facilidades

3. Regras de formatação:
   - REMOVA DUPLICATAS, mantendo a primeira ocorrência
   - Mantenha a forma mais completa dos termos
   - Preserve termos compostos quando relevantes
   - Mantenha acrônimos apenas quando são a forma principal de uso

4. Foque em extrair:
   - Competências técnicas específicas
   - Habilidades profissionais requeridas
   - Conhecimentos de domínio necessários
   - Responsabilidades principais da função
   - Experiências relevantes solicitadas

Retorne APENAS o JSON abaixo preenchido:

{{
"introduction": "Análise detalhada do currículo de [NOME] para as vagas de [CARGO]. [Breve resumo do perfil e adequação]",
"extracted_keywords": {{
"all_keywords": [
"Lista COMPLETA de palavras-chave ÚNICAS encontradas nas vagas (sem duplicatas, mantendo a grafia original da primeira ocorrência)"
]
}},
"keywords": {{
"present": [
"[termo exato único]"
],
"missing": [
"[termo exato único]"
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
            
            # Deduzir créditos em uma transação separada
            try:
                user_credits.remaining_analyses -= 1
                db.commit()
                logger.info(f"Créditos deduzidos com sucesso. Novo saldo: {user_credits.remaining_analyses}")
            except Exception as e:
                db.rollback()
                logger.error(f"Erro ao deduzir créditos: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Erro ao processar créditos"
                )
            
            validated_analysis = validate_analysis_results(analysis, resume_text)
            return validated_analysis

        except Exception as e:
            db.rollback()
            logger.error(f"Erro durante análise: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno do servidor"
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
