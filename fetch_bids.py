import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests

MY_API_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService02/getBidPblancListInfoServc02"

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
three_days_ago = now - timedelta(days=3)

raw_key = os.environ.get("DATA_GO_KR_KEY", "").strip()
if not raw_key:
    raise RuntimeError("DATA_GO_KR_KEY 비밀키가 설정되지 않았습니다.")

service_key = urllib.parse.unquote(raw_key)

params = {
    "serviceKey": service_key,
    "numOfRows": "100",
    "pageNo": "1",
    "inqryDiv": "1",
    "inqryBgnDt": three_days_ago.strftime("%Y%m%d0000"),
    "inqryEndDt": now.strftime("%Y%m%d2359"),
    "type": "json",
}

resp = requests.get(MY_API_URL, params=params, timeout=30)
print(f"요청한 주소: {MY_API_URL}")
print(f"응답 상태 코드: {resp.status_code}")

try:
    parsed = resp.json()
except Exception:
    raise RuntimeError(f"JSON 대신 다른 응답이 왔습니다 -> {resp.text[:400]}")

header = parsed.get("response", {}).get("header", {})
if header.get("resultCode") != "00":
    raise RuntimeError(f"조달청 API 오류 응답 -> {header}")

body = parsed.get("response", {}).get("body", {})
raw_items = body.get("items", [])

if isinstance(raw_items, dict):
    items = raw_items.get("item", [])
    if isinstance(items, dict):
        items = [items]
elif isinstance(raw_items, list):
    items = raw_items
else:
    items = []

bids = []
for item in items:
    bids.append({
        "bidNo": f"{item.get('bidNtceNo', '')}-{item.get('bidNtceOrd', '00')}",
        "title": item.get("bidNtceNm", ""),
        "agency": item.get("dminsttNm") or item.get("ntceInsttNm", ""),
        "noticeDate": item.get("bidNtceDt", ""),
        "closeDate": item.get("bidClseDt", ""),
        "price": item.get("presmptPrce") or item.get("asignBdgtAmt") or "0",
        "method": item.get("cntrctCnclsMthdNm", ""),
        "url": item.get("bidNtceDtlUrl", ""),
    })

output = {
    "updatedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
    "totalCount": len(bids),
    "bids": bids,
}

with open("bids.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"총 {len(bids)}건의 용역 공고를 bids.json에 저장했습니다.")
