FROM python:3.14-slim

# Устанавливаем uv
RUN pip install uv

WORKDIR /fastapi_beckend_app

COPY requirements.txt .
# Синхронизируем зависимости с помощью uv
RUN uv pip install  --system -r requirements.txt
# Копируем файлы проекта
COPY . .

# Создаем директорию для монтирования (если будет использоваться)
RUN mkdir -p /local_storage

EXPOSE 8010

# Запускаем Streamlit
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]