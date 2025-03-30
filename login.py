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
            result = json.loads(content.strip().strip("dr1004();"))
            return result["result"], result["msg"]
    except urllib.error.URLError:
        return 0, "网络错误"


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
    args = parser.parse_args()
    
    # 验证参数
    if not args.account or not args.password:
        logger.error("未指定校园网账户或密码")
        sys.exit(-1)
    
    if args.term_type not in ["android", "pc"]:
        logger.error("登录设备类型必须为 android 或 pc")
        sys.exit(-1)
    
    return args.account, args.password, args.term_type, args.log_level, args.interval


def main():
    global logger
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

    account, password, term_type, log_level, interval = parse_args()

    set_logger(log_level)

    logger.info(f"每{interval}秒检查一次网络状态, 如果掉线则重新认证, CTRL+C 停止程序")
    while True:
        # 如果网络已经认证, 则不再重复认证
        if is_internet_connected():
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
