FROM python:3.8-alpine
ENV TZ=Asia/Shanghai
WORKDIR /app
COPY login.py .
CMD ["python", "login.py"]