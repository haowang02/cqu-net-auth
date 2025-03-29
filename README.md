# 重庆大学校园网认证脚本

持续监测网络认证状态并认证校园网，适合服务器、路由器等场景使用。效果如下：

```bash
$ python .\login.py --account 2018xxxx --password xxxxxx --term_type pc
2025-03-29 22:03:29,705 - INFO - 每5秒检查一次网络状态, 如果掉线则重新认证
2025-03-29 22:03:29,705 - INFO - 如果需要停止程序, 请使用 Ctrl+C 停止
2025-03-29 22:03:42,848 - INFO - 正在认证: 账户(2018xxxx), 设备类型(pc), 设备IP(10.x.x.x)
2025-03-29 22:03:43,214 - INFO - 认证成功: 王x(2018xxxx)
2025-03-29 22:04:21,815 - INFO - 正在认证: 账户(2018xxxx), 设备类型(pc), 设备IP(10.x.x.x)
2025-03-29 22:04:22,179 - INFO - 认证成功: 王x(2018xxxx)
```

## 直接运行

```
# 环境变量传参
ACCOUNT=校园网账户 PASSWORD=校园网密码 TERM_TYPE=终端类型 python login.py
# 注意：终端类型选填 android 或 pc

# 命令行传参 (兼容 Windows 系统)
python login.py --account 校园网账户 --password 校园网密码 --term_type 终端类型
# 注意：终端类型选填 android 或 pc
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
    -e ACCOUNT="校园网账户" \
    -e PASSWORD="校园网密码" \
    -e TERM_TYPE="终端类型" \           # 注意：终端类型选填 android 或 pc
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

检查校园网 IP
```bash
curl -s "http://10.254.7.4/a79.htm" | iconv -f GBK -t UTF-8 | grep -oP "v46ip='.*?'"
```
