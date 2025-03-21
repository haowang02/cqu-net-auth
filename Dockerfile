FROM python:3.8-alpine
WORKDIR /app
COPY login.py .
RUN pip install --no-cache-dir -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple requests
CMD ["python", "login.py"]