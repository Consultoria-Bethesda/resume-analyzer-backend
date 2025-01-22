FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Script de inicialização
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Usar o script de entrypoint para inicializar o banco e iniciar a aplicação
ENTRYPOINT ["./docker-entrypoint.sh"]
