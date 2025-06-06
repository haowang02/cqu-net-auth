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
import http.client

logger = None
ANDROID_AUTH_URL = "http://10.254.7.4:801/eportal/portal/login?callback=dr1005&login_method=1&user_account=%2C1%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Linux%3B%20Android%208.0.0%3B%20SM-G955U%20Build%2FR16NW)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Mobile%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=2&jsVersion=4.2&terminal_type=2&lang=zh-cn&v=9451&lang=zh"
PC_AUTH_URL = "http://10.254.7.4:801/eportal/portal/login?callback=dr1004&login_method=1&user_account=%2C0%2C{account}&user_password={password}&wlan_user_ip={ip}&wlan_user_ipv6=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&ua=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F134.0.0.0%20Safari%2F537.36%20Edg%2F134.0.0.0&term_type=1&jsVersion=4.2&terminal_type=1&lang=zh-cn&v=9875&lang=zh"
AUTH_INFO_URL = "http://10.254.7.4/drcom/chkstatus?callback=dr1002&jsVersion=4.X&v=5505&lang=zh"
UNBIND_URL = "http://10.254.7.4:801/eportal/portal/mac/unbind?callback=dr1002&user_account={account}&wlan_user_mac=000000000000&wlan_user_ip={int_ip}&jsVersion=4.2&v=6024&lang=zh"
LOGOUT_URL = "http://10.254.7.4:801/eportal/portal/logout"


class IfaceHTTPConnection(http.client.HTTPConnection):
    """使用 setsockopt 的 SO_BINDTODEVICE 选项限制从指定的网络接口建立连接"""
    
    def __init__(
        self, host, port=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None, blocksize=8192, source_interface=None
    ):
        super().__init__(
            host, port, timeout=timeout, 
            source_address=source_address, blocksize=blocksize
        )
        self.source_interface: str = source_interface
        self._create_connection = self.create_connection

    # this function is copied from socket.py 
    # since we need to alter its behavior
    def create_connection(
        self, address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None, *, all_errors=False
    ):

        host, port = address
        exceptions = []
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                    sock.settimeout(timeout)
                if self.source_interface:
                    # 使用 SO_BINDTODEVICE 选项绑定到指定的网络接口
                    sock.setsockopt(
                        socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 
                        (self.source_interface+"\0").encode('utf-8')
                    )
                elif source_address:
                    sock.bind(source_address)
                sock.connect(sa)
                # Break explicitly a reference cycle
                exceptions.clear()
                return sock

            except OSError as exc:
                if not all_errors:
                    exceptions.clear()  # raise only the last error
                exceptions.append(exc)
                if sock is not None:
                    sock.close()

        if len(exceptions):
            try:
                if not all_errors:
                    raise exceptions[0]
                raise ExceptionGroup("create_connection failed", exceptions)
            finally:
                # Break explicitly a reference cycle
                exceptions.clear()
        else:
            raise OSError("getaddrinfo returns an empty list")
        
class SourceInterfaceHandler(urllib.request.HTTPHandler):
    """自定义HTTP处理器，用于设置请求的源接口"""
    def __init__(self, source_interface=None):
        self.source_interface = source_interface
        super().__init__()
    
    def http_open(self, req):
        return self.do_open(IfaceHTTPConnection, req, source_interface=self.source_interface)

class SourceAddressHandler(urllib.request.HTTPHandler):
    """自定义HTTP处理器，用于设置请求的源地址"""
    def __init__(self, source_address=None):
        self.source_address = source_address
        super().__init__()

    def http_open(self, req):
        return self.do_open(http.client.HTTPConnection, req, source_address=self.source_address)


def get_interface_ip(interface):
    """使用fcntl获取指定网络接口的IPv4地址"""
    import fcntl
    import struct
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(interface[:15], 'utf-8'))
        )[20:24])
    except Exception as e:
        logger.debug(f"获取接口 {interface} 的IP地址失败: {e}")
        return None


def create_and_install_opener(interface=None, source_address=None):
    """创建并安装自定义opener以设置源地址"""
    if interface:
        opener = urllib.request.build_opener(SourceInterfaceHandler(source_interface=interface))
    elif source_address:
        opener = urllib.request.build_opener(SourceAddressHandler((source_address, 0)))
    # 未指定 interface 和 address 时使用默认的 opener，不需要额外操作
    else:
        return 
    
    urllib.request.install_opener(opener)


def is_internet_connected(host="223.6.6.6", port=53, timeout=3, interface=None):
    """通过 socket 检查是否连接到互联网"""
    # 动态获取接口IP
    interface_ip = None
    if interface:
        interface_ip = get_interface_ip(interface)
        if not interface_ip:
            logger.debug(f"无法获取接口 {interface} 的IP地址，将使用系统默认接口")
    
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if interface_ip:
            conn.bind((interface_ip, 0))  # 绑定到指定接口
        conn.settimeout(timeout)
        conn.connect((host, port))
        conn.close()
        return True
    except Exception as e:
        logger.debug(f"Socket连接失败: {e}")
        return False


def is_http_connected(url="https://www.baidu.com", timeout=3, interface=None):
    """通过 http 检查是否连接到互联网"""
    create_and_install_opener(interface=interface)
    req = urllib.request.Request(url, method='HEAD')
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
        if response.getcode() == 200:
            return True
    except Exception as e:
        logger.debug(f"HTTP连接失败: {e}")
        return False


def check_internet(method="socket", interface=None, **kwargs):
    """检查互联网连接状态"""
    if method == "socket":
        return is_internet_connected(interface=interface, **kwargs)
    elif method == "http":
        return is_http_connected(interface=interface, **kwargs)
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


def get_auth_info(timeout=3, interface=None):
    """获取 IP, ACCOUNT 等信息"""
    create_and_install_opener(interface=interface)
    req = urllib.request.Request(AUTH_INFO_URL)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                return drcom_message_parser(response.read().decode('GB2312'))
            return None
    except Exception as e:
        return None


def login(account: str, password: str, term_type: str, ip: str, timeout=3, interface=None):
    """认证校园网"""
    create_and_install_opener(interface=interface)
    auth_url = ANDROID_AUTH_URL if term_type == "android" else PC_AUTH_URL
    req = urllib.request.Request(auth_url.format(account=account, password=password, ip=ip))
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


def old_logout(timeout=3, interface=None):
    """传统注销方式"""
    create_and_install_opener(interface=interface)
    req = urllib.request.Request(LOGOUT_URL)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200 and "Radius注销成功！" in response.read().decode('utf-8'):
                return True
            return False
    except Exception:
        return False


def logout(account, ip, timeout=3, interface=None):
    """注销当前认证账户"""
    create_and_install_opener(interface=interface)
    int_ip = int.from_bytes(socket.inet_aton(ip), 'big')
    url = UNBIND_URL.format(account=account, int_ip=int_ip)
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                result = drcom_message_parser(response.read().decode('utf-8'))
                if result and "解绑终端MAC成功！" in result.get("msg", ""):
                    return True
                elif result and "mac不存在" in result.get("msg", ""):
                    return old_logout(timeout=timeout, interface=interface)
                return False
            return False
    except Exception:
        return False


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
    parser.add_argument("--check_with_http", action='store_true', default=os.getenv("CHECK_WITH_HTTP", "False").lower() in ('true', 'yes', '1', 't', 'y'), help="使用 HTTP 连接的的结果检查网络状态，默认为 False")
    parser.add_argument("--http_url", type=str, default=os.getenv("HTTP_URL", "https://www.baidu.com"), help="使用 HTTP 检查网络状态时访问的 URL, 仅在 --check_with_http 为 true 时有效")
    parser.add_argument("--interface", type=str, default=os.getenv("INTERFACE", ""), help="指定使用的网络接口名称，如eth0、wlan0等")
    
    args = parser.parse_args()
    
    set_logger(args.log_level)
    
    if not args.account or not args.password:
        logger.error("未指定校园网账户或密码")
        sys.exit(-1)
    
    if args.term_type not in ["android", "pc"]:
        logger.error("登录设备类型必须为 android 或 pc")
        sys.exit(-1)
    
    if os.name == "nt" and args.interface:
        logger.error("Windows系统不支持指定网络接口")
        sys.exit(-1)
    
    return args.account, args.password, args.term_type, args.interval, args.check_with_http, args.http_url, args.interface


def main():
    global logger
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

    account, password, term_type, interval, check_with_http, http_url, interface = parse_args()
    
    if interface:
        logger.info(f"认证网络接口 {interface}")
    
    logger.info(f"每{interval}秒检查一次网络状态, 如果掉线则重新认证, CTRL+C 停止程序")
    
    check_method = "http" if check_with_http else "socket"
    check_params = {"url": http_url} if check_with_http else {}
    
    status = "init"  # init/auth/unauth/uncertain
    while True:
        # 如果是 auth 状态，则检查 Internet 连接, 绕过对认证服务器的访问
        if status == "auth" and check_internet(method=check_method, interface=interface, **check_params):
            logger.debug(f"网络连接正常, {interval}秒后重新检查网络状态...")
            time.sleep(interval)
            continue
        
        # 首先获取认证信息
        auth_info = get_auth_info(interface=interface)
        if not auth_info:
            logger.warning(f"无法连接认证服务器")
            ####################################
            ###### 这里可以添加 DHCP 重播逻辑 ######
            ####################################
            status = "uncertain"
            continue
        
        # 如果当前已认证, 且 uid 与 account 不一致, 则先注销当前认证账户
        if "uid" in auth_info and auth_info["uid"] != account:
            if logout(auth_info["uid"], auth_info["v46ip"], interface=interface):
                logger.info(f"已注销 {auth_info['uid']}")
                status = "unauth"
                continue
            else:
                logger.error(f"注销 {auth_info['uid']} 失败")
                status = "uncertain"
                continue
        
        # 如果当前已认证, 且 uid 与 account 一致, 则不需要重新认证
        if "uid" in auth_info:
            logger.debug(f"已认证 {auth_info['uid']}")
            status = "auth"
            continue
        
        # 执行认证
        result, msg = login(account, password, term_type, auth_info['v46ip'], interface=interface)
        if not result:
            status = "unauth"
            if msg in ["账号不存在", "密码错误"]:
                logger.error(f"认证失败 {account}({term_type}): {msg}")
                sys.exit(-1)
            elif "等待5分钟" in msg:
                logger.warning(f"触发共享上网检测, 等待 5 分钟...")
                time.sleep(300)
                logger.info("等待结束")
            else:
                logger.warning(f"认证失败 {account}({term_type}): {msg}")
        else:
            status = "auth"
            logger.info(f"认证成功 {account}({term_type})")


if __name__ == "__main__":
    main()
