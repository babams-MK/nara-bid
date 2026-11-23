import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
three_days_ago = now - timedelta(days=3)

raw_key = os.environ.get("DATA_GO_KR_KEY", "").strip()
if not raw_key:
    raise RuntimeError("DATA_GO_KR_KEY 비밀키가 설정되지 않았습니다.")

# Encoding/Decoding 어느 키를 저장했든 정상 작동하도록 자동 변환
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

endpoints = [
    "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc",
    "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServc",
]

data = None
last_error = None

for url in endpoints:
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            parsed = resp.json()
            header = parsed.get("response", {}).get("header", {})
            if header.get("resultCode") == "00":
                data = parsed
                print(f"수집 성공: {url}")
                break
            last_error = f"API 응답 오류: {header}"
        else:
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        last_error = str(e)

if data is None:
    raise RuntimeError(f"조달청 API 호출 실패 -> {last_error}")

body = data.get("response", {}).get("body", {})
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
