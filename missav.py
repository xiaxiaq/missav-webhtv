# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except:
    class BaseSpider:
        def __init__(self):
            pass

try:
    import requests
    import urllib3
    urllib3.disable_warnings()
    HAS_REQ = True
except:
    HAS_REQ = False


class Spider(BaseSpider):
    def __init__(self):
        try:
            super().__init__()
        except:
            pass
        self.index = []
        self.by_id = {}
        self.loaded = False

    def getName(self):
        return "MissAV"

    def init(self, extend=""):
        self._load(extend)
        return True

    def destroy(self):
        self.index = []
        self.by_id = {}
        self.loaded = False

    def isVideoFormat(self, url):
        return ".m3u8" in str(url) or ".mp4" in str(url)

    def manualVideoCheck(self):
        return False

    def _fetch(self, url):
        if not HAS_REQ:
            return ""
        try:
            r = requests.get(url, timeout=30, verify=False, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
        except Exception as e:
            print("fetch error:", e)
        return ""

    def _load(self, extend):
        if self.loaded:
            return
        url = "https://raw.githubusercontent.com/xiaxiaq/missav-webhtv/main/m3u8播放链接_汇总.txt"
        if extend and str(extend).startswith("http"):
            url = str(extend).split("|")[0].strip()

        text = self._fetch(url)
        if not text:
            print("index empty")
            return

        for line in text.splitlines():
            line = line.strip()
            if not line or "\t" not in line:
                continue
            p = line.split("\t")
            if len(p) < 3:
                continue
            title = p[0].strip()
            detail = p[1].strip()
            play = p[3].strip() if len(p) > 3 else p[2].strip()
            vid = detail.rstrip("/").split("/")[-1].lower()
            if not vid:
                continue
            item = {
                "vod_id": vid,
                "vod_name": title[:80],
                "vod_pic": "https://fourhoi.com/%s/cover-t.jpg" % vid,
                "vod_remarks": "本地",
                "play": play
            }
            self.index.append(item)
            self.by_id[vid] = item

        self.loaded = True
        print("loaded", len(self.index))

    def homeContent(self, filter=False):
        classes = [
            {"type_id": "all", "type_name": "全部"},
            {"type_id": "10musume", "type_name": "10musume"},
            {"type_id": "1pondo", "type_name": "1pondo"},
            {"type_id": "caribbean", "type_name": "Caribbean"},
            {"type_id": "pacopacomama", "type_name": "Pacopacomama"},
            {"type_id": "fc2", "type_name": "FC2"},
            {"type_id": "tokyohot", "type_name": "Tokyo Hot"},
            {"type_id": "siro", "type_name": "SIRO"},
            {"type_id": "中出", "type_name": "中出"},
            {"type_id": "人妻", "type_name": "人妻"},
            {"type_id": "巨乳", "type_name": "巨乳"},
            {"type_id": "素人", "type_name": "素人"},
        ]
        return {"class": classes, "list": self.index[:24]}

    def homeVideoContent(self):
        return {"list": self.index[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if str(pg).isdigit() else 1
        size = 24
        start = (page - 1) * size

        if tid == "all" or not tid:
            data = self.index
        else:
            key = tid.lower()
            data = [x for x in self.index if key in x["vod_id"] or key in x["vod_name"].lower()]

        total = len(data)
        return {
            "list": data[start:start+size],
            "page": page,
            "pagecount": max(1, (total + size - 1) // size),
            "limit": size,
            "total": total
        }

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids).split("/")[-1].lower()
        item = self.by_id.get(vid)
        if not item:
            return {"list": []}
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": item["vod_name"],
                "vod_pic": item["vod_pic"],
                "vod_play_from": "本地",
                "vod_play_url": "播放$%s" % item["play"]
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        key = key.lower().strip()
        res = []
        for x in self.index:
            if key in x["vod_id"] or key in x["vod_name"].lower():
                res.append({
                    "vod_id": x["vod_id"],
                    "vod_name": x["vod_name"],
                    "vod_pic": x["vod_pic"],
                    "vod_remarks": "本地"
                })
                if len(res) >= 40:
                    break
        return {"list": res}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://missav.ws/",
                "Origin": "https://missav.ws"
            }
        }

    def localProxy(self, param):
        return [200, "text/plain", b""]
