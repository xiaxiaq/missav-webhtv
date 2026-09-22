# -*- coding: utf-8 -*-
"""
MissAV 离线增强版（WebHomeTV / 影视+ / PeekPili）
- 完全不访问 missav.ws（绕过 Cloudflare）
- 使用 m3u8播放链接_汇总.txt 作为播放数据
- 使用 _分类索引.txt 生成丰富分类
"""

import re
import sys
from urllib.parse import quote, unquote

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
        self.index = []          # 全部条目
        self.by_id = {}          # vid -> item
        self.classes = []        # 分类列表
        self.loaded = False

    def getName(self):
        return "MissAV"

    def init(self, extend=""):
        # extend 可以是 m3u8 索引地址，也可以是 "m3u8地址|分类索引地址"
        self._load_all(extend)
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

    def _fetch_text(self, url):
        if not url or not HAS_REQ:
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

    def _load_all(self, extend):
        if self.loaded:
            return

        m3u8_url = "https://raw.githubusercontent.com/xiaxiaq/missav-webhtv/main/m3u8播放链接_汇总.txt"
        cate_url = "https://raw.githubusercontent.com/xiaxiaq/missav-webhtv/main/_分类索引.txt"

        if extend and str(extend).strip():
            parts = str(extend).strip().split("|")
            if parts[0].startswith("http"):
                m3u8_url = parts[0].strip()
            if len(parts) > 1 and parts[1].startswith("http"):
                cate_url = parts[1].strip()

        # 1. 加载播放索引
        text = self._fetch_text(m3u8_url)
        if not text:
            print("[MissAV] m3u8 index empty")
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
        print("[MissAV] loaded %d play items" % len(items))

        # 2. 加载分类索引
        cate_text = self._fetch_text(cate_url)
        classes = [{"type_id": "all", "type_name": "全部"}]

        # 优先加常用工作室
        studio_order = [
            "10musume", "1pondo", "caribbeancom", "caribbeancompr", "pacopacomama",
            "tokyohot", "xxxav", "fc2", "siro", "gana", "ara", "scute", "clive",
            "gachinco", "marriedslash", "naughty0930", "naughty4610"
        ]
        for s in studio_order:
            classes.append({"type_id": s, "type_name": s})

        # 再加热门类型
        hot_types = [
            ("中文字幕", "中文字幕"), ("無碼流出", "無碼流出"), ("最新上架", "最新上架"),
            ("最近发布", "最近发布"), ("中出", "中出"), ("NTR", "NTR"), ("VR", "VR"),
            ("人妻", "人妻"), ("OL", "OL"), ("乱伦", "乱伦"), ("丝袜", "丝袜"),
            ("主观视角", "主观视角"), ("偷拍", "偷拍"), ("SM", "SM"), ("3P / 4P", "3P"),
            ("乳交", "乳交"), ("巨乳", "巨乳"), ("美少女", "美少女"), ("熟女", "熟女"),
            ("素人", "素人"), ("学生", "学生"), ("制服", "制服"), ("口交", "口交"),
            ("颜射", "颜射"), ("多P", "多P"), ("调教", "调教"), ("痴女", "痴女"),
            ("4K", "4K"), ("高清", "高清")
        ]
        for tid, name in hot_types:
            classes.append({"type_id": tid, "type_name": name})

        # 从分类索引再补充一些有数据的工作室/类型（避免太多）
        if cate_text:
            seen = set(c["type_id"] for c in classes)
            for line in cate_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "\t" not in line:
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                dim, name, cnt = parts[0].strip(), parts[1].strip(), parts[2].strip()
                try:
                    count = int(cnt)
                except:
                    count = 0
                if count < 50:  # 太少的跳过
                    continue
                tid = name
                if tid in seen or len(classes) > 80:
                    continue
                # 只加工作室和集合页，类型太多就不全部加了
                if dim in ("10musume", "1pondo", "caribbeancom", "片商", "集合页") or dim in studio_order:
                    classes.append({"type_id": tid, "type_name": name[:20]})
                    seen.add(tid)

        self.classes = classes
        self.loaded = True
        print("[MissAV] classes: %d" % len(classes))

    def homeContent(self, filter=False):
        return {
            "class": self.classes or [{"type_id": "all", "type_name": "全部"}],
            "list": self.index[:30]
        }

    def homeVideoContent(self):
        return {"list": self.index[:30]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg) if str(pg).isdigit() else 1
        page_size = 24
        start = (page - 1) * page_size
        end = start + page_size

        if not tid or tid == "all":
            data = self.index
        else:
            key = tid.lower().replace(" ", "").replace("/", "").replace("、", "")
            data = []
            for x in self.index:
                vid = x["vod_id"]
                name = x["vod_name"].lower()
                if key in vid or key in name:
                    data.append(x)
                # 简单同义词
                elif key in ("中出", "creampie") and ("中出" in name or "creampie" in name):
                    data.append(x)
                elif key in ("无码", "無碼", "uncensored") and ("uncensored" in vid or "无码" in name or "無碼" in name):
                    data.append(x)

        total = len(data)
        pagecount = max(1, (total + page_size - 1) // page_size)
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
                if len(results) >= 60:
                    break
        return {
            "list": results,
            "page": 1,
            "pagecount": 1,
            "limit": 60,
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
