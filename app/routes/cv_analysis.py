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
from pypdf import PdfReader  # Mudado de PyPDF2 para pypdf
import docx
import io
from app.utils.keywords_filter import filter_relevant_keywords

logger = logging.getLogger(__name__)
router = APIRouter()

# Inicialize o cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def validate_content_type(content_type: str) -> bool:
    """Validação básica do Content-Type para mitigar ReDoS"""
    if not content_type:
        return False
    valid_types = ['multipart/form-data', 'application/pdf', 'application/msword', 
                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    return any(valid_type in content_type.lower() for valid_type in valid_types)

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
1. Extraia TODAS as palavras-chave relevantes das vagas, considerando:

OBRIGATORIAMENTE INCLUIR:
- Cargos e funções específicas mencionadas
- Tecnologias, ferramentas e sistemas
- Metodologias e frameworks de trabalho
- Certificações e qualificações técnicas
- Conhecimentos específicos do setor/indústria
- Responsabilidades e atribuições chave
- Competências técnicas específicas
- Processos e práticas de trabalho relevantes
- Termos técnicos do setor
- Habilidades específicas requeridas
- Experiências profissionais relevantes
- Conhecimentos de negócio específicos
- Áreas de especialização

REGRAS DE EXTRAÇÃO:
- Capture termos técnicos mesmo quando aparecem sozinhos (ex: SQL, AWS)
- Mantenha termos compostos completos (ex: "gestão de projetos", não separar em "gestão" e "projetos")
- Inclua variações relevantes de termos (ex: se menciona "Product Owner" e "PO", inclua ambos)
- Capture termos específicos do setor/indústria
- Mantenha siglas e acrônimos relevantes (ex: KPI, B2B)
- Inclua competências comportamentais específicas e relevantes

OBRIGATORIAMENTE EXCLUIR:
- Benefícios (vale refeição, plano de saúde, etc)
- Modalidade de trabalho (remoto, híbrido)
- Localização e horário
- Informações sobre contratação
- Remuneração e comissões
- Outros benefícios (cursos, dress code)
- Informações sobre a empresa
- Prazos e datas
- Idiomas
- Termos genéricos sem contexto específico

CURRÍCULO:
{resume_text}

DESCRIÇÕES DAS VAGAS:
{chr(10).join(job_descriptions)}

Retorne um JSON com a seguinte estrutura:
{{
    "extracted_keywords": {{
        "all_keywords": ["lista de todas as palavras-chave extraídas das vagas"]
    }},
    "keywords": {{
        "present": ["palavras-chave encontradas no currículo - Em: seção sugerida"],
        "missing": ["palavras-chave não encontradas no currículo - Add em: seção sugerida"]
    }},
    "recommendations": ["lista de recomendações práticas para melhorar o currículo"],
    "conclusion": "conclusão geral da análise"
}}"""

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
            
            # Filtrar as palavras-chave para remover benefícios e informações adicionais
            if 'extracted_keywords' in analysis_result and 'all_keywords' in analysis_result['extracted_keywords']:
                filtered_keywords = filter_relevant_keywords(analysis_result['extracted_keywords']['all_keywords'])
                analysis_result['extracted_keywords']['all_keywords'] = filtered_keywords
                
                # Atualizar as listas de palavras presentes e ausentes com base nas palavras filtradas
                if 'keywords' in analysis_result:
                    if 'present' in analysis_result['keywords']:
                        analysis_result['keywords']['present'] = [
                            kw for kw in analysis_result['keywords']['present']
                            if any(filtered_kw in kw for filtered_kw in filtered_keywords)
                        ]
                    
                    if 'missing' in analysis_result['keywords']:
                        analysis_result['keywords']['missing'] = [
                            kw for kw in analysis_result['keywords']['missing']
                            if any(filtered_kw in kw for filtered_kw in filtered_keywords)
                        ]
            
            required_keys = ["extracted_keywords", "keywords", "recommendations", "conclusion"]
            if all(key in analysis_result for key in required_keys):
                return analysis_result
            else:
                logger.error("JSON incompleto - faltam chaves obrigatórias")
                missing_keys = [key for key in required_keys if key not in analysis_result]
                logger.error(f"Chaves faltantes: {missing_keys}")
                return {
                    "error": "Resposta incompleta da análise",
                    "missing_keys": missing_keys
                }

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
            return {"error": "Erro ao processar resposta da análise"}

    except Exception as e:
        logger.error(f"Erro geral na análise: {e}")
        return {"error": f"Erro geral na análise: {str(e)}"}

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
