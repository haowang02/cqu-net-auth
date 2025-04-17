import os
import re
import sys
import time
import json
import signal
import socket
import logging
import urllib.request
import argparse

logger = None
ANDROID_AUTH_URL = "http://10.254.7.4:801/eportal/portal/login?callback=dr1005&login_method=1&user_account=%2C1%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Linux%3B%20Android%208.0.0%3B%20SM-G955U%20Build%2FR16NW)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Mobile%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=2&jsVersion=4.2&terminal_type=2&lang=zh-cn&v=9451&lang=zh"
PC_AUTH_URL = "http://10.254.7.4:801/eportal/portal/login?callback=dr1004&login_method=1&user_account=%2C0%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=1&jsVersion=4.2&terminal_type=1&lang=zh-cn&v=9875&lang=zh"
AUTH_INFO_URL = "http://10.254.7.4/drcom/chkstatus?callback=dr1002&jsVersion=4.X&v=5505&lang=zh"


def is_internet_connected(host="223.6.6.6", port=53, timeout=3):
    """通过 socket 检查是否连接到互联网"""
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except Exception as e:
        return False


def is_http_connected(url="https://www.baidu.com", timeout=3):
    """通过 http 检查是否连接到互联网"""
    try:
        response = urllib.request.urlopen(url, timeout=timeout)
        if response.getcode() == 200:
            return True
    except Exception:
        return False


def check_internet(method="socket", **kwargs):
    """检查互联网连接状态"""
    if method == "socket":
        return is_internet_connected(**kwargs)
    elif method == "http":
        return is_http_connected(**kwargs)
    else:
        raise ValueError("method must be 'socket' or 'http'")


def drcom_message_parser(drcom_message):
    """将形如 `dr1004(...);` 或 `dr1002(...)` 的内容解析为 dict"""
    if isinstance(drcom_message, bytes):
        drcom_message = drcom_message.decode('GB2312')
    
    match = re.search(r'dr\d+\((.*?)\);?', drcom_message)
    if match:
        json_str = match.group(1)
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError:
            return None
    else:
        return None


def get_auth_info(timeout=3):
    """获取 IP, ACCOUNT 等信息"""
    req = urllib.request.Request(AUTH_INFO_URL)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                return drcom_message_parser(response.read().decode('GB2312'))
            return None
    except Exception:
        return None


def login(account: str, password: str, term_type: str, ip: str, timeout=3):
    """认证校园网
    dr1004({"result":1,"msg":"Portal协议认证成功！"});
    dr1004({"result":0,"msg":"账号不存在","ret_code":1});
    dr1004({"result":0,"msg":"密码错误","ret_code":1});
    dr1004({"result":0,"msg":"认证操作非本机终端！","ret_code":"1"});
    dr1004({"result":0,"msg":"认证出现异常！","ret_code":"1"});
    dr1004({"result":0,"msg":"IP: x.x.x.x 已经在线！","ret_code":"1"});
    """
    if term_type == 'android':
        url = ANDROID_AUTH_URL
    else:
        url = PC_AUTH_URL
    req = urllib.request.Request(url.format(account=account, password=password, ip=ip))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() != 200:
                return 0, "认证服务器异常"
            result = drcom_message_parser(response.read().decode('utf-8'))
            if result:
                return result.get("result", 0), result.get("msg", "未知错误")
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
    
    check_method = "http" if check_with_http else "socket"
    check_params = {"url": http_url} if check_with_http else {}
    
    while True:
        # 首先获取认证信息
        auth_info = get_auth_info()
        if not auth_info:
            logger.warning(f"无法获取校园网 IP, 请检查链路是否正常, {interval}秒后重试...")
            time.sleep(interval)
            continue
        
        # 检查互联网连接状态, 如果 auth_info["NID"] 不存在则表示未认证, 可以跳过互联网连接检查
        if "NID" in auth_info and check_internet(method=check_method, **check_params):
            logger.debug(f"网络连接正常, 已认证账户[{auth_info['NID']} {auth_info['uid']}], {interval}秒后重新检查网络状态...")
            time.sleep(interval)
            continue
        
        # 执行认证
        logger.info(f"正在认证: 账户({account}), 设备类型({term_type}), 校园网IP({auth_info['v46ip']})")
        result, msg = login(account, password, term_type, auth_info['v46ip'])
        
        # 处理认证结果
        if not result:
            if msg in ["账号不存在", "密码错误"]:
                logger.error(f"认证失败: {msg}")
                sys.exit(-1)
            else:
                logger.warning(f"认证失败: {msg}, {interval}秒后重试...")
        else:
            logger.info(f"认证成功, {interval}秒后重新检查网络状态...")
        time.sleep(interval)


if __name__ == "__main__":
    main()
