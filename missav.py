# -*- coding: utf-8 -*-
"""
MissAV 离线版（自动过滤无数据分类）
只依赖 m3u8播放链接_汇总.txt
"""

import sys
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
        self.index = []
        self.by_id = {}
        self.classes = []
        self.loaded = False

    def getName(self):
        return "MissAV"

    def init(self, extend=""):
        self._load(extend)
        return True

    def destroy(self):
        self.index = []
        self.by_id = {}
        self.classes = []
        self.loaded = False

    def isVideoFormat(self, url):
        return bool(url and (".m3u8" in url or ".mp4" in url))

    def manualVideoCheck(self):
        return False

    def _fetch(self, url):
        if not HAS_REQ or not url:
            return ""
        try:
            r = requests.get(url, timeout=25, verify=False, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
        except Exception as e:
            print("[MissAV] fetch error:", e)
        return ""

    def _load(self, extend):
        if self.loaded:
            return

        m3u8_url = "https://raw.githubusercontent.com/xiaxiaq/missav-webhtv/main/m3u8播放链接_汇总.txt"
        if extend and str(extend).strip().startswith("http"):
            # 兼容以前的 | 写法，只取第一个
            m3u8_url = str(extend).split("|")[0].strip()

        text = self._fetch(m3u8_url)
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
            item = {
                "vod_id": vid,
                "vod_name": title[:100],
                "vod_pic": "https://fourhoi.com/%s/cover-t.jpg" % vid,
                "vod_remarks": "本地",
                "play": quality or playlist,
            }
            items.append(item)
            self.by_id[vid] = item

        self.index = items
        print("[MissAV] loaded %d items" % len(items))

        # 只保留真正有数据的分类
        candidates = [
            ("all", "全部"),
            ("10musume", "10musume"),
            ("1pondo", "1pondo"),
            ("caribbean", "Caribbean"),
            ("pacopacomama", "Pacopacomama"),
            ("tokyohot", "Tokyo Hot"),
            ("xxx-av", "XXX-AV"),
            ("xxxav", "XXX-AV"),
            ("fc2", "FC2"),
            ("siro", "SIRO"),
            ("gana", "GANA"),
            ("ara", "ARA"),
            ("scute", "S-Cute"),
            ("heyzo", "Heyzo"),
            ("中文字幕", "中文字幕"),
            ("無碼", "無碼流出"),
            ("无码", "无码"),
            ("中出", "中出"),
            ("ntr", "NTR"),
            ("vr", "VR"),
            ("人妻", "人妻"),
            ("ol", "OL"),
            ("乱伦", "乱伦"),
            ("丝袜", "丝袜"),
            ("巨乳", "巨乳"),
            ("美少女", "美少女"),
            ("熟女", "熟女"),
            ("素人", "素人"),
            ("学生", "学生"),
            ("制服", "制服"),
            ("口交", "口交"),
            ("颜射", "颜射"),
            ("sm", "SM"),
            ("3p", "3P"),
            ("4k", "4K"),
        ]

        classes = []
        for tid, name in candidates:
            if tid == "all":
                classes.append({"type_id": "all", "type_name": "全部"})
                continue
            # 简单统计是否有匹配
            cnt = 0
            key = tid.lower()
            for it in items:
                if key in it["vod_id"] or key in it["vod_name"].lower():
                    cnt += 1
                    if cnt >= 3:  # 至少有几条才显示
                        break
            if cnt >= 3:
                classes.append({"type_id": tid, "type_name": name})

        self.classes = classes
        self.loaded = True
        print("[MissAV] valid classes:", len(classes))

    def homeContent(self, filter=False):
        return {
            "class": self.classes or [{"type_id": "all", "type_name": "全部"}],
            "list": self.index[:30]
        }

    def homeVideoContent(self):
        return {"list": self.index[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if str(pg).isdigit() else 1
        size = 24
        start = (page - 1) * size
        end = start + size

        if not tid or tid == "all":
            data = self.index
        else:
            key = tid.lower()
            data = [x for x in self.index if key in x["vod_id"] or key in x["vod_name"].lower()]

        total = len(data)
        pagecount = max(1, (total + size - 1) // size)
        return {
            "list": data[start:end],
            "page": page,
            "pagecount": pagecount,
            "limit": size,
            "total": total,
        }

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        vid = str(vid).strip("/").split("/")[-1].lower()
        item = self.by_id.get(vid)
        if not item:
            return {"list": []}
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": item["vod_name"],
                "vod_pic": item["vod_pic"],
                "vod_content": item["vod_name"],
                "vod_play_from": "本地索引",
                "vod_play_url": "高清$%s" % item["play"],
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
        return {"list": results, "page": 1, "pagecount": 1, "limit": 50, "total": len(results)}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://missav.ws/",
                "Origin": "https://missav.ws",
            }
        }

    def localProxy(self, param):
        return [200, "text/plain", b""]
