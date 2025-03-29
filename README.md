# 重庆大学校园网认证脚本

持续监测网络认证状态并认证校园网，适合服务器、路由器等场景使用。

## 直接运行

```
# 指定IP
USERNAME=校园网账户 PASSWORD=校园网密码 TERM_TYPE=终端类型 IP=待认证的校园网IP python login.py

# 指定WAN口（适用于路由器）
USERNAME=校园网账户 PASSWORD=校园网密码 TERM_TYPE=终端类型 WAN=路由器WAN口如eth0 python login.py

# 注意：终端类型选填 android 或 pc
```

## Docker 容器运行

构建容器:

```bash
docker build -t cqu-net-auth .
```

启动:

```bash
# 指定IP
docker run -d \
    --name cqu-net-auth \
    --restart always \
    -e USERNAME="校园网账户" \
    -e PASSWORD="校园网密码" \
    -e TERM_TYPE="终端类型" \           # 注意：终端类型选填 android 或 pc
    -e IP="待认证的校园网IP" \
    cqu-net-auth

# 指定WAN口（适用于路由器）
docker run -d \
    --name cqu-net-auth \
    --restart always \
    -e USERNAME="校园网账户" \
    -e PASSWORD="校园网密码" \
    -e TERM_TYPE="终端类型" \           # 注意：终端类型选填 android 或 pc
    -e WAN="路由器WAN口如eth0" \
    cqu-net-auth
```

查看日志:

```bash
docker logs -f cqu-net-auth
```

## 其他常用命令

登出校园网

```bash
curl http://10.254.7.4:801/eportal/portal/logout
```

检查当前认证的校园网账户
```bash
curl -s "http://10.254.7.4/" | iconv -f GBK -t UTF-8 | grep -oP "uid='.*?'|NID='.*?'"
```
