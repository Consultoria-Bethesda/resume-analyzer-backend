FROM python:3.9

WORKDIR /app

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Tornar o script de entrypoint executável
RUN chmod +x docker-entrypoint.sh

# Variáveis de ambiente
ENV PORT=8000
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Expor a porta
EXPOSE 8000

# Usar o script de entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
