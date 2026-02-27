FROM python:3.11-slim

# seta o diretorio de trabalho
WORKDIR /app

# evita que o python crie arquivos .pyc e forca o log a aparecer na hora no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# instala as dependencias direto na imagem
RUN pip install --no-cache-dir -r requirements.txt

# copia o codigo do bot pro container
COPY main.py .

# comando final pra ligar o bot
CMD ["python", "main.py"]