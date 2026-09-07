FROM python:3.14-slim

# Install uv
RUN pip install uv

WORKDIR /fastapi_beckend_app

COPY requirements.txt .
# Sync dependencies using uv
RUN uv pip install  --system -r requirements.txt
# Copy project files
COPY . .

# Create the mount directory (if it will be used)
RUN mkdir -p /local_storage

EXPOSE 8010

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
