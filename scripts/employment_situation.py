#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,html,io,json,re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

SERIES={
"payroll_change":{"series_id":"CES0000000001","table":"B-1","unit":"thousands of jobs, over-the-month change","seasonal_adjustment":"seasonally adjusted"},
"unemployment_rate":{"series_id":"LNS14000000","table":"A-1","unit":"percent","seasonal_adjustment":"seasonally adjusted"},
"labor_force_participation_rate":{"series_id":"LNS11300000","table":"A-1","unit":"percent","seasonal_adjustment":"seasonally adjusted"},
"average_hourly_earnings":{"series_id":"CES0500000003","table":"B-3","unit":"US dollars per hour","seasonal_adjustment":"seasonally adjusted"},
}
MONTHS={m:f"{i:02d}" for i,m in enumerate("JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER".split(),1)}

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]
    def handle_data(self,d):
        if d.strip(): self.parts.append(d.strip())
def plain(raw):
    p=Text(); p.feed(raw.decode()); return html.unescape(re.sub(r"\s+"," "," ".join(p.parts))).strip()
def one(pat,text,label):
    m=re.search(pat,text,re.I)
    if not m: raise ValueError(f"missing or malformed {label}")
    return m
def jobs_to_thousands(value):
    jobs=int(value.replace(",",""))
    if jobs % 1000: raise ValueError("payroll jobs value is not expressed in whole thousands")
    return jobs//1000
def parse_release(raw:bytes,*,source_url:str,retrieved_at:str):
    t=plain(raw)
    rid=one(r"USDL-\s*(\d{2}-\d+).*?8:30\s*a\.m\.\s*\(ET\)\s*(?:Friday|Thursday|Wednesday|Tuesday|Monday),\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",t,"release identity")
    ref=one(r"THE EMPLOYMENT SITUATION\s*-\s*([A-Za-z]+)\s+(\d{4})",t,"reference month")
    rmn,ry=ref.group(1).upper(),int(ref.group(2)); rm=int(MONTHS[rmn])
    pm=one(r"Total nonfarm payroll employment\s+(increased|rose|decreased|declined) by\s+([\d,]+)\s+in\s+"+ref.group(1),t,"payroll")
    payroll=jobs_to_thousands(pm.group(2))
    if pm.group(1).lower() in {"decreased","declined"}: payroll=-payroll
    ur=float(one(r"unemployment rate .*? at\s+(\d+(?:\.\d+)?)\s+percent",t,"unemployment rate").group(1))
    part=float(one(r"labor force participation rate .*? to\s+(\d+(?:\.\d+)?)\s+percent",t,"participation").group(1))
    ahe=float(one(r"average hourly earnings for all employees on private nonfarm payrolls .*? to\s+\$(\d+(?:\.\d+)?)",t,"earnings").group(1))
    rev=one(r"change in total nonfarm payroll employment for\s+([A-Za-z]+)\s+was revised\s+(?:up|down)\s+by\s+([\d,]+),\s+from\s+([+-]?[\d,]+)\s+to\s+([+-]?[\d,]+),\s+and the change for\s+([A-Za-z]+)\s+was revised\s+(?:up|down)\s+by\s+([\d,]+),\s+from\s+([+-]?[\d,]+)\s+to\s+([+-]?[\d,]+)",t,"revisions")
    revisions=[]
    for groups in [(1,2,3,4),(5,6,7,8)]:
        mon,amt,prev,new=[rev.group(i) for i in groups]
        mi=int(MONTHS[mon.upper()]); yy=ry if mi<rm else ry-1
        prevk,newk,amtk=map(jobs_to_thousands,(prev,new,amt))
        if abs(newk-prevk)!=amtk: raise ValueError("revision arithmetic mismatch")
        revisions.append({"reference_month":f"{yy}-{mi:02d}","previously_published_thousands":prevk,"revised_thousands":newk,"revision_thousands":newk-prevk})
    relmon=int(MONTHS[rid.group(2).upper()]); relday=int(rid.group(3)); relyear=int(rid.group(4))
    release_time=datetime(relyear,relmon,relday,8,30,tzinfo=ZoneInfo("America/New_York")).isoformat()
    payload={"schema_version":1,"publisher":"U.S. Bureau of Labor Statistics","dataset":"Employment Situation",
      "reference_month":f"{ry}-{rm:02d}","release_id":f"USDL-{rid.group(1)}","release_timestamp":release_time,
      "retrieved_at":retrieved_at,"source_url":source_url,"evidence_kind":"normalized_release_excerpt","evidence_sha256":hashlib.sha256(raw).hexdigest(),
      "verification_state":"VERIFIED_HISTORICAL_RELEASE","series":SERIES,
      "metrics":{"payroll_change":float(payroll),"unemployment_rate":ur,"labor_force_participation_rate":part,"average_hourly_earnings":ahe},
      "payroll_revisions":revisions}
    validate_snapshot(payload); return payload

def validate_snapshot(p):
    required={"schema_version","publisher","dataset","reference_month","release_id","release_timestamp","retrieved_at","source_url","evidence_kind","evidence_sha256","verification_state","series","metrics","payroll_revisions"}
    if required-p.keys(): raise ValueError(f"snapshot missing fields: {sorted(required-p.keys())}")
    if p["schema_version"]!=1 or p["dataset"]!="Employment Situation": raise ValueError("unsupported schema")
    if p["series"]!=SERIES: raise ValueError("series/table identity mismatch")
    if set(p["metrics"])!=set(SERIES): raise ValueError("metric identity mismatch")
    if not str(p["source_url"]).startswith("https://www.bls.gov/news.release/archives/empsit_"): raise ValueError("source URL is not archived BLS Employment Situation")
    if p["evidence_kind"]!="normalized_release_excerpt": raise ValueError("unsupported evidence kind")
    if not re.fullmatch(r"[0-9a-f]{64}",str(p["evidence_sha256"])): raise ValueError("invalid evidence hash")
    if p["verification_state"]!="VERIFIED_HISTORICAL_RELEASE": raise ValueError("snapshot is not verified historical release")
    if len(p["payroll_revisions"])!=2: raise ValueError("two revisions required")
    for r in p["payroll_revisions"]:
        if r["revised_thousands"]-r["previously_published_thousands"]!=r["revision_thousands"]: raise ValueError("revision arithmetic mismatch")

def jbytes(x): return (json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
def render(p):
    validate_snapshot(p)
    latest={k:p[k] for k in ["schema_version","dataset","reference_month","release_timestamp","retrieved_at","verification_state","series","metrics","payroll_revisions"]}
    latest["authority"]="KAFKA2306/econalert"; latest["source"]={"url":p["source_url"],"evidence_sha256":p["evidence_sha256"],"evidence_kind":p["evidence_kind"],"release_id":p["release_id"]}
    s=io.StringIO(); w=csv.writer(s,lineterminator="\n"); w.writerow(["reference_month","release_timestamp","metric","series_id","value","unit","seasonal_adjustment"])
    for name,m in SERIES.items(): w.writerow([p["reference_month"],p["release_timestamp"],name,m["series_id"],p["metrics"][name],m["unit"],m["seasonal_adjustment"]])
    jb=jbytes(latest); cb=s.getvalue().encode()
    manifest={"schema_version":1,"dataset":"Employment Situation","reference_month":p["reference_month"],"evidence_sha256":p["evidence_sha256"],"outputs":{"latest.json":hashlib.sha256(jb).hexdigest(),"latest.csv":hashlib.sha256(cb).hexdigest()}}
    return {"latest.json":jb,"latest.csv":cb,"manifest.json":jbytes(manifest)}
def write_outputs(snapshot,out,check=False):
    p=json.loads(Path(snapshot).read_text()); outputs=render(p); out=Path(out)
    if check:
        for n,b in outputs.items():
            if not (out/n).exists() or (out/n).read_bytes()!=b: raise SystemExit(f"generated output is stale: {out/n}")
    else:
        out.mkdir(parents=True,exist_ok=True)
        for n,b in outputs.items(): (out/n).write_bytes(b)
def fetch_release(url):
    with urlopen(Request(url,headers={"User-Agent":"econalert/1.0 github.com/KAFKA2306/econalert"}),timeout=60) as r:return r.read()
def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    c=sp.add_parser("collect"); c.add_argument("--url",required=True); c.add_argument("--retrieved-at",required=True); c.add_argument("--output",type=Path,required=True)
    b=sp.add_parser("build"); b.add_argument("--snapshot",type=Path,required=True); b.add_argument("--output-dir",type=Path,default=Path("api/v1/employment-situation")); b.add_argument("--check",action="store_true")
    a=ap.parse_args()
    if a.cmd=="collect":
        p=parse_release(fetch_release(a.url),source_url=a.url,retrieved_at=a.retrieved_at); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_bytes(jbytes(p))
    else: write_outputs(a.snapshot,a.output_dir,a.check)
if __name__=="__main__": main()
