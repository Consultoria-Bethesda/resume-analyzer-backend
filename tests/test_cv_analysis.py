def test_cases():
    # Caso 1: Correspondência exata com diferença de maiúsculas/minúsculas
    resume1 = """
    Experiência profissional:
    - Desenvolvedor PYTHON com 5 anos de experiência
    - Conhecimento em JAVASCRIPT e React
    """
    
    job1 = {
        "title": "Desenvolvedor Python",
        "requirements": [
            "Python",
            "JavaScript",
            "React"
        ]
    }

    # Caso 2: Palavras em contexto (não devem corresponder)
    resume2 = """
    Habilidades:
    - Conhecimentos básicos de programação Python
    - Experiência com desenvolvimento JavaScript
    """

    # Caso 3: Termos técnicos específicos
    resume3 = """
    Tecnologias:
    AWS
    DOCKER
    kubernetes
    """
    
    job3 = {
        "title": "DevOps Engineer",
        "requirements": [
            "AWS",
            "Docker",
            "Kubernetes"
        ]
    }

    return [(resume1, job1), (resume2, job1), (resume3, job3)]