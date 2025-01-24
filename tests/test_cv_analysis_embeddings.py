import pytest
from app.routes.cv_analysis import get_embedding, analyze_resume
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Dados de teste
TEST_RESUME = """
Desenvolvedor Full Stack Senior
10 anos de experiência em desenvolvimento de software

Habilidades Técnicas:
- Python, Django, FastAPI
- JavaScript, React, Node.js
- AWS (Lambda, EC2, S3)
- Docker, Kubernetes
- MongoDB, PostgreSQL

Experiência Profissional:
Tech Lead na Empresa XYZ (2020-2023)
- Liderou equipe de 8 desenvolvedores usando metodologia Scrum
- Implementou CI/CD pipeline reduzindo tempo de deploy em 70%
- Migrou arquitetura monolítica para microserviços
"""

TEST_JOB_DESCRIPTION = """
Buscamos Desenvolvedor Full Stack Senior
Requisitos:
- Sólida experiência com Python e frameworks web
- Conhecimento em React e Node.js
- Experiência com AWS e containers
- Familiaridade com metodologias ágeis
- Capacidade de liderar equipes técnicas
"""

@pytest.mark.asyncio
async def test_get_embedding():
    """Testa a geração de embeddings"""
    embedding = await get_embedding(TEST_RESUME)
    
    # Verifica se o embedding tem o formato correto
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.asyncio
async def test_embedding_similarity():
    """Testa o cálculo de similaridade entre embeddings"""
    resume_embedding = await get_embedding(TEST_RESUME)
    job_embedding = await get_embedding(TEST_JOB_DESCRIPTION)
    
    # Calcula similaridade
    similarity = cosine_similarity([resume_embedding], [job_embedding])[0][0]
    
    # Verifica se a similaridade está entre 0 e 1
    assert 0 <= similarity <= 1
    # Deve ter alta similaridade dado o conteúdo similar
    assert similarity > 0.7

@pytest.mark.asyncio
async def test_analyze_resume():
    """Testa a análise completa do currículo"""
    result = await analyze_resume(TEST_RESUME, [TEST_JOB_DESCRIPTION])
    
    # Verifica estrutura da resposta
    assert isinstance(result, dict)
    assert "job_keywords" in result
    assert "resume_matches" in result
    assert "semantic_similarity" in result
    assert "missing_keywords_with_recommendations" in result
    assert "match_percentage" in result
    assert "motivational_message" in result
    
    # Verifica campos específicos
    assert isinstance(result["semantic_similarity"]["score"], str)
    assert float(result["semantic_similarity"]["score"]) > 0
    
    # Verifica matches esperados
    assert "Python" in str(result["resume_matches"])
    assert "AWS" in str(result["resume_matches"])
    
    # Verifica formato do match_percentage
    assert "%" in result["match_percentage"]
    match_value = float(result["match_percentage"].strip("%"))
    assert 0 <= match_value <= 100

@pytest.mark.asyncio
async def test_analyze_resume_with_multiple_jobs():
    """Testa análise com múltiplas descrições de vagas"""
    job_descriptions = [
        TEST_JOB_DESCRIPTION,
        """
        Senior Backend Developer
        - Python expertise required
        - Experience with FastAPI and Django
        - Database design skills
        - AWS knowledge
        """,
        """
        Full Stack Team Lead
        - React and Node.js experience
        - Python backend development
        - Team leadership experience
        - Agile methodologies
        """
    ]
    
    result = await analyze_resume(TEST_RESUME, job_descriptions)
    
    # Verifica se a análise considera todas as descrições
    assert isinstance(result, dict)
    assert float(result["semantic_similarity"]["score"]) > 0
    
    # Deve encontrar matches comuns entre todas as descrições
    common_skills = ["Python", "AWS"]
    for skill in common_skills:
        assert skill in str(result["resume_matches"])

@pytest.mark.asyncio
async def test_analyze_resume_edge_cases():
    """Testa casos extremos"""
    # Currículo vazio
    with pytest.raises(Exception):
        await analyze_resume("", [TEST_JOB_DESCRIPTION])
    
    # Descrição de vaga vazia
    with pytest.raises(Exception):
        await analyze_resume(TEST_RESUME, [""])
    
    # Lista vazia de descrições
    with pytest.raises(Exception):
        await analyze_resume(TEST_RESUME, [])

if __name__ == "__main__":
    pytest.main(["-v", "test_cv_analysis_embeddings.py"])