FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -m -u 1000 app && mkdir /app/data && chown app:app /app/data
COPY app.py engine.py orchestration.py access_control.py ./
COPY .streamlit .streamlit
USER app
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
