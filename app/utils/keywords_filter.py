def filter_relevant_keywords(keywords: list) -> list:
    """
    Filtra palavras-chave relevantes para análise técnica e profissional,
    excluindo benefícios e informações adicionais
    """
    # Lista de palavras-chave a serem excluídas (benefícios e informações adicionais)
    exclude_patterns = {
        # Benefícios
        r'vale.*', r'assistência.*', r'convênio.*', r'seguro.*',
        r'gympass', r'plano.*saúde', r'benefícios?', r'day\s*off',
        
        # Remuneração
        r'remuneração.*', r'salário.*', r'bônus.*', r'participação.*lucros?',
        r'plr', r'remuneração.*variável', r'comissão.*',
        
        # Modalidade de trabalho
        r'modelo\s+de\s+trabalho.*', r'híbrido', r'remoto', r'presencial',
        r'home\s*office',
        
        # Localização e horário
        r'horário.*', r'jornada.*', r'expediente.*',
        r'localização.*', r'região.*', r'bairro.*',
        
        # Contratação
        r'regime.*', r'contratação.*', r'vaga.*', r'oportunidade.*',
        r'efetivo', r'temporário', r'estágio', r'trainee',
        
        # Outros benefícios
        r'curso.*', r'treinamento.*', r'desenvolvimento.*profissional',
        r'flexibilidade.*', r'dress\s*code'
    }
    
    def should_exclude(keyword: str) -> bool:
        """Verifica se a palavra-chave deve ser excluída baseado nos padrões"""
        import re
        keyword_lower = keyword.lower()
        return any(re.search(pattern, keyword_lower) for pattern in exclude_patterns)
    
    # Retorna palavras-chave que não se enquadram nos padrões de exclusão
    filtered_keywords = []
    for keyword in keywords:
        if not should_exclude(keyword):
            # Remove espaços extras e padroniza
            cleaned_keyword = ' '.join(keyword.split())
            filtered_keywords.append(cleaned_keyword)
    
    return filtered_keywords