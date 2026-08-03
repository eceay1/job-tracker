# -*- coding: utf-8 -*-
"""채용 트래커 자동 수집 v5 — 원티드 공개 API (다중 엔드포인트 자동 시도)"""
import urllib.request, urllib.parse, json, ssl, time, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA = {
  "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
  "Accept":"application/json, text/plain, */*",
  "Accept-Language":"ko-KR,ko;q=0.9",
  "Referer":"https://www.wanted.co.kr/search",
  "Origin":"https://www.wanted.co.kr",
}
COMPANIES = [
 ("삼성전자 DS",["삼성전자"],0),("SK하이닉스",["하이닉스","hynix"],0),("마이크론코리아",["마이크론","micron"],0),
 ("매그나칩반도체",["매그나칩","magnachip"],0),("온세미",["온세미","onsemi"],0),
 ("어플라이드머티어리얼즈",["어플라이드","applied"],1),("ASML코리아",["asml","에이에스엠엘"],1),
 ("도쿄일렉트론코리아",["도쿄일렉트론","tokyo electron"],1),("램리서치코리아",["램리서치","lam research"],1),
 ("원익IPS",["원익아이피","wonik ips","원익 ips"],1),("주성엔지니어링",["주성","jusung"],1),("PSK",["피에스케이"],1),
 ("유진테크",["유진테크"],1),("테스",["(주)테스","주식회사 테스"],1),("케이씨텍",["케이씨텍","kc tech"],1),
 ("이오테크닉스",["이오테크닉스","eo technics"],1),("GST",["글로벌스탠다드","gst"],1),("유니셈",["유니셈","unisem"],1),
 ("네패스",["네패스","nepes"],2),("앰코",["앰코","amkor"],2),("한미반도체",["한미반도체"],2),
 ("LB세미콘",["엘비세미콘","lb semicon"],2),("하나마이크론",["하나마이크론"],2),("두산테스나",["테스나","tesna"],2),
 ("SFA반도체",["에스에프에이반도체","sfa semicon"],2),
 ("삼성전기",["삼성전기"],3),("SK실트론",["실트론","siltron"],3),("동진쎄미켐",["동진쎄미켐"],3),
 ("솔브레인",["솔브레인","soulbrain"],3),("티씨케이",["티씨케이"],3),("동우화인켐",["동우화인켐"],3),
 ("원익QnC",["원익큐엔씨","wonik qnc"],3),("하나머티리얼즈",["하나머티리얼즈"],3),("코미코",["코미코","komico"],3),
 ("디엔에프",["디엔에프"],3),("미코",["(주)미코"],3),("엠케이전자",["엠케이전자"],3),
 ("삼성디스플레이",["삼성디스플레이"],4),("LG디스플레이",["엘지디스플레이","lg display"],4),
 ("LG에너지솔루션",["엘지에너지","lg energy"],5),("삼성SDI",["삼성sdi","삼성에스디아이"],5),("SK온",["에스케이온","sk on"],5),
 ("포스코퓨처엠",["포스코퓨처엠"],5),("에코프로비엠",["에코프로비엠"],5),("엘앤에프",["엘앤에프"],5),
 ("에코프로머티리얼즈",["에코프로머티리얼"],5),("SK아이이테크놀로지",["아이이테크놀로지"],5),
 ("대주전자재료",["대주전자"],5),("나노신소재",["나노신소재"],5),("성일하이텍",["성일하이텍"],5),
]
KEYWORDS = ["반도체","이차전지","공정","소자","배터리"]

def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20, context=ctx) as res:
        return json.loads(res.read().decode("utf-8","replace"))

def endpoints(kw, offset):
    e = urllib.parse.quote(kw)
    return [
     f"https://www.wanted.co.kr/api/chaos/search/v1/results?country=kr&job_sort=job.latest_order&years=-1&locations=all&limit=100&offset={offset}&keyword={e}",
     f"https://www.wanted.co.kr/api/v4/jobs?country=kr&job_sort=job.latest_order&years=-1&limit=100&offset={offset}&keyword={e}",
     f"https://www.wanted.co.kr/api/chaos/navigation/v1/results?country=kr&job_sort=job.latest_order&years=-1&limit=100&offset={offset}&keyword={e}",
    ]

def dig_list(obj):
    """응답 어디에 잡 리스트가 있든 찾아냄"""
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        for key in ("data","results","jobs","job_list","list"):
            if key in obj:
                v = dig_list(obj[key])
                if v: return v
    return []

def comp_name(j):
    c = j.get("company")
    if isinstance(c, dict): return c.get("name","")
    if isinstance(c, str): return c
    return j.get("company_name","") or ""

def match(comp):
    low = (comp or "").lower()
    for disp, keys, cat in COMPANIES:
        if any(k.lower() in low for k in keys): return disp, cat
    return None

def main():
    print("="*50); print("원티드 공개 API 수집 v5")
    working_ep = None; got_map = {}
    dbg = False
    for kw in KEYWORDS:
        n=0
        for url in endpoints(kw,0):
            try:
                data = http_json(url)
                if not dbg:
                    print(f"  [디버그] 성공 엔드포인트: {url.split('/api/')[1][:40]}")
                    print(f"  [디버그] 응답 최상위 키: {list(data.keys())[:8] if isinstance(data,dict) else 'list'}")
                    dbg=True
                jobs = dig_list(data)
                for j in jobs:
                    if not isinstance(j, dict): continue
                    hit = match(comp_name(j))
                    if not hit: continue
                    jid = j.get("id") or j.get("job_id")
                    u = f"https://www.wanted.co.kr/wd/{jid}" if jid else ""
                    if not u or u in got_map: continue
                    got_map[u] = {"tracker":hit[0],"cat":hit[1],"company":comp_name(j),
                       "title":j.get("position") or j.get("name") or j.get("title") or "",
                       "url":u,"deadline":"","note":"원티드"}
                    n+=1
                if jobs: break
            except Exception as ex:
                print(f"  '{kw}' 실패: {type(ex).__name__}: {str(ex)[:60]}")
        print(f"  '{kw}': +{n} (누적 {len(got_map)})")
        time.sleep(0.4)
    items=list(got_map.values())
    (HERE/"jobs.js").write_text("window.JOBS = "+json.dumps(
       {"generatedAt":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source":"원티드 공개 API","items":items}, ensure_ascii=False,indent=1)+";",encoding="utf-8")
    print("="*50); print(f"완료! 총 {len(items)}건 → jobs.js")

if __name__=="__main__": main()
