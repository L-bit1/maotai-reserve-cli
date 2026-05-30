"""i茅台 App API 客户端。"""

from __future__ import annotations

import datetime
import json
import logging
import random
import time
import uuid
from typing import Any

import requests

from .config_loader import AccountCredentials, AntidetectConfig, mask_mobile
from .crypto import ActParamEncryptor, request_signature
from .device_util import make_mt_r, make_request_id, normalize_device_id, random_ua
from .exceptions import AuthError, RateLimitError, SessionNotReadyError
from .proxy_util import build_requests_proxies, mask_proxy_url, resolve_account_proxy
from .risk_control import (
    DeviceProfile,
    get_throttle,
    is_rate_limited_status,
    resolve_device_profile,
    throttle_key,
)

logger = logging.getLogger(__name__)

APP_HOST = "app.moutai519.com.cn"
STATIC_HOST = "static.moutai519.com.cn"
H5_HOST = "h5.moutai519.com.cn"

_encryptor = ActParamEncryptor()


def fetch_app_version() -> str:
    try:
        r = requests.get(
            "https://itunes.apple.com/cn/lookup?id=1600482450",
            timeout=15,
        )
        return r.json()["results"][0]["version"]
    except Exception as e:
        logger.warning("无法从 App Store 获取版本号，使用默认 1.8.0: %s", e)
        return "1.9.6"  # 与 base.apk 逆向版本一致，抓包失败时的兜底


class IMaotaiClient:
    def __init__(
        self,
        account: AccountCredentials,
        app_version: str | None = None,
        *,
        proxy_pools: dict[str, str] | None = None,
        antidetect: AntidetectConfig | None = None,
    ):
        self.account = account
        self.app_version = app_version or fetch_app_version()
        self.antidetect = antidetect or AntidetectConfig(enabled=False)
        self._profile: DeviceProfile = resolve_device_profile(account, self.antidetect)
        self._throttle_key = throttle_key(account.mobile, account.egress_group)
        self._throttle = get_throttle()
        self.session_id: str | None = None
        self._session = requests.Session()
        self._proxy_url = resolve_account_proxy(
            account.proxy_url,
            account.egress_group,
            proxy_pools or {},
        )
        proxies = build_requests_proxies(self._proxy_url)
        if proxies:
            self._session.proxies.update(proxies)
            logger.info(
                "%s 出口 [%s] 代理 %s",
                mask_mobile(account.mobile),
                account.egress_group or "-",
                mask_proxy_url(self._proxy_url),
            )
        self._init_headers()

    def _init_headers(self) -> None:
        device = normalize_device_id(self.account.device_id)
        self.account.device_id = device
        try:
            mt_r = make_mt_r(device)
        except Exception:
            mt_r = "clips_OlU6TmFRag5rCXwbNAQ/Tz1SKlN8THcecBp/HGhHdw=="

        p = self._profile
        self._headers = {
            "Host": APP_HOST,
            "Accept": "*/*",
            "MT-User-Tag": "0",
            "MT-Network-Type": p.network_type,
            "MT-Token": self.account.token or "",
            "MT-Team-ID": "",
            "MT-Info": p.mt_info,
            "MT-Device-ID": device,
            "MT-Bundle-ID": "com.moutai.mall",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9",
            "MT-APP-Version": self.app_version,
            "User-Agent": p.ua,
            "MT-R": mt_r,
            "Content-Type": "application/json; charset=UTF-8",
            "Connection": "keep-alive",
            "userId": str(self.account.user_id or "0"),
            "MT-Lat": self.account.lat,
            "MT-Lng": self.account.lng,
            "MT-Request-ID": make_request_id(),
        }

    def _auth_headers(self) -> dict[str, str]:
        """登录 / 发验证码：Token 必须为空，每次新 Request-ID。"""
        h = dict(self._headers)
        h["MT-Token"] = ""
        h["userId"] = "0"
        h["MT-Request-ID"] = make_request_id()
        return h

    def _pace_request(self) -> None:
        ad = self.antidetect
        if not ad.enabled:
            return
        self._throttle.pace(
            self._throttle_key,
            ad.request_delay_min,
            ad.request_delay_max,
        )

    def _static_headers(self) -> dict[str, str]:
        p = self._profile
        return {
            "User-Agent": p.ua,
            "Accept": "*/*",
            "Referer": f"https://{H5_HOST}/gux/game/main?appConfig=2_1_2",
            "MT-APP-Version": self.app_version,
            "mt-lat": self.account.lat,
            "mt-lng": self.account.lng,
            "MT-Device-ID": self.account.device_id,
        }

    def warmup(self) -> None:
        """模拟 App 打开后的浏览（龙蒙超版）；失败不阻断主流程。"""
        if not self.antidetect.enabled or not self.antidetect.warmup_before_reserve:
            return
        logger.info("%s 行为预热…", mask_mobile(self.account.mobile))
        h5_h = {
            **self._static_headers(),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        steps = [
            ("h5", f"https://{H5_HOST}/gux/game/main?appConfig=2_1_2", h5_h),
            ("info", f"https://{APP_HOST}/xhr/front/user/info", self._headers),
            (
                "session",
                f"https://{STATIC_HOST}/mt-backend/xhr/front/mall/index/session/get/"
                f"{int(time.mktime(datetime.date.today().timetuple()) * 1000)}",
                self._static_headers(),
            ),
            ("user2", f"https://{APP_HOST}/xhr/front/user/getUserInfo", self._headers),
        ]
        for _name, url, headers in steps:
            try:
                self._pace_request()
                self._session.get(url, headers=headers, timeout=10)
            except Exception:
                pass
            time.sleep(random.uniform(0.35, 1.1))

    @staticmethod
    def _parse_api_message(resp: requests.Response) -> str:
        try:
            body = resp.json()
            return str(body.get("message") or body.get("msg") or body)[:200]
        except Exception:
            return resp.text[:200]

    def _signed_post(
        self,
        path: str,
        params: dict[str, str],
        *,
        for_auth: bool = False,
    ) -> requests.Response:
        md5, ts = request_signature(params)
        body = {**params, "md5": md5, "timestamp": ts, "MT-APP-Version": self.app_version}
        url = f"https://{APP_HOST}{path}"
        if not for_auth:
            self._pace_request()
        else:
            self._throttle.assert_not_cooled(self._throttle_key)
        headers = self._auth_headers() if for_auth else self._headers
        headers["MT-Request-ID"] = make_request_id()
        return self._session.post(url, json=body, headers=headers, timeout=30)

    def send_vcode(self, mobile: str) -> tuple[bool, str]:
        ok, msg = self._throttle.can_send_vcode(
            mobile, self.antidetect.login_vcode_interval
        )
        if not ok:
            return False, msg
        resp = self._signed_post(
            "/xhr/front/user/register/vcode",
            {"mobile": mobile},
            for_auth=True,
        )
        body_preview = self._parse_api_message(resp)
        if is_rate_limited_status(resp.status_code, body_preview):
            self._throttle.set_cooldown(
                self._throttle_key,
                max(120.0, self.antidetect.reserve_429_cooldown),
                "发码429",
            )
            return False, "发送过于频繁(429)，请等待 2 分钟后再试"
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code} {body_preview}"
        try:
            j = resp.json()
            if j.get("code") not in (2000, 0, "2000", None) and j.get("code") is not None:
                return False, f"发送失败 code={j.get('code')} {j.get('message', '')}"
        except json.JSONDecodeError:
            pass
        self._throttle.record_vcode(mobile)
        return True, "验证码已发送，请查看短信（约 1 分钟内有效）"

    def login(self, mobile: str, vcode: str) -> tuple[str, str]:
        code = (vcode or "").strip()
        if len(code) < 4:
            raise AuthError("验证码不能为空，请输入短信里的 4–6 位数字")

        last_err = ""
        for attempt in range(3):
            resp = self._signed_post(
                "/xhr/front/user/register/login",
                {"mobile": mobile, "vCode": code, "ydToken": "", "ydLogId": ""},
                for_auth=True,
            )

            if is_rate_limited_status(resp.status_code, self._parse_api_message(resp)):
                self._throttle.set_cooldown(
                    self._throttle_key,
                    max(300.0, self.antidetect.reserve_429_cooldown * 2),
                    "登录429",
                )
                raise RateLimitError(
                    "登录请求过于频繁(429)。请勿立即重试，否则限流会加重。\n"
                    "建议：等待 5～15 分钟；勿重复发验证码；可换手机 4G 热点后再试。"
                )

            if resp.status_code != 200:
                raise AuthError(
                    f"HTTP {resp.status_code} {self._parse_api_message(resp)}"
                )

            try:
                j = resp.json()
            except json.JSONDecodeError:
                raise AuthError(f"响应无法解析: {resp.text[:120]}")

            api_code = j.get("code")
            if api_code not in (2000, 0, "2000") or not j.get("data"):
                msg = j.get("message") or j.get("msg") or str(j)
                raise AuthError(f"登录失败: {msg}")

            data = j["data"]
            token, user_id = data["token"], str(data["userId"])
            self.account.token = token
            self.account.user_id = user_id
            self._headers["MT-Token"] = token
            self._headers["userId"] = user_id
            return token, user_id

        raise RateLimitError(last_err or "登录失败")

    def refresh_session_id(self) -> str:
        day_ms = int(
            time.mktime(datetime.date.today().timetuple()) * 1000
        )
        url = f"https://{STATIC_HOST}/mt-backend/xhr/front/mall/index/session/get/{day_ms}"
        resp = self._session.get(url, timeout=30)
        resp.raise_for_status()
        self.session_id = str(resp.json()["data"]["sessionId"])
        return self.session_id

    def is_session_ready(self) -> bool:
        sid = self.session_id or self.refresh_session_id()
        return bool(sid) and sid != "0"

    def ensure_session_id(
        self,
        max_wait_seconds: int = 120,
        poll_interval: int = 5,
    ) -> str:
        """等待有效 sessionId；仍为 0 则抛出 SessionNotReadyError。"""
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            sid = self.refresh_session_id()
            if sid and sid != "0":
                logger.info("场次 sessionId=%s", sid)
                return sid
            wait = poll_interval
            if self.antidetect.enabled:
                wait = max(2.0, poll_interval + poll_interval * random.uniform(-0.4, 0.4))
            logger.info(
                "sessionId=0（非申购时段或未开放），%.1fs 后重试…",
                wait,
            )
            time.sleep(wait)
        raise SessionNotReadyError(
            f"在 {max_wait_seconds}s 内未获取到有效 sessionId。"
            "请确认当前为申购时段（通常 9:00–10:00）或稍后重试。"
        )

    def validate_token(self) -> tuple[bool, str]:
        """检查 MT-Token 是否仍有效。"""
        paths = (
            "/xhr/front/user/info",
            "/xhr/front/user/getUserInfo",
        )
        for path in paths:
            url = f"https://{APP_HOST}{path}"
            try:
                resp = self._session.get(url, headers=self._headers, timeout=15)
            except requests.RequestException as e:
                return False, f"网络异常: {e}"

            if resp.status_code == 401:
                return False, "Token 已失效 (HTTP 401)"

            if resp.status_code != 200:
                continue

            try:
                body = resp.json()
            except json.JSONDecodeError:
                return True, "Token 有效"

            code = body.get("code")
            if code in (2000, 0, "2000"):
                return True, "Token 有效"
            if code in (401, 4001, 4030):
                return False, f"Token 无效 code={code}"
            if body.get("data"):
                return True, "Token 有效"

        # 接口路径变更时：有 token 且非空则放行，由预约接口最终校验
        if self.account.token and len(self.account.token) > 10:
            return True, "Token 未校验（接口无响应），将尝试预约"
        return False, "Token 为空"

    def fetch_shop_map(self) -> tuple[dict, dict]:
        """返回 (省市区->门店ID列表, shopId->门店详情)。"""
        self._pace_request()
        url = f"https://{STATIC_HOST}/mt-backend/xhr/front/mall/resource/get"
        res = self._session.get(url, headers=self._static_headers(), timeout=30).json()
        shops_url = res["data"]["mtshops_pc"]["url"]
        shops = self._session.get(shops_url, timeout=60).json()

        province_city_map: dict[str, dict[str, list[str]]] = {}
        for shop_id, info in shops.items():
            prov = info.get("provinceName", "")
            city = info.get("cityName", "")
            province_city_map.setdefault(prov, {}).setdefault(city, []).append(shop_id)
        return province_city_map, shops

    def fetch_session_shops(self, item_code: str) -> list[dict]:
        if not self.session_id:
            self.refresh_session_id()
        day_ms = int(time.mktime(datetime.date.today().timetuple()) * 1000)
        url = (
            f"https://{STATIC_HOST}/mt-backend/xhr/front/mall/shop/list/slim/v3/"
            f"{self.session_id}/{self.account.province}/{item_code}/{day_ms}"
        )
        self._pace_request()
        resp = self._session.get(url, headers=self._static_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("shops", [])

    def build_reserve_payload(self, shop_id: str, item_id: str) -> dict[str, Any]:
        inner = {
            "itemInfoList": [{"count": 1, "itemId": item_id}],
            "sessionId": int(self.session_id),
            "userId": self.account.user_id,
            "shopId": shop_id,
        }
        return {
            **inner,
            "actParam": _encryptor.encrypt(inner),
        }

    def preview_reserve(self, shop_id: str, item_id: str) -> dict[str, Any]:
        """dry-run：仅生成请求体，不提交。"""
        payload = self.build_reserve_payload(shop_id, item_id)
        public = {k: v for k, v in payload.items() if k != "actParam"}
        return {
            "shop_id": shop_id,
            "item_id": item_id,
            "session_id": self.session_id,
            "payload_keys": list(payload.keys()),
            "act_param_len": len(payload.get("actParam", "")),
            "act_param_preview": str(payload.get("actParam", ""))[:48] + "…",
            "body_preview": public,
        }

    def reserve(self, shop_id: str, item_id: str) -> tuple[bool, str]:
        can, quota_msg = self._throttle.can_reserve(
            self._throttle_key, self.antidetect.max_reserve_per_minute
        )
        if not can:
            return False, quota_msg
        self._pace_request()
        payload = self.build_reserve_payload(shop_id, item_id)
        payload.pop("userId", None)
        url = f"https://{APP_HOST}/xhr/front/mall/reservation/add"
        resp = self._session.post(url, json=payload, headers=self._headers, timeout=30)
        self._throttle.record_reserve(self._throttle_key)
        body = resp.text[:300]
        if is_rate_limited_status(resp.status_code, body):
            self._throttle.set_cooldown(
                self._throttle_key,
                self.antidetect.reserve_429_cooldown,
                "预约429",
            )
            return False, f"HTTP {resp.status_code} 触发限流，已冷却 {self.antidetect.reserve_429_cooldown:.0f}s"
        ok = False
        if resp.status_code == 200:
            try:
                j = resp.json()
                ok = j.get("code") == 2000 or j.get("success") is True
            except json.JSONDecodeError:
                ok = "成功" in body or "success" in body.lower()
        return ok, f"HTTP {resp.status_code} {body}"

    def claim_energy(self) -> str:
        cookies = {
            "MT-Device-ID-Wap": self.account.device_id,
            "MT-Token-Wap": self.account.token,
        }
        url = f"https://{H5_HOST}/game/isolationPage/getUserEnergyAward"
        resp = self._session.post(url, cookies=cookies, headers=self._headers, json={}, timeout=20)
        return f"{resp.status_code} {resp.text[:120]}"

    def _h5_game_headers(self, *, with_geo: bool = False) -> dict[str, str]:
        """H5 小游戏（旅行/耐力）请求头；Cookie 使用 MT-Token。"""
        token = self.account.token or ""
        device = self.account.device_id
        h = {
            "MT-Device-ID": device,
            "MT-APP-Version": self.app_version,
            "User-Agent": self._profile.ua,
            "Cookie": f"MT-Token-Wap={token};MT-Device-ID-Wap={device};",
        }
        if with_geo:
            h["MT-Lat"] = self.account.lat
            h["MT-Lng"] = self.account.lng
        return h

    def query_reservation_results(self) -> list[dict[str, Any]]:
        """查询申购记录（含中签状态）。"""
        self._pace_request()
        url = f"https://{APP_HOST}/xhr/front/mall/reservation/list/pageOne/queryV2"
        resp = self._session.get(url, headers=self._headers, timeout=30)
        if resp.status_code != 200:
            raise AuthError(f"查询申购结果 HTTP {resp.status_code}")
        body = resp.json()
        if body.get("code") not in (2000, 0, "2000"):
            raise AuthError(f"查询申购结果失败: {body.get('message', body)}")
        items = body.get("data", {}).get("reservationItemVOS") or []
        out: list[dict[str, Any]] = []
        for raw in items:
            status = raw.get("status")
            status_key = {0: "waiting", 1: "failed", 2: "won"}.get(status, "unknown")
            pay_status = raw.get("payStatus") or raw.get("orderStatus") or raw.get("payState")
            payment_status = "none"
            if status_key == "won":
                if pay_status in (1, "1", "paid", "PAYED", "PAY_SUCCESS"):
                    payment_status = "paid"
                elif pay_status in (2, "2", "expired", "EXPIRED"):
                    payment_status = "expired"
                else:
                    payment_status = "pending"
            ts = raw.get("reservationTime") or raw.get("createTime") or 0
            out.append(
                {
                    "item_id": str(raw.get("itemId", "")),
                    "item_name": raw.get("itemName", ""),
                    "session_name": raw.get("sessionName", ""),
                    "status": status_key,
                    "status_code": status,
                    "payment_status": payment_status,
                    "order_id": str(raw.get("orderId") or raw.get("reservationId") or ""),
                    "pay_deadline": raw.get("payEndTime") or raw.get("payDeadline") or "",
                    "reservation_time": int(ts) if ts else 0,
                    "raw": raw,
                }
            )
        return out

    def fetch_weekend_special_session(self) -> dict[str, Any]:
        """周末欢乐购专场 session 与商品列表（type=3）。"""
        ts = int(time.time() * 1000)
        url = (
            f"https://{H5_HOST}/xhr/front/mall/index/special/session/getByType/3"
            f"?__timestamp={ts}&"
        )
        resp = self._session.get(url, headers=self._static_headers(), timeout=30)
        body = resp.json()
        if body.get("code") not in (2000, 0, "2000"):
            raise AuthError(f"周末欢乐购场次失败: {body.get('message', body)}")
        data = body.get("data") or {}
        items = [
            {"item_code": i.get("itemCode", ""), "title": i.get("title", "")}
            for i in (data.get("itemList") or [])
        ]
        return {"session_id": str(data.get("sessionId", "")), "items": items}

    def reserve_with_session(self, shop_id: str, item_id: str, session_id: str) -> tuple[bool, str]:
        """使用指定 sessionId 提交预约（周末欢乐购等专场）。"""
        old_sid = self.session_id
        self.session_id = session_id
        try:
            return self.reserve(shop_id, item_id)
        finally:
            self.session_id = old_sid

    def run_travel(self) -> list[str]:
        """小茅运旅行：领取奖励 → 开始旅行（参考 ken 5_travel）。"""
        lines: list[str] = []
        h = self._h5_game_headers()
        base = f"https://{H5_HOST}/game"

        def _get(path: str, params: dict | None = None) -> dict:
            self._pace_request()
            r = self._session.get(f"{base}{path}", headers=h, params=params or {}, timeout=20)
            return r.json()

        def _post(path: str) -> dict:
            self._pace_request()
            r = self._session.post(f"{base}{path}", headers=h, timeout=20)
            return r.json()

        page = _get("/isolationPage/getUserIsolationPageData", {"__timestamp": int(time.time() * 1000)})
        if page.get("code") not in (2000, 200):
            return [f"旅行页失败: {page.get('message', page)}"]
        data = page.get("data") or {}
        xm = data.get("xmTravel") or {}
        status = xm.get("status")
        energy = int(data.get("energy") or 0)
        remain = int(xm.get("remainChance") or 0)
        lines.append(f"旅行状态={status} 耐力={energy} 今日剩余次数={remain}")

        reward = data.get("energyReward") or {}
        if int(reward.get("value") or 0) > 0:
            er = self._session.post(
                f"{base}/isolationPage/getUserEnergyAward",
                headers=self._h5_game_headers(with_geo=True),
                timeout=20,
            )
            lines.append(f"领取耐力: {er.status_code}")

        if status == 2:
            lines.append("旅行进行中，请稍后再试")
            return lines

        if status == 3:
            rw = _get("/xmTravel/getXmTravelReward")
            xmy = (rw.get("data") or {}).get("travelRewardXmy")
            if xmy:
                recv = _post("/xmTravel/receiveReward")
                lines.append(f"领取小茅运: {recv.get('message', recv.get('code'))}")
            try:
                share = _post("/xmTravel/shareReward")
                lines.append(f"分享奖励: {share.get('message', share.get('code'))}")
            except Exception:
                pass

        if remain < 1:
            lines.append("今日旅行次数已用完")
            return lines
        if energy < 100:
            lines.append(f"耐力不足 100（当前 {energy}）")
            return lines

        start = _post("/xmTravel/startTravel")
        if start.get("code") == 2000:
            lines.append("已开始新旅行")
        else:
            lines.append(f"开始旅行失败: {start.get('message', start)}")
        return lines


def new_device_id() -> str:
    return str(uuid.uuid4()).upper()
