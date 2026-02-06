FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY __init__.py .
COPY main.py .
COPY MLLP/ ./MLLP/
COPY decoder/ ./decoder/
COPY processor/ ./processor/
COPY pager/ ./pager/
COPY saved_model/ ./saved_model/

# Entry point
CMD ["python", "main.py"]
