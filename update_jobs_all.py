# -*- coding: utf-8 -*-
"""
채용 트래커 통합 수집 스크립트 v3
────────────────────────────────
데이터 소스 (있는 키만 자동 사용, 하나만 있어도 작동):
 [A] 워크넷(고용24) 공공 API  → worknet_key.txt   (공공데이터포털, 신청 즉시 발급)
 [B] 사람인 채용정보 API      → api_key.txt       (승인 필요, 나중에 추가 가능)
두 소스 결과를 합쳐 jobs.js 하나로 저장합니다.

로컬: python3 update_jobs_all.py
GitHub Actions: 매일 자동 실행 (update-jobs.yml)
"""
import json, time, sys, re, datetime, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (트래커 기업명, 검색 키워드, 회사명 매칭 문자열들, 제외어, 카테고리)
COMPANIES = [
    ("삼성전자 DS","삼성전자",["삼성전자"],[],0),
    ("SK하이닉스","SK하이닉스",["하이닉스"],[],0),
    ("마이크론코리아","마이크론",["마이크론"],[],0),
    ("매그나칩반도체","매그나칩",["매그나칩"],[],0),
    ("온세미","온세미",["온세미"],[],0),
    ("어플라이드머티어리얼즈","어플라이드머티어리얼즈",["어플라이드"],[],1),
    ("ASML코리아","ASML",["에이에스엠엘","ASML"],[],1),
    ("도쿄일렉트론코리아","도쿄일렉트론",["도쿄일렉트론"],[],1),
    ("램리서치코리아","램리서치",["램리서치"],[],1),
    ("원익IPS","원익아이피에스",["원익아이피에스","원익IPS"],[],1),
    ("주성엔지니어링","주성엔지니어링",["주성엔지니어링"],[],1),
    ("PSK","피에스케이",["피에스케이"],[],1),
    ("선익시스템","선익시스템",["선익시스템"],[],1),
    ("참엔지니어링","참엔지니어링",["참엔지니어링"],[],1),
    ("캐논코리아","캐논코리아",["캐논코리아"],[],1),
    ("유진테크놀로지","유진테크놀로지",["유진테크놀로지"],[],5),
    ("유진테크","유진테크",["유진테크"],["놀로지"],1),
    ("테스","주식회사 테스",["테스"],["시스템","네트","마이다"],1),
    ("케이씨텍","케이씨텍",["케이씨텍"],[],1),
    ("이오테크닉스","이오테크닉스",["이오테크닉스"],[],1),
    ("GST","글로벌스탠다드테크놀로지",["글로벌스탠다드테크"],[],1),
    ("유니셈","유니셈",["유니셈"],[],1),
    ("네패스","네패스",["네패스"],[],2),
    ("앰코테크놀로지코리아","앰코테크놀로지",["앰코"],[],2),
    ("한미반도체","한미반도체",["한미반도체"],[],2),
    ("LB세미콘","엘비세미콘",["엘비세미콘"],[],2),
    ("스태츠칩팩코리아","스태츠칩팩",["스태츠칩팩"],[],2),
    ("ASE코리아","에이에스이코리아",["에이에스이"],[],2),
    ("하나마이크론","하나마이크론",["하나마이크론"],[],2),
    ("두산테스나","두산테스나",["테스나"],[],2),
    ("SFA반도체","SFA반도체",["에스에프에이반도체","SFA반도체"],[],2),
    ("삼성전기","삼성전기",["삼성전기"],[],3),
    ("SK실트론","실트론",["실트론"],[],3),
    ("동진쎄미켐","동진쎄미켐",["동진쎄미켐"],[],3),
    ("솔브레인","솔브레인",["솔브레인"],[],3),
    ("티씨케이","티씨케이",["티씨케이"],[],3),
    ("동우화인켐","동우화인켐",["동우화인켐"],[],3),
    ("도레이첨단소재","도레이첨단소재",["도레이첨단소재"],[],3),
    ("신에츠코리아","신에츠",["신에츠"],[],3),
    ("KCC","케이씨씨",["케이씨씨","KCC"],["글라스"],3),
    ("LG화학","LG화학",["LG화학","엘지화학"],[],3),
    ("롯데케미칼","롯데케미칼",["롯데케미칼"],[],3),
    ("서울반도체","서울반도체",["서울반도체"],[],3),
    ("일진다이아몬드","일진다이아몬드",["일진다이아"],[],3),
    ("삼화콘덴서","삼화콘덴서",["삼화콘덴서"],[],3),
    ("SEMCNS","셈씨엔에스",["셈씨엔에스","SEMCNS"],[],3),
    ("STM","에스티엠",["에스티엠"],[],3),
    ("원익QnC","원익큐엔씨",["원익큐엔씨","원익QnC"],[],3),
    ("하나머티리얼즈","하나머티리얼즈",["하나머티리얼즈"],[],3),
    ("코미코","코미코",["코미코"],[],3),
    ("디엔에프","디엔에프",["디엔에프"],[],3),
    ("미코","미코세라믹스",["미코"],["코스"],3),
    ("엠케이전자","엠케이전자",["엠케이전자"],[],3),
    ("삼성디스플레이","삼성디스플레이",["삼성디스플레이"],[],4),
    ("LG디스플레이","LG디스플레이",["LG디스플레이","엘지디스플레이"],[],4),
    ("LG에너지솔루션","LG에너지솔루션",["LG에너지솔루션","엘지에너지솔루션"],[],5),
    ("삼성SDI","삼성SDI",["삼성SDI","삼성에스디아이"],[],5),
    ("SK온","에스케이온",["에스케이온","SK온"],[],5),
    ("포스코퓨처엠","포스코퓨처엠",["포스코퓨처엠"],[],5),
    ("에코프로비엠","에코프로비엠",["에코프로비엠"],[],5),
    ("롯데에너지머티리얼즈","롯데에너지머티리얼즈",["롯데에너지머티리얼즈"],[],5),
    ("두산에너빌리티","두산에너빌리티",["두산에너빌리티"],[],5),
    ("두산퓨얼셀","두산퓨얼셀",["두산퓨얼셀"],[],5),
    ("한화큐셀","한화솔루션",["한화솔루션","한화큐셀"],[],5),
    ("동원시스템즈","동원시스템즈",["동원시스템즈"],[],5),
    ("델코","델코",["델코"],[],5),
    ("엘앤에프","엘앤에프",["엘앤에프"],[],5),
    ("에코프로머티리얼즈","에코프로머티리얼즈",["에코프로머티리얼"],[],5),
    ("SK아이이테크놀로지","SK아이이테크놀로지",["아이이테크놀로지"],[],5),
    ("대주전자재료","대주전자재료",["대주전자재료"],[],5),
    ("나노신소재","나노신소재",["나노신소재"],[],5),
    ("성일하이텍","성일하이텍",["성일하이텍"],[],5),
]

def read_key(name):
    f = HERE / name
    if f.exists():
        k = f.read_text(encoding="utf-8").strip()
        return k or None
    return None

def match_ok(co, matches, negs):
    low = co.lower()
    if not any(m.lower() in low for m in matches):
        return False
    if any(n.lower() in low for n in negs):
        return False
    return True

def norm_date(s):
    """'2026-08-31', '20260831', '채용시까지' 등 → YYYY-MM-DD 또는 ''"""
    s = (s or "").strip()
    m = re.search(r"(\d{4})[-./]?(\d{2})[-./]?(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

# ─────────── [A] 워크넷(고용24) 공공 API ───────────
# 발급 페이지의 '요청주소'가 아래와 다르면 이 값만 바꿔주세요.
WORKNET_URL = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do"

def collect_worknet(key):
    items = []
    print("─" * 40)
    print("[A] 워크넷 공공 API 수집 시작")
    for i, (name, kw, matches, negs, cat) in enumerate(COMPANIES, 1):
        try:
            params = urllib.parse.urlencode({
                "authKey": key, "callTp": "L", "returnType": "XML",
                "startPage": 1, "display": 100, "keyword": kw,
            })
            req = urllib.request.Request(WORKNET_URL + "?" + params)
            with urllib.request.urlopen(req, timeout=15) as res:
                xml = res.read().decode("utf-8", "replace")
            root = ET.fromstring(xml)
            n = 0
            for w in root.iter("wanted"):
                co = (w.findtext("company") or "").strip()
                if not match_ok(co, matches, negs):
                    continue
                title = (w.findtext("title") or "").strip()
                url = (w.findtext("wantedInfoUrl") or "").strip()
                if not title:
                    continue
                items.append({
                    "tracker": name, "cat": cat, "company": co,
                    "title": title, "url": url,
                    "location": (w.findtext("region") or "").strip(),
                    "jobType": (w.findtext("holidayTpNm") or "").strip(),
                    "career": (w.findtext("career") or "").strip(),
                    "start": norm_date(w.findtext("regDt")),
                    "expiration": norm_date(w.findtext("closeDt")),
                    "closeType": "" if norm_date(w.findtext("closeDt")) else ((w.findtext("closeDt") or "상시").strip()),
                    "posted": norm_date(w.findtext("regDt")),
                    "src": "worknet",
                })
                n += 1
            if n:
                print(f"  [{i:2d}] {name}: {n}건")
        except Exception as e:
            print(f"  [{i:2d}] {name}: 실패 ({e})")
        time.sleep(0.25)
    print(f"[A] 워크넷 합계 {len(items)}건")
    return items

# ─────────── [B] 사람인 API (키 있을 때만) ───────────
SARAMIN_URL = "https://oapi.saramin.co.kr/job-search"

def saramin_call(key, params):
    params = dict(params); params["access-key"] = key
    req = urllib.request.Request(SARAMIN_URL + "?" + urllib.parse.urlencode(params),
                                 headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = json.loads(res.read().decode("utf-8"))
    if isinstance(data, dict) and "code" in data and "jobs" not in data:
        raise RuntimeError(f"API 오류 {data.get('code')}: {data.get('message')}")
    jobs = data.get("jobs", {}).get("job", [])
    return [jobs] if isinstance(jobs, dict) else jobs

def ts_to_date(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except Exception:
        return ""

def saramin_parse(j, name=None, cat=None):
    if str(j.get("active", "1")) == "0":
        return None
    co = ((j.get("company", {}) or {}).get("detail", {}) or {}).get("name", "") or ""
    if name is None:
        for nm, kw, matches, negs, c in COMPANIES:
            if match_ok(co, matches, negs):
                name, cat = nm, c
                break
        else:
            return None
    pos = j.get("position", {}) or {}
    close = j.get("close-type", {}) or {}
    ccode = str(close.get("code", ""))
    exp = ts_to_date(j.get("expiration-timestamp", "")) if ccode == "1" else ""
    return {
        "tracker": name, "cat": cat, "company": co,
        "title": (pos.get("title") or "").strip(),
        "url": j.get("url", ""),
        "location": ((pos.get("location") or {}).get("name") or "").split(",")[0],
        "jobType": ((pos.get("job-type") or {}).get("name") or ""),
        "career": ((pos.get("experience-level") or {}).get("name") or ""),
        "start": ts_to_date(j.get("opening-timestamp", "")),
        "expiration": exp,
        "closeType": (close.get("name") or ""),
        "posted": ts_to_date(j.get("posting-timestamp", "")),
        "src": "saramin",
    }

def collect_saramin(key):
    items = []
    print("─" * 40)
    print("[B] 사람인 API 수집 시작")
    for i, (name, kw, matches, negs, cat) in enumerate(COMPANIES, 1):
        try:
            n = 0
            for j in saramin_call(key, {"keywords": kw, "count": 110, "sort": "ud"}):
                co = ((j.get("company", {}) or {}).get("detail", {}) or {}).get("name", "") or ""
                if not match_ok(co, matches, negs):
                    continue
                it = saramin_parse(j, name, cat)
                if it:
                    items.append(it); n += 1
            if n:
                print(f"  [{i:2d}] {name}: {n}건")
        except Exception as e:
            print(f"  [{i:2d}] {name}: 실패 ({e})")
        time.sleep(0.4)
    # 공채속보 보강
    try:
        for page in range(3):
            jl = saramin_call(key, {"bbs_gb": 1, "count": 110, "start": page, "sort": "ud"})
            if not jl:
                break
            for j in jl:
                it = saramin_parse(j)
                if it:
                    it["bbs"] = 1
                    items.append(it)
            if len(jl) < 110:
                break
            time.sleep(0.4)
    except Exception as e:
        print(f"  공채속보 실패 ({e})")
    print(f"[B] 사람인 합계 {len(items)}건")
    return items

def main():
    wk = read_key("worknet_key.txt")
    sk = read_key("api_key.txt")
    if not wk and not sk:
        print("키가 없어요. worknet_key.txt (즉시발급) 또는 api_key.txt 를 만들어주세요.")
        print("워크넷 키 발급: data.go.kr → '워크넷 채용정보' 검색 → 활용신청 → 마이페이지에서 인증키 복사")
        sys.exit(1)

    items = []
    if wk: items += collect_worknet(wk)
    if sk: items += collect_saramin(sk)

    # 중복 제거 (URL 우선, 없으면 회사+제목)
    seen, out = set(), []
    for it in items:
        k = it.get("url") or (it["tracker"] + "|" + it["title"])
        if k in seen:
            continue
        seen.add(k); out.append(it)
    out.sort(key=lambda x: x["expiration"] or "9999-99-99")

    (HERE / "jobs.js").write_text(
        "window.JOBS = " + json.dumps({
            "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": ("워크넷 공공 API" if wk else "") + (" + " if wk and sk else "") + ("사람인 API" if sk else ""),
            "items": out,
        }, ensure_ascii=False, indent=1) + ";",
        encoding="utf-8")
    print("─" * 40)
    print(f"완료! 총 {len(out)}건 → jobs.js 저장")

if __name__ == "__main__":
    main()
