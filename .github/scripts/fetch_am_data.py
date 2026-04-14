#!/usr/bin/env python3
"""
GitHub Actions 中运行：用小红书 SSO cookie 请求 RedBI 数据
环境变量：AM_NAME, XHS_COOKIE
"""
import os, json, datetime, urllib.request, sys

AM_NAME = os.environ.get("AM_NAME", "").strip()
XHS_COOKIE = os.environ.get("XHS_COOKIE", "").strip()
DATA_FILE = "data.json"

if not AM_NAME:
    print("❌ AM_NAME 未设置"); sys.exit(1)

def fetch_redbi(am_name, cookie):
    """调用 RedBI NL 取数接口，模糊匹配 AM 名字"""
    url = "https://redbi.devops.xiaohongshu.com/api/nl/query"
    headers = {
        "Cookie": cookie,
        "Content-Type": "application/json",
        "Referer": "https://redbi.devops.xiaohongshu.com/analysis/edit?analysisId=41927735&shortcutId=15157602&projectId=4",
        "Origin": "https://redbi.devops.xiaohongshu.com",
    }
    body = json.dumps({
        "analysisId": 41927735,
        "shortcutId": 15157602,
        "projectId": 4,
        "query": f"商家am名称 包含 {am_name}，提取商家ID、商家名称、DGMV，按DGMV降序取TOP50"
    }).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        rows = data.get("data", {}).get("rows", [])
        if not rows:
            # 尝试备用字段
            rows = data.get("rows", [])
        merchants = []
        for row in rows[:50]:
            mid = row.get("商家ID") or row.get("merchant_id") or row.get("seller_id", "")
            name = row.get("商家名称") or row.get("merchant_name") or row.get("shop_name", "")
            if mid and name and len(str(mid)) > 10:  # 过滤汇总行
                merchants.append({
                    "id": str(mid), "name": str(name),
                    "week7Count": 0, "todayCount": 0,
                    "week7Items": [], "todayItems": [],
                    "isBlackBox": False, "amAdvice": ""
                })
        print(f"RedBI 返回 {len(rows)} 行，有效商家 {len(merchants)} 家")
        return merchants
    except Exception as e:
        print(f"RedBI 取数失败: {e}")
        return []

# 读取现有 data.json
try:
    with open(DATA_FILE) as f:
        existing = json.load(f)
except Exception:
    existing = {"updatedAt": "", "ams": {}}

# 取数
merchants = fetch_redbi(AM_NAME, XHS_COOKIE)

# 更新对应 AM，保留其他 AM 数据不变
existing["ams"][AM_NAME] = {
    "displayName": AM_NAME,
    "category": "",
    "placeholder": len(merchants) == 0,
    "merchants": merchants
}
existing["updatedAt"] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()

with open(DATA_FILE, "w") as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

print(f"✅ data.json 已更新，AM={AM_NAME}，商家数={len(merchants)}")
if len(merchants) == 0:
    print("⚠️ 商家数为0，可能是 XHS_COOKIE 过期或 AM 名字不匹配")
    sys.exit(1)
