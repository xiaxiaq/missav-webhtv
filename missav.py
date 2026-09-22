# -*- coding: utf-8 -*-
"""
MissAV TVBox 爬虫（稳定版）
域名: https://missav.ws
封面: fourhoi.com
播放: surrit.com m3u8（自动带 Referer）
支持在线爬取 + 可选本地/远程 m3u8 索引加速
"""

import re
import sys
import time
import random
from html import unescape
from urllib.parse import urljoin, quote

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def __init__(self):
            pass

try:
    import requests
    import urllib3
    urllib3.disable_warnings()
    HAS_REQ = True
except Exception:
    HAS_REQ = False


class Spider(BaseSpider):
    host = "https://missav.ws"
    locale = "cn"
    categories = None
    session = None
    index_cache = None
    index_loaded = False

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self._ensure_session()

    def _ensure_session(self):
        if self.session is not None:
            return
        if HAS_REQ:
            self.session = requests.Session()
            self.session.verify = False
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": self.host + "/",
                "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
            })

    def getName(self):
        return "MissAV"

    def init(self, extend=""):
        self._ensure_session()
        if self.categories is None:
            self._fetch_categories()
        if extend and str(extend).strip():
            self._load_index(str(extend).strip())
        return True

    def destroy(self):
        if self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None
        self.index_cache = None
        self.index_loaded = False

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url))

    def manualVideoCheck(self):
        return False

    def _fetch(self, url, referer=None, retries=3):
        if not url.startswith("http"):
            url = urljoin(self.host, url)
        for i in range(retries):
            try:
                if i:
                    time.sleep(random.uniform(0.25, 0.7))
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Referer": referer or (self.host + "/"),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8",
                }
                if HAS_REQ and self.session is not None:
                    r = self.session.get(url, headers=headers, timeout=18, allow_redirects=True)
                    if r.status_code == 200 and r.text:
                        r.encoding = "utf-8"
                        return r.text
                else:
                    from urllib import request as urlrequest
                    req = urlrequest.Request(url, headers=headers)
                    with urlrequest.urlopen(req, timeout=18) as resp:
                        return resp.read().decode("utf-8", "replace")
            except Exception as e:
                print("[MissAV] fetch error:", e)
        return ""

    def _load_index(self, path_or_url):
        if self.index_loaded:
            return
        text = ""
        try:
            if path_or_url.startswith("http"):
                text = self._fetch(path_or_url)
            else:
                with open(path_or_url, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
        except Exception as e:
            print("[MissAV] load index failed:", e)
            return
        if not text:
            return
        cache = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            title = parts[0].strip()
            detail = parts[1].strip()
            playlist = parts[2].strip()
            quality = parts[3].strip() if len(parts) > 3 else playlist
            vid = detail.rstrip("/").split("/")[-1].lower()
            if not vid:
                continue
            pic = "https://fourhoi.com/%s/cover-t.jpg" % vid
            cache[vid] = {
                "vod_id": vid,
                "vod_name": title[:100],
                "vod_pic": pic,
                "vod_remarks": "本地索引",
                "play": quality or playlist,
                "playlist": playlist,
            }
        self.index_cache = cache
        self.index_loaded = True
        print("[MissAV] index loaded: %d items" % len(cache))

    def _default_categories(self):
        return [
            {"type_id": "new", "type_name": "最近更新", "url": "/cn/new"},
            {"type_id": "release", "type_name": "新作上市", "url": "/cn/release"},
            {"type_id": "today-hot", "type_name": "今日热门", "url": "/cn/today-hot"},
            {"type_id": "weekly-hot", "type_name": "本周热门", "url": "/cn/weekly-hot"},
            {"type_id": "monthly-hot", "type_name": "本月热门", "url": "/cn/monthly-hot"},
            {"type_id": "uncensored-leak", "type_name": "无码流出", "url": "/cn/uncensored-leak"},
            {"type_id": "chinese-subtitle", "type_name": "中文字幕", "url": "/cn/chinese-subtitle"},
            {"type_id": "english-subtitle", "type_name": "英文字幕", "url": "/cn/english-subtitle"},
            {"type_id": "vr", "type_name": "VR", "url": "/cn/genres/VR"},
            {"type_id": "amateur", "type_name": "素人", "url": "/cn/genres/Amateur"},
        ]

    def _fetch_categories(self):
        self.categories = self._default_categories()

    def _parse_grid(self, html):
        items, seen = [], set()
        if not html:
            return items
        for m in re.finditer(
            r'data-src="(https://fourhoi\.com/([a-z0-9][a-z0-9\-]+)/cover-t\.jpg)"',
            html,
        ):
            pic, vid = m.group(1), m.group(2).lower()
            if vid in seen:
                continue
            seen.add(vid)
            idx = m.start()
            chunk = html[max(0, idx - 500): idx + 600]
            title = vid.upper()
            t = re.search(r'alt="([^"]{2,120})"', chunk)
            if t:
                title = unescape(t.group(1)).strip()
            else:
                t = re.search(r'class="[^"]*text-secondary[^"]*"[^>]*>([\s\S]*?)</a>', chunk)
                if t:
                    title = re.sub(r"<[^>]+>", "", t.group(1)).strip()
                    title = unescape(title)
            dur = ""
            dm = re.search(r'absolute bottom-1 right-1[^>]*>\s*([\d:]+)\s*<', chunk)
            if dm:
                dur = dm.group(1).strip()
            remarks = dur
            if "uncensored" in vid:
                remarks = (remarks + " 无码").strip()
            elif "chinese" in vid:
                remarks = (remarks + " 中字").strip()
            items.append({
                "vod_id": vid,
                "vod_name": title[:90] or vid.upper(),
                "vod_pic": pic,
                "vod_remarks": remarks or "MissAV",
            })
        if len(items) < 6:
            for m in re.finditer(r"fourhoi\.com/([a-z0-9][a-z0-9\-]+)/cover", html):
                vid = m.group(1).lower()
                if vid in seen:
                    continue
                seen.add(vid)
                items.append({
                    "vod_id": vid,
                    "vod_name": vid.upper(),
                    "vod_pic": "https://fourhoi.com/%s/cover-t.jpg" % vid,
                    "vod_remarks": "MissAV",
                })
        return items

    def homeContent(self, filter=False):
        if self.categories is None:
            self._fetch_categories()
        html = self._fetch(self.host + "/cn/new")
        if not html:
            html = self._fetch(self.host + "/cn")
        items = self._parse_grid(html)
        return {"class": self.categories or self._default_categories(), "list": items}

    def homeVideoContent(self):
        return self.categoryContent("new", "1", False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if str(pg).isdigit() else 1
        if self.categories is None:
            self._fetch_categories()
        cat_url = None
        for cat in self.categories or []:
            if cat["type_id"] == tid:
                cat_url = cat.get("url") or ("/cn/" + tid)
                break
        if not cat_url:
            cat_url = "/cn/" + str(tid)
        if page <= 1:
            url = self.host + cat_url
        else:
            url = self.host + cat_url + ("&" if "?" in cat_url else "?") + "page=%s" % page
        html = self._fetch(url)
        items = self._parse_grid(html)
        total = page
        pages = re.findall(r"[?&]page=(\d+)", html or "")
        if pages:
            total = max(int(p) for p in pages)
        return {
            "list": items,
            "page": page,
            "pagecount": max(total, page + (1 if items else 0)),
            "limit": 24,
            "total": 99999 if items else 0,
        }

    def _unpack_surrit(self, html):
        out = []
        if not html:
            return out
        for m in re.finditer(
            r"}\('((?:\\'|[^'])*)',(\d+),(\d+),'([^']+)'\.split\('\|'\)",
            html,
        ):
            p, a, c, k = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split("|")
            try:
                p = p.encode("utf-8").decode("unicode_escape")
            except Exception:
                pass

            def to_base(n, base):
                alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                if base < 2:
                    base = 16
                if n == 0:
                    return "0"
                s = ""
                while n:
                    s = alphabet[n % base] + s
                    n //= base
                return s

            try:
                decoded = p
                for i in range(c - 1, -1, -1):
                    if i < len(k) and k[i]:
                        decoded = re.sub(r"\b" + re.escape(to_base(i, a)) + r"\b", k[i], decoded)
                for name, url in re.findall(r"(source\d*|source)\s*=\s*'(https?://[^']+\.m3u8)'", decoded):
                    out.append((name, url))
                for url in re.findall(r"https?://surrit\.com/[^'\s]+\.m3u8", decoded):
                    if not any(u == url for _, u in out):
                        out.append(("auto", url))
            except Exception as e:
                print("[MissAV] unpack error:", e)
                continue

        for url in re.findall(r"https?://surrit\.com/[0-9a-f\-]+/[^\s\"']+\.m3u8", html):
            url = url.replace("\\/", "/")
            if not any(u == url for _, u in out):
                out.append(("raw", url))

        def score(item):
            n, u = item
            if "1080" in n or "1080" in u or "1280" in n:
                return 0
            if "720" in n or "720" in u or "842" in n:
                return 1
            if "playlist" in u:
                return 2
            return 3

        seen, uniq = set(), []
        for n, u in sorted(out, key=score):
            if u not in seen:
                seen.add(u)
                uniq.append((n, u))
        return uniq

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        vid = str(vid).strip("/").split("/")[-1].lower()

        if self.index_cache and vid in self.index_cache:
            item = self.index_cache[vid]
            play = item.get("play") or item.get("playlist")
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": item["vod_name"],
                    "vod_pic": item["vod_pic"],
                    "vod_content": item["vod_name"],
                    "vod_play_from": "本地索引",
                    "vod_play_url": "高清$%s" % play,
                }]
            }

        detail_url = "%s/cn/%s" % (self.host, vid)
        html = self._fetch(detail_url)
        if not html:
            html = self._fetch("%s/ja/%s" % (self.host, vid))
        if not html:
            return {"list": []}

        title = vid.upper()
        m = re.search(r'og:title"\s+content="([^"]+)"', html)
        if m:
            title = unescape(m.group(1)).strip()
        else:
            m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        cover = "https://fourhoi.com/%s/cover-t.jpg" % vid
        m = re.search(r'og:image"\s+content="(https?://[^"]+)"', html)
        if m:
            cover = m.group(1)
            if "/cover-n.jpg" in cover:
                cover = cover.replace("/cover-n.jpg", "/cover-t.jpg")

        sources = self._unpack_surrit(html)
        if not sources:
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title[:100],
                    "vod_pic": cover,
                    "vod_play_from": "MissAV",
                    "vod_play_url": "播放$%s" % detail_url,
                }]
            }

        play_from = []
        play_url = []
        for name, url in sources:
            if "1080" in name or "1080" in url or "1280" in url:
                label = "1080P"
            elif "720" in name or "720" in url or "842" in url:
                label = "720P"
            else:
                label = "高清"
            play_from.append(label)
            play_url.append("%s$%s" % (label, url))

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title[:100],
                "vod_pic": cover,
                "vod_content": title,
                "vod_play_from": "$$$".join(play_from) if play_from else "MissAV",
                "vod_play_url": "$$$".join(play_url) if play_url else "播放$%s" % detail_url,
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        key = key.strip()

        if self.index_cache:
            results = []
            key_lower = key.lower()
            for vid, item in self.index_cache.items():
                if key_lower in vid or key_lower in item["vod_name"].lower():
                    results.append({
                        "vod_id": item["vod_id"],
                        "vod_name": item["vod_name"],
                        "vod_pic": item["vod_pic"],
                        "vod_remarks": item.get("vod_remarks", "本地"),
                    })
                    if len(results) >= 50:
                        break
            if results:
                return {
                    "list": results,
                    "page": 1,
                    "pagecount": 1,
                    "limit": 50,
                    "total": len(results),
                }

        url = "%s/cn/search/%s" % (self.host, quote(key))
        if page > 1:
            url += "?page=%s" % page
        html = self._fetch(url)
        items = self._parse_grid(html)
        return {
            "list": items,
            "page": page,
            "pagecount": page + (1 if items else 0),
            "limit": 24,
            "total": 9999,
        }

    def playerContent(self, flag, id, vipFlags):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://missav.ws/",
            "Origin": "https://missav.ws",
        }
        return {
            "parse": 0,
            "url": id,
            "header": headers,
        }

    def localProxy(self, param):
        return [200, "text/plain", b""]
