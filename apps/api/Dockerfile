FROM python:3.10-slim

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app code
COPY app /app/app

COPY tests /app/tests

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
