# 1. Immagine di base
FROM python:3.13-slim

# 2. Imposta la cartella di lavoro
WORKDIR /app

# 3. Copia e installa le dipendenze
COPY requirements.txt .
RUN pip install -r requirements.txt

# 4. Copia il resto del progetto
COPY . .

# 5. (Opzionale) Esponi una porta
# EXPOSE 8000

# 6. Comando di avvio
CMD ["python", "run/NPM_analysis/run_HUT_analysis.py"]

# Crea l'immagine con:
# docker build -t hut_npm_analysis:latest .