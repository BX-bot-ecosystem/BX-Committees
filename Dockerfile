FROM python:3.10

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./
COPY service_account.json ../

CMD ["python", "Committees-Parrot.py"]
