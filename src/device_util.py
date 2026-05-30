"""设备标识：MT-R 生成；可选反检测随机化（合并龙蒙超版）。"""

import base64
import hashlib
import os
import random
import uuid

# 社区常用固定值（与早期开源脚本一致，random_mt_info=false 时使用）
DEFAULT_MT_INFO = "028e7f96f6369cafe1d105579c5b9377"

_IOS_UA_POOL = [
    "iOS;16.1;Apple;iPhone14,7",
    "iOS;16.3;Apple;iPhone14,7",
    "iOS;16.6;Apple;iPhone15,2",
    "iOS;16.5;Apple;iPhone15,3",
    "iOS;17.0;Apple;iPhone15,2",
    "iOS;17.1;Apple;iPhone15,3",
    "iOS;17.3;Apple;iPhone15,2",
    "iOS;17.4;Apple;iPhone15,4",
    "iOS;17.0;Apple;iPhone16,1",
    "iOS;17.2;Apple;iPhone16,2",
    "iOS;17.3;Apple;iPhone16,1",
    "iOS;17.5;Apple;iPhone16,2",
    "iOS;17.6;Apple;iPhone16,1",
    "iOS;18.0;Apple;iPhone17,1",
    "iOS;18.1;Apple;iPhone17,2",
    "iOS;18.2;Apple;iPhone17,3",
    "iOS;18.3;Apple;iPhone17,1",
    "iOS;18.0;Apple;iPhone16,2",
    "iOS;18.1;Apple;iPhone16,1",
    "iOS;17.7;Apple;iPhone16,2",
]

_NETWORK_TYPES = ["WIFI", "WIFI", "WIFI", "4G", "4G", "5G"]


def random_ua() -> str:
    return random.choice(_IOS_UA_POOL)


def random_network_type() -> str:
    return random.choice(_NETWORK_TYPES)


def generate_mt_info() -> str:
    return hashlib.md5(os.urandom(16)).hexdigest()


def profile_from_device_id(device_id: str) -> tuple[str, str, str]:
    """
    由 device_id 确定性生成 UA / MT-Info / 网络类型。
    同一账号长期稳定，不同账号各不相同（优于每会话随机）。
    """
    seed = hashlib.sha256(device_id.strip().upper().encode()).digest()
    ua = _IOS_UA_POOL[seed[0] % len(_IOS_UA_POOL)]
    network = _NETWORK_TYPES[seed[1] % len(_NETWORK_TYPES)]
    mt_info = hashlib.md5(seed[2:18]).hexdigest()
    return ua, mt_info, network


def make_mt_r(device_id: str) -> str:
    buf: list[str] = []
    xor_val = 72
    for ch in device_id:
        xor_val ^= ord(ch)
        buf.append(chr(xor_val))
    raw = "".join(buf)
    return "clips_" + base64.b64encode(raw.encode("latin-1")).decode("ascii")


def make_request_id() -> str:
    return str(uuid.uuid4())


def normalize_device_id(device_id: str) -> str:
    device_id = device_id.strip().upper()
    if not device_id:
        return str(uuid.uuid4()).upper()
    return device_id
