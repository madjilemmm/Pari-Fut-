FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY ml/ ml/
COPY jobs/ jobs/
COPY data/ data/

RUN chmod +x backend/entrypoint.sh
CMD ["backend/entrypoint.sh"]
