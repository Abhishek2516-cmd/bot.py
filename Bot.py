import os, json, requests, yfinance as yf, pandas as pd
from datetime import datetime, timezone

TOKEN=os.environ["8562495673:AAFO93ZjJ4g6X9sQ3EbalRiNNZlsC3L3DJM"]; CHAT=os.environ["6842570365"]
FILE="signals.json"

def send(m):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id":CHAT,"text":m})

def get(sym, itv="15m", period="5d"):
    d=yf.download(sym,interval=itv,period=period,progress=False)
    d.columns=d.columns.get_level_values(0)
    d.index=d.index.tz_convert("UTC") if d.index.tz else d.index.tz_localize("UTC")
    return d

def news_near():
    try:
        r=requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",timeout=10).json()
        now=datetime.now(timezone.utc)
        for e in r:
            if e["country"]=="USD" and e["impact"]=="High":
                t=datetime.fromisoformat(e["date"]).astimezone(timezone.utc)
                if abs((t-now).total_seconds())<1800:
                    return True
    except Exception:
        pass
    return False

def trend_up(sym):
    d=get(sym)
    return d["Close"].iloc[-1] > d["Close"].rolling(20).mean().iloc[-1]

def load():
    try: return json.load(open(FILE))
    except Exception: return []

def save(sigs):
    json.dump(sigs, open(FILE,"w"), indent=1)

def stats(sigs):
    tp=sum(1 for s in sigs if s["status"]=="TP")
    sl=sum(1 for s in sigs if s["status"]=="SL")
    n=tp+sl
    wr=(tp/n*100) if n else 0
    return f"Total closed: {n} | TP: {tp} | SL: {sl} | Win rate: {wr:.0f}%"

def check_results(sigs, df):
    now=pd.Timestamp.now(tz="UTC")
    for s in sigs:
        if s["status"]!="OPEN": continue
        t=pd.Timestamp(s["time"])
        res=None
        for _,r in df[df.index>t].iterrows():
            if s["side"]=="BUY":
                hit_sl = r["Low"]<=s["sl"]; hit_tp = r["High"]>=s["tp"]
            else:
                hit_sl = r["High"]>=s["sl"]; hit_tp = r["Low"]<=s["tp"]
            if hit_sl: res="SL"; break
            if hit_tp: res="TP"; break
        if not res and (now-t).total_seconds()>48*3600:
            res="EXPIRED"
        if res:
            s["status"]=res
            icon={"TP":"✅","SL":"❌","EXPIRED":"⏱"}[res]
            send(f"{icon} GOLD {s['side']} {res}\nEntry {s['entry']:.2f} | SL {s['sl']:.2f} | TP {s['tp']:.2f}\n{stats(sigs)}")

df=get("GC=F")
sigs=load()
check_results(sigs, df)   # result check hamesha chalega

# filters (sirf naye signal ke liye)
if (7 <= datetime.now(timezone.utc).hour < 17) and not news_near():
    dxy_up=trend_up("DX-Y.NYB"); tnx_up=trend_up("^TNX")

    res=df["High"].iloc[-34:-3].max()
    sup=df["Low"].iloc[-34:-3].min()
    atr=float((df["High"]-df["Low"]).rolling(14).mean().iloc[-2])
    s=df.iloc[-3]; k=df.iloc[-2]; a=df.iloc[-4]
    sid=lambda side: f"{side}-{df.index[-3].isoformat()}"
    known={x["id"] for x in sigs}

    def fire(side, e, sl, tp, icon):
        sigs.append({"id":sid(side),"time":df.index[-2].isoformat(),"side":side,
                     "entry":e,"sl":sl,"tp":tp,"status":"OPEN"})
        send(f"{icon} GOLD {side} (15m)\nEntry {e:.2f}\nSL {sl:.2f}\nTP {tp:.2f}\n"
             f"OB zone {s['Low']:.2f}-{s['High']:.2f}\nResistance {res:.2f} | Support {sup:.2f}\n"
             f"Bias: DXY {'up' if dxy_up else 'down'}, US10Y {'up' if tnx_up else 'down'}\n"
             f"Liquidity sweep + FVG")

    if s["High"]>res and s["Close"]<res and k["High"]<a["Low"] and dxy_up and sid("SELL") not in known:
        e=float(k["Close"]); sl=float(s["High"])+atr*0.3
        fire("SELL", e, sl, e-2*(sl-e), "🔴")

    if s["Low"]<sup and s["Close"]>sup and k["Low"]>a["High"] and not dxy_up and sid("BUY") not in known:
        e=float(k["Close"]); sl=float(s["Low"])-atr*0.3
        fire("BUY", e, sl, e+2*(e-sl), "🟢")

save(sigs)