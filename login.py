import os
import signal
import requests
import logging
import time
import socket
import sys


logger = None


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


def get_username():
    """获取当前认证的用户名"""
    try:
        resp = requests.get("http://10.254.7.4/")
        if resp.status_code != 200:
            return None
    except:
        return None
    html = resp.content.decode("GB2312")
    html = [i.strip() for i in html.split(";")]
    uid_list = list(filter(lambda x: x.startswith("uid="), html))
    nid_list = list(filter(lambda x: x.startswith("NID="), html))
    if len(uid_list) <= 0 or len(nid_list) <= 0:
        return None
    id = uid_list[0].split("\'")[1]
    name = nid_list[0].split("\'")[1]
    return f"{name}({id})"


def login(username: str, password: str, term_type: str, ip: str):
    """认证校园网"""
    if term_type == 'android':
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
            return True, response.text
        else:
            return False, response.text
    except:
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
    信号处理函数，处理 SIGTERM 信号
    """
    global logger
    logger.info(f"Received signal {signum}, exiting...")
    sys.exit(0)


def main():
    global logger
    signal.signal(signal.SIGTERM, signal_handler)
    # 从环境变量中获取认证所需信息
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    term_type = os.getenv("TERM_TYPE")
    ip = os.getenv("IP")
    log_level = os.getenv("LOG_LEVEL")
    
    set_logger(log_level)
    
    if not username or not password or not term_type or not ip:
        logger.error("请通过环境变量指定用户名、密码、登录设备类型和登录设备IP")
        sys.exit(-1)
    
    if term_type not in ["android", "pc"]:
        logger.error("登录设备类型必须为 android 或 pc")
        sys.exit(-1)
    
    # 每5秒检查一次网络状态，如果掉线则重新认证
    interval = 5

    # 初次认证
    logger.info(f"开始认证: 账户({username}), 设备类型({term_type}), 设备IP({ip})")
    success, response = login(username, password, term_type, ip)
    if not success:
        logger.error(f"认证失败: {response}")
        sys.exit(-1)
    logger.info(f"认证成功: {get_username()}")
    logger.info(f"开始每{interval}秒检查一次网络状态，如果掉线则重新认证")
    logger.info(f"如果需要停止程序，请使用 Ctrl+C 停止")
    
    try:
        while True:
            time.sleep(interval)
            if not is_internet_connected():
                logger.info(f"网络已断开，重新认证: 账户({username}), 设备类型({term_type}), 设备IP({ip})")
                success, response = login(username, password, term_type, ip)
                if not success:
                    logger.warning(f"认证失败: {response}, {interval}秒后重试...")
                else:
                    logger.info(f"认证成功: {get_username()}")
            else:
                logger.debug("该网络已认证")
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received (Ctrl+C), exiting...")
        sys.exit(0) 


if __name__ == "__main__":
    main()
