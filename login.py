import os
import re
import sys
import time
import json
import signal
import socket
import logging
import urllib.error
import urllib.request
import argparse

logger = None


def get_ip():
    """获取待认证的ip"""
    try:
        with urllib.request.urlopen('http://10.254.7.4/a79.htm', timeout=5) as response:
            html = response.read().decode('GB2312')
            v46ip_match = re.search(r"v46ip='([^']+)'", html)
            return v46ip_match.group(1) if v46ip_match else None
    except Exception as e:
        return None


def is_internet_connected(host="223.6.6.6", port=53, timeout=3):
    """检查是否连接到互联网"""
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except Exception as e:
        return False
    
def is_http_connected(url, timeout=5):
    try:
        response = urllib.request.urlopen(url, timeout=timeout)

        if response.getcode() == 200:
            logger.debug(f"访问 {url} 成功, 状态码: {response.getcode()}")
            return True
        else:
            logger.warning(f"访问 {url} 失败, 状态码: {response.getcode()}")
            return False
    except urllib.error.URLError as e:
        # 捕获 URL 错误，例如无法连接到服务器、超时等
        logger.warning(f"访问 {url} 失败: {e.reason}")
        return False
    except urllib.error.HTTPError as e:
        # 捕获 HTTP 错误，例如 404、500 等
        logger.warning(f"访问 {url} 失败, HTTP 错误: {e.code} - {e.reason}")
        return False
    except Exception as e:
        # 捕获其他异常
        logger.error(f"访问 {url} 失败: {e}")
        return False


def get_account():
    """获取当前认证的账户"""
    try:
        with urllib.request.urlopen('http://10.254.7.4/', timeout=5) as response:
            html = response.read().decode('GB2312')
            id_match = re.search(r"uid='([^']*)'", html)
            name_match = re.search(r"NID='([^']*)'", html)
            id = id_match.group(1) if id_match else None
            name = name_match.group(1) if name_match else None
            return id, name
    except Exception as e:
        return None, None


def login(account: str, password: str, term_type: str, ip: str):
    """认证校园网
    dr1004({"result":1,"msg":"Portal协议认证成功！"});
    dr1004({"result":0,"msg":"账号不存在","ret_code":1});
    dr1004({"result":0,"msg":"密码错误","ret_code":1});
    dr1004({"result":0,"msg":"认证操作非本机终端！","ret_code":"1"});
    dr1004({"result":0,"msg":"认证出现异常！","ret_code":"1"});
    """
    if term_type == 'android':
        url = f"http://10.254.7.4:801/eportal/portal/login?callback=dr1005&login_method=1&user_account=%2C1%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Linux%3B%20Android%208.0.0%3B%20SM-G955U%20Build%2FR16NW)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Mobile%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=2&jsVersion=4.2&terminal_type=2&lang=zh-cn&v=9451&lang=zh"
    else:
        url = f"http://10.254.7.4:801/eportal/portal/login?callback=dr1004&login_method=1&user_account=%2C0%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=1&jsVersion=4.2&terminal_type=1&lang=zh-cn&v=9875&lang=zh"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            match = re.search(r'\(([\s\S]*?)\);', content)
            if match:
                result = json.loads(match.group(1))
                return result["result"], result["msg"]
            else:
                return 0, "未知错误"
    except Exception as e:
        return 0, f"网络错误: {e}"


def set_logger(log_level: str):
    global logger
    if log_level and log_level.lower() == "debug":
        level = logging.DEBUG
    else:
        level = logging.INFO
    logger = logging.getLogger()
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def parse_args():
    global logger
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=str, default=os.getenv("ACCOUNT", ""), help="校园网账户(学/工号)")
    parser.add_argument("--password", type=str, default=os.getenv("PASSWORD", ""), help="校园网密码")
    parser.add_argument("--term_type", type=str, default=os.getenv("TERM_TYPE", "pc"), choices=["android", "pc"], help="登录设备类型")
    parser.add_argument("--log_level", type=str, default=os.getenv("LOG_LEVEL", "info"), choices=["debug", "info"], help="日志级别")
    parser.add_argument("--interval", type=int, default=os.getenv("INTERVAL", 5), help="检查网络状态的间隔时间(秒)")
    parser.add_argument("--check_with_http", type=bool, default=os.getenv("CHECK_WITH_HTTP", False), help="是否使用 HTTP 连接的的结果检查网络状态，默认为 False")
    parser.add_argument(
        "--http_url", type=str, 
        default=os.getenv("HTTP_URL", "https://www.baidu.com"), 
        help="使用 HTTP 检查网络状态时访问的 URL, 仅在 --check_with_http 为 true 时有效"
    )
    args = parser.parse_args()
    
    # 验证参数
    if not args.account or not args.password:
        logger.error("未指定校园网账户或密码")
        sys.exit(-1)
    
    if args.term_type not in ["android", "pc"]:
        logger.error("登录设备类型必须为 android 或 pc")
        sys.exit(-1)
    
    return args.account, args.password, args.term_type, args.log_level, args.interval, args.check_with_http, args.http_url


def main():
    global logger
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

    account, password, term_type, log_level, interval, check_with_http, http_url = parse_args()

    set_logger(log_level)

    logger.info(f"每{interval}秒检查一次网络状态, 如果掉线则重新认证, CTRL+C 停止程序")
    while True:
        # 如果网络已经认证, 则不再重复认证
        connected = False
        if check_with_http:
            connected = is_http_connected(http_url)
        else:  
            connected=is_internet_connected()

        if connected:
            logger.debug(f"该网络已认证, 认证账户: {get_account()}, {interval}秒后重新检查网络状态...")
            time.sleep(interval)
            continue

        # 获取待认证的校园网 IP, 如果获取失败则等待 interval 秒后重试
        ip = get_ip()
        if not ip:
            logger.warning(f"认证失败: 无法获取校园网 IP, 请检查 DHCP 是否正常, {interval}秒后重试...")
            time.sleep(interval)
            continue

        # 认证校园网
        logger.info(f"正在认证: 账户({account}), 设备类型({term_type}), 校园网IP({ip})")
        result, msg = login(account, password, term_type, ip)
        
        # 如果失败原因为账号不存在或密码错误, 则直接退出程序
        if not result and msg in ["账号不存在", "密码错误"]:
            logger.warning(f"认证失败: {msg}")
            sys.exit(-1)
        elif not result:
            logger.warning(f"认证失败: {msg}, {interval}秒后重试...")
        else:
            logger.info(f"认证成功: {get_account()}, {interval}秒后重新检查网络状态...")
        time.sleep(interval)


if __name__ == "__main__":
    main()
