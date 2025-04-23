import re
import json
import socket
import urllib.request

AUTH_INFO_URL = "http://10.254.7.4/drcom/chkstatus?callback=dr1002&jsVersion=4.X&v=5505&lang=zh"
UNBIND_URL = "http://10.254.7.4:801/eportal/portal/mac/unbind?callback=dr1002&user_account={account}&wlan_user_mac=000000000000&wlan_user_ip={int_ip}&jsVersion=4.2&v=6024&lang=zh"
CHECK_LOGOUT_URL = "http://10.254.7.4:801/eportal/portal/Custom/checkLogout?callback=dr1003&ip={ip}&jsVersion=4.2&v=8573&lang=zh"
LOGOUT_URL = "http://10.254.7.4:801/eportal/portal/logout"


def ip_to_int(ip):
    """
    Convert an IP address to an integer.
    """
    return int.from_bytes(socket.inet_aton(ip), 'big')


def drcom_message_parser(drcom_message):
    """将形如 `dr1004(...);` 或 `dr1002(...)` 的内容解析为 dict"""
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


def unbind(account, int_ip, timeout=3):
    """解绑终端 MAC
    响应: dr1002({"result":1,"msg":"解绑终端MAC成功！"});
    """
    url = UNBIND_URL.format(account=account, int_ip=int_ip)
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                return drcom_message_parser(response.read().decode('utf-8'))
            return None
    except Exception:
        return None


def check_logout(ip, timeout=3):
    """检查注销状态
    响应: dr1003({"code":0,"oauth_logout_url":"","msg":"获取统一注销地址成功"});
    """
    url = CHECK_LOGOUT_URL.format(ip=ip)
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                return drcom_message_parser(response.read().decode('utf-8'))
            return None
    except Exception:
        return None


def old_logout(timeout=3):
    """传统注销方式"""
    req = urllib.request.Request(LOGOUT_URL)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200 and "Radius注销成功！" in response.read().decode('utf-8'):
                return True, "Radius注销成功！"
            return False, "注销失败"
    except Exception:
        return False, "注销失败"


def logout():
    """注销校园网认证"""
    auth_info = get_auth_info()
    if not auth_info:
        return False, "获取认证信息失败"
    if "uid" not in auth_info:
        return False, "未认证账户"
    ip = auth_info["v46ip"]
    int_ip = ip_to_int(ip)
    account = auth_info["uid"]
    unbind_result = unbind(account, int_ip)
    if unbind_result and "解绑终端MAC成功！" in unbind_result.get("msg", ""):
        return True, "解绑终端MAC成功！"
    elif unbind_result and "mac不存在" in unbind_result.get("msg", ""):
        return old_logout()
    return True, "注销成功"


if __name__ == "__main__":
    success, message = logout()
    print(message)
