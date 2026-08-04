# -*- coding: utf-8 -*-
"""
고용24(work24.go.kr) 채용정보 API 자동수집 v8 — 정확판
──────────────────────────────────────────
공식 명세 기준 정확한 URL + 태그명 사용.
<wanted> 안: company, title, region, closeDt, wantedInfoUrl, wantedAuthNo, career
"반도체/이차전지" 키워드 검색 + 신입(career=N) 우선. 관심기업이면 강조.
"""
import urllib.request, urllib.parse, json, ssl, time, datetime, re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
BASE = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L01.do"

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
def fav_hit(c):
    low=(c or "").lower().replace(" ","")
    for k,cat in FAV.items():
        if k.replace(" ","") in low: return cat
    return None
def guess_cat(c,t):
    x=(c+t).lower()
    if any(w in x for w in ["배터리","이차전지","2차전지","양극","음극","전해","분리막","셀"]): return 5
    if any(w in x for w in ["디스플레이","oled","lcd"]): return 4
    if any(w in x for w in ["패키","후공정","본딩"]): return 2
    if any(w in x for w in ["소재","화학","전구체","웨이퍼"]): return 3
    if any(w in x for w in ["장비","설비","챔버"]): return 1
    return 0

# 코드표(명세): coTp 01대기업 03벤처 04공공 05외국계 09강소 / career N신입
KEYWORDS = ["반도체","이차전지","배터리","반도체장비","반도체소재","디스플레이","웨이퍼","전지"]

def read_key():
    for n in ("worknet_key.txt","api_key.txt"):
        f=HERE/n
        if f.exists():
            k=f.read_text(encoding="utf-8").strip()
            if k: return k
    return None

def norm_date(s):
    s=(s or "").strip()
    m=re.search(r"(\d{4})[-.]?(\d{2})[-.]?(\d{2})",s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

def fetch(key, keyword, page=1):
    params={"authKey":key,"callTp":"L","returnType":"XML",
            "startPage":page,"display":100,"keyword":keyword}
    url=BASE+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/xml,text/xml,*/*"})
    with urllib.request.urlopen(req,timeout=25,context=ctx) as r:
        return r.read().decode("utf-8","replace")

def main():
    key=read_key()
    if not key:
        print("키 없음"); save([]); return
    print("="*50); print(f"고용24 채용정보 수집 (키 {len(key)}자)")

    # 첫 호출로 키 유효성 확인
    try:
        test=fetch(key,"반도체")
        print(f"[디버그] 응답 앞부분: {test[:250].replace(chr(10),' ')}")
        if "유효하지 않은" in test:
            print("⚠ 인증키 오류 — 키 반영 대기(최대 1시간) 또는 키 확인 필요")
            save([]); return
    except Exception as e:
        print(f"⚠ 첫 호출 실패: {type(e).__name__}: {e}")
        save([]); return

    got={}
    for kw in KEYWORDS:
        try:
            xml=fetch(key,kw)
            root=ET.fromstring(xml)
            n=0
            for w in root.iter("wanted"):
                company=(w.findtext("company") or "").strip()
                title=(w.findtext("title") or "").strip()
                if not title: continue
                jid=(w.findtext("wantedAuthNo") or "").strip() or (company+title)
                if jid in got: continue
                cat=fav_hit(company); is_fav=cat is not None
                if cat is None: cat=guess_cat(company,title)
                got[jid]={
                    "tracker":company or "기업","cat":cat,"company":company,"title":title,
                    "url":(w.findtext("wantedInfoUrl") or "").strip(),
                    "deadline":norm_date(w.findtext("closeDt")),
                    "region":(w.findtext("region") or "").strip(),
                    "career":(w.findtext("career") or "").strip(),
                    "fav":is_fav,"note":("관심기업" if is_fav else "고용24")}
                n+=1
            print(f"  '{kw}': {n}건 (누적 {len(got)})")
        except Exception as e:
            print(f"  '{kw}': 실패 {type(e).__name__}: {str(e)[:50]}")
        time.sleep(0.3)

    items=sorted(got.values(), key=lambda x:(not x["fav"], x["deadline"] or "9999"))
    save(items)

def save(items):
    out={"generatedAt":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "source":"고용24 자동수집","items":items,"programs":[]}
    (HERE/"jobs.js").write_text("window.JOBS = "+json.dumps(out,ensure_ascii=False,indent=1)+";",encoding="utf-8")
    print("="*50); print(f"완료! {len(items)}건 → jobs.js")

if __name__=="__main__": main()
