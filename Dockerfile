FROM python:3.11-slim

WORKDIR /app

COPY simple_test_app.py .

EXPOSE 8080

CMD ["python", "simple_test_app.py"]