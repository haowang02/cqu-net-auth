# 重庆大学校园网认证脚本

持续监测网络认证状态并认证校园网，适合服务器、路由器等场景使用。

## 直接运行

```
pip install requests
USERNAME=校园网账户 PASSWORD=校园网密码 TYPE=设备类型 IP=待认证的校园网IP python login.py
# 注意：设备类型选填 android 或 pc
```

## Docker 容器运行

构建容器:

```bash
docker build -t cqu-net-auth .
```

启动:

```bash
docker run -d \
    --name cqu-net-auth \
    --restart always \
    -e USERNAME="校园网账户" \
    -e PASSWORD="校园网密码" \
    -e TYPE="设备类型" \           # 注意：设备类型选填 android 或 pc
    -e IP="待认证的校园网IP" \
    cqu-net-auth
```

查看日志:

```bash
docker logs -f cqu-net-auth
```