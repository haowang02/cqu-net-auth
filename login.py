import os
import re
import sys
import time
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
            match = re.search(r"v46ip='([^']+)'", html)
            if match:
                v46ip = match.group(1)
                return v46ip
            else:
                return None
    except urllib.error.URLError:
        return None


def is_internet_connected(host="223.6.6.6", port=53, timeout=1, max_retries=3):
    """检查是否连接到互联网"""
    retries = 0
    while retries < max_retries:
        try:
            conn = socket.create_connection((host, port), timeout=timeout)
            conn.close()
            return True
        except Exception as e:
            retries += 1
    return False


def get_account():
    """获取当前认证的账户"""
    try:
        with urllib.request.urlopen('http://10.254.7.4/', timeout=5) as response:
            html = response.read().decode('GB2312')
            html = [i.strip() for i in html.split(";")]
            uid_list = list(filter(lambda x: x.startswith("uid="), html))
            nid_list = list(filter(lambda x: x.startswith("NID="), html))
            if len(uid_list) <= 0 or len(nid_list) <= 0:
                return None
            id = uid_list[0].split("\'")[1]
            name = nid_list[0].split("\'")[1]
            return f"{name}({id})"
    except urllib.error.URLError:
        return None


def login(account: str, password: str, term_type: str, ip: str):
    """认证校园网"""
    if term_type == 'android':
        url = f"http://10.254.7.4:801/eportal/portal/login?callback=dr1005&login_method=1&user_account=%2C1%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Linux%3B%20Android%208.0.0%3B%20SM-G955U%20Build%2FR16NW)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Mobile%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=2&jsVersion=4.2&terminal_type=2&lang=zh-cn&v=9451&lang=zh"
    else:
        url = f"http://10.254.7.4:801/eportal/portal/login?callback=dr1004&login_method=1&user_account=%2C0%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=1&jsVersion=4.2&terminal_type=1&lang=zh-cn&v=9875&lang=zh"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            if "Portal协议认证成功！" in content:
                return True, content
            else:
                return False, content
    except urllib.error.URLError:
        return False, None


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


def signal_handler(signum, frame):
    """
    信号处理函数，处理 SIGTERM/SIGINT 信号
    """
    global logger
    logger.info(f"Received signal {signum}, exiting...")
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=str, default=os.getenv("ACCOUNT", ""), help="校园网账户(学/工号)")
    parser.add_argument("--password", type=str, default=os.getenv("PASSWORD", ""), help="校园网密码")
    parser.add_argument("--term_type", type=str, default=os.getenv("TERM_TYPE", "pc"), choices=["android", "pc"], help="登录设备类型")
    parser.add_argument("--log_level", type=str, default=os.getenv("LOG_LEVEL", "info"), choices=["debug", "info"], help="日志级别")
    args = parser.parse_args()
    return args.account, args.password, args.term_type, args.log_level


def main():
    global logger
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    account, password, term_type, log_level = parse_args()

    set_logger(log_level)

    if not account or not password:
        logger.error("未指定校园网账户或密码")
        sys.exit(-1)

    if term_type not in ["android", "pc"]:
        logger.error("登录设备类型必须为 android 或 pc")
        sys.exit(-1)

    # 每5秒检查一次网络状态, 如果掉线则重新认证
    interval = 5

    first = True
    try:
        while True:
            if not is_internet_connected():
                ip = get_ip()
                if not ip:
                    logger.warning("获取IP失败, 请检查 DHCP 是否正常")
                    continue
                logger.info(f"正在认证: 账户({account}), 设备类型({term_type}), 设备IP({ip})")
                success, response = login(account, password, term_type, ip)
                if not success:
                    logger.warning(f"认证失败: {response}, {interval}秒后重试...")
                else:
                    logger.info(f"认证成功: {get_account()}")
            else:
                logger.debug(f"该网络已认证, 认证账户: {get_account()}")
            if first:
                first = False
                logger.info(f"每{interval}秒检查一次网络状态, 如果掉线则重新认证")
                logger.info(f"如果需要停止程序, 请使用 Ctrl+C 停止")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received (Ctrl+C), exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
