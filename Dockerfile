FROM python:3.8-alpine
WORKDIR /app
COPY login.py .
CMD ["python", "login.py"]