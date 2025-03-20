import os
import requests
import logging
import time
import socket


def is_internet_connected(host="223.6.6.6", port=53, timeout=1, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            # 创建一个套接字对象并尝试连接到指定的主机和端口
            conn = socket.create_connection((host, port), timeout=timeout)
            conn.close()
            return True
        except Exception as e:
            retries += 1
    return False


def login(username: str, password: str, type: str, ip: str):
    """认证校园网"""
    if type == 'android':
        url = f"http://10.254.7.4:801/eportal/portal/login?callback=dr1005&login_method=1&user_account=%2C1%2C{username}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Linux%3B%20Android%208.0.0%3B%20SM-G955U%20Build%2FR16NW)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Mobile%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=2&jsVersion=4.2&terminal_type=2&lang=zh-cn&v=9451&lang=zh"
    else:
        url = f"http://10.254.7.4:801/eportal/portal/login?callback=dr1004&login_method=1&user_account=%2C0%2C{username}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=1&jsVersion=4.2&terminal_type=1&lang=zh-cn&v=9875&lang=zh"
    try:
        response = requests.get(url, headers={
            "Host": "10.254.7.4:801",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
            "Accept": "*/*"
        })
        if "Portal协议认证成功！" in response.text:
            return True
        else:
            return False
    except:
        return False


def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def main():
    # 从环境变量中获取认证所需信息
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    type = os.getenv("TYPE")
    ip = os.getenv("IP")

    logger = set_logger()
    if not username or not password or not type or not ip:
        logger.error("请通过环境变量指定用户名、密码、登录设备类型和登录设备IP")
        exit(-1)

    # 初次认证
    if not login(username, password, type=type, ip=ip):
        logger.error("认证失败，请检查用户名和密码是否正确")
        exit(-1)
    else:
        logger.info("认证成功")

    # 每5秒检查一次网络状态，如果掉线则重新认证
    interval = 5
    try:
        while True:
            if not is_internet_connected():
                logger.info("网络已断开，即将重新认证...")
                if not login(username, password, type=type, ip=ip):
                    logger.error(f"未知原因导致认证失败，{interval}秒后重试")
                else:
                    logger.info("认证成功")
            else:
                logger.info("该网络已认证")
            time.sleep(interval)
    except:
        exit(0)


if __name__ == "__main__":
    main()
