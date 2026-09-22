# -*- coding: utf-8 -*-
"""
MissAV 离线版（专供 WebHomeTV / 影视+）
完全依赖 m3u8播放链接_汇总.txt，不访问 missav.ws
解决 Cloudflare 导致暂无数据的问题
"""

import re
import sys
from urllib.parse import quote

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
    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.index = []          # 所有条目
        self.by_id = {}          # vid -> item
        self.loaded = False

    def getName(self):
        return "MissAV"

    def init(self, extend=""):
        self._load_index(extend)
        return True

    def destroy(self):
        self.index = []
        self.by_id = {}
        self.loaded = False

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url))

    def manualVideoCheck(self):
        return False

    def _fetch_text(self, url):
        if not HAS_REQ:
            return ""
        try:
            r = requests.get(url, timeout=20, verify=False, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
        except Exception as e:
            print("[MissAV] fetch index error:", e)
        return ""

    def _load_index(self, path_or_url):
        if self.loaded:
            return
        text = ""
        if path_or_url and str(path_or_url).strip().startswith("http"):
            text = self._fetch_text(str(path_or_url).strip())
        if not text:
            # 默认尝试你仓库里的文件
            text = self._fetch_text("https://raw.githubusercontent.com/xiaxiaq/missav-webhtv/main/m3u8播放链接_汇总.txt")
        if not text:
            print("[MissAV] index empty")
            return

        items = []
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
            item = {
                "vod_id": vid,
                "vod_name": title[:100],
                "vod_pic": pic,
                "vod_remarks": "本地",
                "play": quality or playlist,
                "playlist": playlist,
            }
            items.append(item)
            self.by_id[vid] = item

        self.index = items
        self.loaded = True
        print("[MissAV] loaded %d items" % len(items))

    def homeContent(self, filter=False):
        classes = [
            {"type_id": "all", "type_name": "全部"},
            {"type_id": "musume", "type_name": "10musume"},
            {"type_id": "pondo", "type_name": "1pondo"},
            {"type_id": "xxx-av", "type_name": "XXX-AV"},
            {"type_id": "caribbean", "type_name": "Caribbean"},
            {"type_id": "pacopacomama", "type_name": "Pacopacomama"},
            {"type_id": "heyzo", "type_name": "Heyzo"},
            {"type_id": "tokyo-hot", "type_name": "Tokyo Hot"},
            {"type_id": "other", "type_name": "其他"},
        ]
        # 首页先返回最新 30 条
        return {"class": classes, "list": self.index[:30]}

    def homeVideoContent(self):
        return {"list": self.index[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if str(pg).isdigit() else 1
        page_size = 24
        start = (page - 1) * page_size
        end = start + page_size

        if tid == "all" or not tid:
            data = self.index
        else:
            key = tid.lower()
            data = [x for x in self.index if key in x["vod_id"] or key in x["vod_name"].lower()]

        total = len(data)
        pagecount = (total + page_size - 1) // page_size if total else 1
        return {
            "list": data[start:end],
            "page": page,
            "pagecount": pagecount,
            "limit": page_size,
            "total": total,
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        vid = str(vid).strip("/").split("/")[-1].lower()
        item = self.by_id.get(vid)
        if not item:
            return {"list": []}
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

    def searchContent(self, key, quick=False, pg="1"):
        key = key.strip().lower()
        results = []
        for item in self.index:
            if key in item["vod_id"] or key in item["vod_name"].lower():
                results.append({
                    "vod_id": item["vod_id"],
                    "vod_name": item["vod_name"],
                    "vod_pic": item["vod_pic"],
                    "vod_remarks": "本地",
                })
                if len(results) >= 50:
                    break
        return {
            "list": results,
            "page": 1,
            "pagecount": 1,
            "limit": 50,
            "total": len(results),
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
