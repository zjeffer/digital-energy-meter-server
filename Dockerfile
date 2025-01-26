FROM python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -U pyserial
RUN pip install --no-cache-dir -r requirements.txt -U

COPY . .

EXPOSE 8000

CMD ["python3", "server.py"]