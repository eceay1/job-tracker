# -*- coding: utf-8 -*-
"""
워크넷(고용24) 채용정보 자동수집 — 키워드 기반 v6
─────────────────────────────────────────
회사명이 아니라 "반도체/이차전지" 키워드로 검색해서 관련 공고를 널리 수집.
관심기업이면 강조 표시, 아니어도 반도체/전지 중소·강소기업이면 포함.
→ 대기업은 못 잡아도 중소·강소 공고는 매일 자동으로 쌓임.
"""
import urllib.request, urllib.parse, json, ssl, time, datetime, re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

# 워크넷 API URL (구/신 둘 다 시도)
URLS = [
  "https://openapi.work.go.kr/opi/opi/opia/wantedApi.do",
  "http://openapi.work.go.kr/opi/opi/opia/wantedApi.do",
  "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do",
]

# 관심기업 (있으면 강조) — 트래커 카테고리 매핑
FAV = {
 "삼성전자":0,"하이닉스":0,"마이크론":0,"매그나칩":0,"온세미":0,
 "어플라이드":1,"asml":1,"도쿄일렉트론":1,"램리서치":1,"원익":1,"주성":1,"피에스케이":1,
 "유진테크":1,"테스":1,"케이씨텍":1,"이오테크닉스":1,"지에스티":1,"유니셈":1,
 "네패스":2,"앰코":2,"한미반도체":2,"엘비세미콘":2,"하나마이크론":2,"테스나":2,"에스에프에이":2,
 "삼성전기":3,"실트론":3,"동진쎄미켐":3,"솔브레인":3,"티씨케이":3,"동우화인켐":3,
 "원익큐엔씨":3,"하나머티리얼즈":3,"코미코":3,"디엔에프":3,"엠케이전자":3,
 "삼성디스플레이":4,"엘지디스플레이":4,
 "엘지에너지":5,"삼성sdi":5,"에스케이온":5,"포스코퓨처엠":5,"에코프로":5,"엘앤에프":5,
 "대주전자":5,"나노신소재":5,"성일하이텍":5,
}
def fav_hit(company):
    low=(company or "").lower().replace(" ","")
    for k,cat in FAV.items():
        if k.replace(" ","") in low: return cat
    return None

# 카테고리 추정 (관심기업 아닐 때)
def guess_cat(company, title):
    t=(company+title).lower()
    if any(w in t for w in ["배터리","이차전지","2차전지","양극재","음극재","전해질","분리막","셀"]): return 5
    if any(w in t for w in ["디스플레이","oled","lcd"]): return 4
    if any(w in t for w in ["패키징","후공정","본딩","테스트"]): return 2
    if any(w in t for w in ["소재","화학","전구체","케미","웨이퍼"]): return 3
    if any(w in t for w in ["장비","설비","이송","챔버"]): return 1
    return 0

KEYWORDS = ["반도체","반도체장비","반도체소재","이차전지","배터리소재","디스플레이","웨이퍼","반도체공정","식각","증착","패키징"]

def read_key():
    for name in ("worknet_key.txt","api_key.txt"):
        f=HERE/name
        if f.exists():
            k=f.read_text(encoding="utf-8").strip()
            if k: return k
    return None

def norm_date(s):
    s=(s or "").strip()
    m=re.search(r"(\d{4})[-.]?(\d{2})[-.]?(\d{2})", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def fetch(base, key, keyword, page=1):
    params=urllib.parse.urlencode({
        "authKey":key,"callTp":"L","returnType":"XML",
        "startPage":page,"display":100,"keyword":keyword,
    })
    req=urllib.request.Request(base+"?"+params,
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/xml,text/xml,*/*"})
    with urllib.request.urlopen(req,timeout=20,context=ctx) as r:
        return r.read().decode("utf-8","replace")

def main():
    key=read_key()
    if not key:
        print("키 없음"); return
    print("="*50); print(f"워크넷 키워드 수집 시작 (키 {len(key)}자)")

    # 작동하는 URL 찾기
    base=None
    for u in URLS:
        try:
            xml=fetch(u,key,"반도체")
            if "<wanted" in xml or "wantedRoot" in xml:
                base=u
                print(f"✅ 작동 URL: {u}")
                print(f"   응답 앞부분: {xml[:200].replace(chr(10),' ')}")
                break
            else:
                print(f"   {u.split('//')[1][:30]}: 응답이 이상함 → {xml[:100]}")
        except Exception as e:
            print(f"   {u.split('//')[1][:30]}: {type(e).__name__}: {str(e)[:50]}")
    if not base:
        print("⚠ 모든 URL 실패 — 키 반영 대기중이거나 URL 변경됨")
        # 빈 결과라도 저장
        save([]); return

    got={}
    for kw in KEYWORDS:
        try:
            xml=fetch(base,key,kw)
            root=ET.fromstring(xml)
            n=0
            for w in root.iter("wanted"):
                company=(w.findtext("company") or "").strip()
                title=(w.findtext("title") or "").strip()
                url=(w.findtext("wantedInfoUrl") or "").strip()
                if not title: continue
                jid=(w.findtext("wantedAuthNo") or url or company+title).strip()
                if jid in got: continue
                cat=fav_hit(company)
                is_fav = cat is not None
                if cat is None: cat=guess_cat(company,title)
                got[jid]={
                    "tracker":company,"cat":cat,"company":company,"title":title,
                    "url":url,"deadline":norm_date(w.findtext("closeDt")),
                    "region":(w.findtext("region") or "").strip(),
                    "fav":is_fav,"note":("관심기업" if is_fav else "워크넷"),
                }
                n+=1
            print(f"  '{kw}': {n}건 (누적 {len(got)})")
        except Exception as e:
            print(f"  '{kw}': 실패 {type(e).__name__}: {str(e)[:40]}")
        time.sleep(0.3)

    # 관심기업 우선 정렬
    items=sorted(got.values(), key=lambda x:(not x["fav"], x["deadline"] or "9999"))
    save(items)

def save(items):
    out={"generatedAt":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "source":"워크넷 자동수집","items":items,"programs":[]}
    (HERE/"jobs.js").write_text("window.JOBS = "+json.dumps(out,ensure_ascii=False,indent=1)+";",encoding="utf-8")
    print("="*50); print(f"완료! {len(items)}건 → jobs.js")
    if not items:
        print("⚠ 0건 — 워크넷에 해당 키워드 공고가 없거나 키 반영 대기중")

if __name__=="__main__": main()
