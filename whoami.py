import re
import json
import urllib.request

AUTH_INFO_URL = "http://login.cqu.edu.cn/drcom/chkstatus?callback=dr1002&jsVersion=4.X&v=5505&lang=zh"


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
    except Exception as e:
        return None


def main():
    auth_info = get_auth_info()
    if auth_info:
        if auth_info.get('uid'):
            print(f"{auth_info['v46ip']} {auth_info.get('uid', '')}({auth_info.get('NID', '')})")
        else:
            print(f"{auth_info['v46ip']} 未认证")
    else:
        print("获取认证信息失败")


if __name__ == "__main__":
    main()
