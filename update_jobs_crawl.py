# -*- coding: utf-8 -*-
"""
사람인 채용공고 크롤러 v1 — GitHub Actions용
────────────────────────────────────────
API가 아니라 사람인 검색결과 페이지를 직접 파싱 (BeautifulSoup).
개인 구직 목적 · 출처(사람인)와 원문 링크 표시 · 딜레이 준수.
반도체/이차전지 키워드로 검색 → 관심기업이면 강조.
"""
import urllib.request, urllib.parse, ssl, time, datetime, re, json
from pathlib import Path
try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable,"-m","pip","install","beautifulsoup4","--quiet"])
    from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE

HEADERS = {
 "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
 "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
 "Accept-Language":"ko-KR,ko;q=0.9,en;q=0.8",
 "Referer":"https://www.saramin.co.kr/zf_user/",
 "Connection":"keep-alive",
 "Upgrade-Insecure-Requests":"1",
}

FAV = {
 "삼성전자":0,"하이닉스":0,"마이크론":0,"매그나칩":0,"온세미":0,"디비하이텍":0,
 "어플라이드":1,"asml":1,"도쿄일렉트론":1,"램리서치":1,"원익ips":1,"원익아이피":1,"주성":1,"피에스케이":1,
 "유진테크":1,"세메스":1,"케이씨텍":1,"이오테크닉스":1,"지에스티":1,"유니셈":1,"테스":1,
 "네패스":2,"앰코":2,"한미반도체":2,"엘비세미콘":2,"하나마이크론":2,"테스나":2,"에스에프에이":2,"한화세미텍":2,
 "삼성전기":3,"실트론":3,"동진쎄미켐":3,"솔브레인":3,"티씨케이":3,"동우화인켐":3,
 "원익큐엔씨":3,"하나머티리얼즈":3,"코미코":3,"디엔에프":3,"엠케이전자":3,"덕산":3,
 "삼성디스플레이":4,"엘지디스플레이":4,
 "엘지에너지":5,"삼성sdi":5,"에스케이온":5,"포스코퓨처엠":5,"에코프로":5,"엘앤에프":5,
 "대주전자":5,"나노신소재":5,"성일하이텍":5,"롯데에너지":5,"천보":5,
}
def fav_hit(c):
    low=(c or "").lower().replace(" ","").replace("(주)","").replace("㈜","")
    for k,cat in FAV.items():
        if k.replace(" ","") in low: return cat
    return None
def guess_cat(c,t):
    x=(c+" "+t).lower()
    if any(w in x for w in ["배터리","이차전지","2차전지","양극","음극","전해","분리막","셀","리튬"]): return 5
    if any(w in x for w in ["디스플레이","oled","lcd"]): return 4
    if any(w in x for w in ["패키","후공정","본딩","테스트","test"]): return 2
    if any(w in x for w in ["소재","화학","전구체","웨이퍼","포토","레지스트"]): return 3
    if any(w in x for w in ["장비","설비","챔버","증착","식각","etch","cvd"]): return 1
    return 0

KEYWORDS = ["반도체 공정","반도체 장비","반도체 소자","식각","증착","이차전지","배터리 소재","반도체 소재"]

def fetch(keyword, page=1):
    kw=urllib.parse.quote(keyword)
    url=(f"https://www.saramin.co.kr/zf_user/search/recruit?"
         f"searchType=search&searchword={kw}&recruitPage={page}"
         f"&recruitSort=relation&recruitPageCount=40")
    req=urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode("utf-8","replace")

def parse(html):
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for it in soup.select(".item_recruit"):
        # 회사명
        corp=it.select_one(".corp_name a")
        company=corp.get_text(strip=True) if corp else ""
        # 제목
        tit=it.select_one(".job_tit a")
        title=tit.get("title") or (tit.get_text(strip=True) if tit else "")
        href=tit.get("href") if tit else ""
        url="https://www.saramin.co.kr"+href if href.startswith("/") else href
        # 조건(지역/경력/학력/고용형태)
        conds=[s.get_text(strip=True) for s in it.select(".job_condition span")]
        region=conds[0] if conds else ""
        # 마감일 (여러 선택자 시도)
        deadline=""
        for sel in [".job_date .date", ".job_date span.date", ".date", ".job_days", "span.deadlines"]:
            el=it.select_one(sel)
            if el:
                txt=el.get_text(strip=True)
                if txt and ("D-" in txt or "~" in txt or "/" in txt or "마감" in txt or "채용시" in txt or "상시" in txt):
                    deadline=txt; break
                if txt and not deadline:
                    deadline=txt
        # 직무 키워드
        sector=it.select_one(".job_sector")
        sector_txt=sector.get_text(" ",strip=True) if sector else ""
        if not (company and title): continue
        out.append({"company":company,"title":title,"url":url,
                    "region":region,"deadline_raw":deadline,"sector":sector_txt})
    return out

def norm_deadline(s):
    s=(s or "").strip()
    today=datetime.date.today()
    # D-7, D-day 형식
    m=re.search(r"D-(\d+)", s)
    if m:
        return (today+datetime.timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    if "오늘마감" in s or "D-DAY" in s.upper(): return today.strftime("%Y-%m-%d")
    if "내일마감" in s: return (today+datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    # ~MM/DD 또는 MM.DD 또는 ~YYYY.MM.DD
    m=re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", s)
    if m:
        try:
            return datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3))).strftime("%Y-%m-%d")
        except: pass
    m=re.search(r"~?\s*(\d{1,2})[/.](\d{1,2})", s)
    if m:
        mo,da=int(m.group(1)),int(m.group(2))
        y=today.year
        try:
            d=datetime.date(y,mo,da)
            if (d-today).days < -30: d=datetime.date(y+1,mo,da)
            return d.strftime("%Y-%m-%d")
        except: return ""
    return ""  # 상시채용/채용시까지 등은 마감일 없음

def main():
    print("="*50); print("사람인 크롤링 시작 (개인 구직용 · 출처 표시)")
    got={}
    ok_any=False
    for kw in KEYWORDS:
        try:
            html=fetch(kw)
            if not ok_any:
                print(f"  [디버그] '{kw}' 응답 길이 {len(html)}, item_recruit {html.count('item_recruit')}개")
            rows=parse(html)
            if rows: ok_any=True
            n=0
            for r in rows:
                cat=fav_hit(r["company"]); is_fav=cat is not None
                # 관심기업만 담기 (원하면 전체로 확장 가능)
                if cat is None:
                    cat=guess_cat(r["company"],r["title"]+r["sector"])
                    # 관심기업 아니어도 반도체/전지 키워드 맞으면 포함
                key=r["url"] or (r["company"]+r["title"])
                if key in got: continue
                got[key]={"tracker":r["company"],"cat":cat,"company":r["company"],
                    "title":r["title"],"url":r["url"],"region":r["region"],
                    "deadline":norm_deadline(r["deadline_raw"]),
                    "fav":is_fav,"note":("관심기업" if is_fav else "사람인")}
                n+=1
            print(f"  '{kw}': {n}건 (누적 {len(got)})")
        except Exception as e:
            print(f"  '{kw}': 실패 {type(e).__name__}: {str(e)[:60]}")
        time.sleep(0.8)

    items=sorted(got.values(), key=lambda x:(not x["fav"], x["deadline"] or "9999"))
    with_dl=sum(1 for x in items if x["deadline"])
    print(f"[통계] 전체 {len(items)}건 중 마감일 있는 공고: {with_dl}건 (상시/미표기: {len(items)-with_dl}건)")
    # 마감일 있는 것 몇 개 샘플 출력
    samples=[x for x in items if x["deadline"]][:5]
    for x in samples:
        print("   예시: %s | 마감 %s | %s" % (x["company"][:15], x["deadline"], x["title"][:25]))
    save(items)

def save(items):
    out={"generatedAt":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "source":"사람인 크롤링 (출처: 사람인 www.saramin.co.kr)","items":items,"programs":[]}
    (HERE/"jobs.js").write_text("window.JOBS = "+json.dumps(out,ensure_ascii=False,indent=1)+";",encoding="utf-8")
    print("="*50); print(f"완료! {len(items)}건 → jobs.js")
    if not items:
        print("⚠ 0건 — 차단(403)이거나 페이지 구조 변경")

if __name__=="__main__": main()
