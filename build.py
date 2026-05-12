#!/usr/bin/env python3
"""
Lighthouse Canton — Tactical MA Dashboard & Optimizer
Generates index.html with embedded data. Run daily at market close.
Usage: python build.py
"""
import yfinance as yf, pandas as pd, numpy as np, json, warnings, sys, os
from datetime import datetime, date
warnings.filterwarnings('ignore')

TICKERS=['QQQ','TQQQ','BIL','SPY','QLD','SSO','SPXL']
START='2015-01-01'; BT='2016-01-01'
MA_SHORT=25; MA_LONG=50; LAG=1; TC=0.0003
LARGE_MAS=[100,150,200]
STRATEGIES=[
    ('QQQ 3x',    'QQQ', {'TQQQ':1.0}),
    ('QQQ 2x',    'QQQ', {'QLD':1.0}),
    ('QQQ Blend', 'QQQ', {'QQQ':0.5,'QLD':0.3,'TQQQ':0.2}),
    ('QQQ 1x',    'QQQ', {'QQQ':1.0}),
    ('SPY 3x',    'SPY', {'SPXL':1.0}),
    ('SPY 2x',    'SPY', {'SSO':1.0}),
    ('SPY Blend', 'SPY', {'SPY':0.5,'SSO':0.3,'SPXL':0.2}),
    ('SPY 1x',    'SPY', {'SPY':1.0}),
]

def run():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Downloading data...")
    pd_dict={}
    for t in TICKERS:
        df=yf.download(t,start=START,progress=False,auto_adjust=True)
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        pd_dict[t]=df['Close']
    prices=pd.DataFrame(pd_dict).sort_index().ffill()
    last_date=str(prices.index[-1].date())
    print(f"  Latest data: {last_date}")

    for t in ['QQQ','SPY']:
        prices[f'{t}_MA{MA_SHORT}']=prices[t].rolling(MA_SHORT).mean()
        prices[f'{t}_MA{MA_LONG}']=prices[t].rolling(MA_LONG).mean()
        raw=np.where((prices[t]>prices[f'{t}_MA{MA_SHORT}'])&(prices[t]>prices[f'{t}_MA{MA_LONG}']),2,
                     np.where(prices[t]>prices[f'{t}_MA{MA_LONG}'],1,0)).astype(float)
        prices[f'{t}_sig_exec']=pd.Series(raw,index=prices.index).shift(LAG)
        for ma in LARGE_MAS:
            prices[f'{t}_MA{ma}']=prices[t].rolling(ma).mean()
            below=np.where(np.isnan(prices[f'{t}_MA{ma}']),-1,
                           np.where(prices[t]<=prices[f'{t}_MA{ma}'],1,0)).astype(float)
            prices[f'{t}_below{ma}']=pd.Series(below,index=prices.index).shift(LAG)

    bt=prices[prices.index>=BT].copy()
    rets=bt[TICKERS].pct_change()
    dates=[str(d.date()) for d in bt.index]
    n=len(dates)

    def portfolio(sig_col, bull_alloc, large_ma=None, db_eq=0.0):
        base=sig_col.split('_')[0]
        sigs=bt[sig_col].values
        below_arr=bt[f'{base}_below{large_ma}'].values if large_ma else None
        daily=np.full(n,np.nan); prev=-99
        for i in range(n):
            s=sigs[i]
            if np.isnan(s): prev=-99; continue
            s=int(s)
            eff=-2 if (below_arr is not None and s==0 and not np.isnan(below_arr[i]) and below_arr[i]==1) else s
            if eff==2: ret=sum(w*rets[t].iloc[i] for t,w in bull_alloc.items())
            elif eff==1: ret=0.75*rets[base].iloc[i]+0.25*rets['BIL'].iloc[i]
            elif eff==0: ret=0.5*rets[base].iloc[i]+0.5*rets['BIL'].iloc[i]
            else: ret=db_eq*rets[base].iloc[i]+(1-db_eq)*rets['BIL'].iloc[i]
            if prev!=-99 and eff!=prev: ret-=TC
            daily[i]=ret; prev=eff
        return daily

    def stats(daily):
        v=daily[~np.isnan(daily)]
        if not len(v): return {}
        n_=len(v); yr=n_/252; cum=np.prod(1+v)
        mn=np.mean(v); sd=np.std(v,ddof=0)
        if sd==0: return {}
        cum_arr=np.cumprod(1+v); rm=np.maximum.accumulate(cum_arr); dd=(cum_arr-rm)/rm
        return dict(tr=round((cum-1)*100,1),cagr=round((cum**(1/yr)-1)*100,1),
                    vol=round(sd*np.sqrt(252)*100,1),
                    sharpe=round((mn-0.04/252)/sd*np.sqrt(252),2),dd=round(dd.min()*100,1))

    def monthly_cum(daily):
        fv=next((i for i,v in enumerate(daily) if not np.isnan(v)),None)
        if fv is None: return {}
        cum=1.0; mc={}
        for i in range(fv,n):
            if not np.isnan(daily[i]): cum*=(1+daily[i])
            mc[dates[i][:7]]=round((cum-1)*100,2)
        return mc

    def annual(daily):
        r={}
        for i in range(n):
            if np.isnan(daily[i]): continue
            y=dates[i][:4]; r[y]=r.get(y,1)*(1+daily[i])
        return {y:round((v-1)*100,1) for y,v in r.items()}

    def quarterly(daily):
        r={}
        for i in range(n):
            if np.isnan(daily[i]): continue
            m=int(dates[i][5:7]); y=dates[i][:4]; q=f"{y}Q{(m-1)//3+1}"
            r[q]=r.get(q,1)*(1+daily[i])
        return {k:round((v-1)*100,1) for k,v in r.items()}

    def dd_monthly(daily):
        fv=next((i for i,v in enumerate(daily) if not np.isnan(v)),None)
        if fv is None: return {}
        cum=1.0; pk=1.0; dc={}
        for i in range(fv,n):
            if not np.isnan(daily[i]): cum*=(1+daily[i])
            pk=max(pk,cum); dc[dates[i][:7]]=round((cum-pk)/pk*100,2)
        return dc

    print("  Computing 8 strategies...")
    dash_strats={}
    for name,sig,bull in STRATEGIES:
        d=portfolio(f'{sig}_sig_exec',bull)
        dash_strats[name]=dict(stats=stats(d),monthly_cum=monthly_cum(d),
            annual=annual(d),quarterly=quarterly(d),dd=dd_monthly(d),
            trades=int(sum(1 for i in range(1,n) if not np.isnan(bt[f'{sig}_sig_exec'].iloc[i]) and
                          bt[f'{sig}_sig_exec'].iloc[i]!=bt[f'{sig}_sig_exec'].iloc[i-1] and
                          not np.isnan(bt[f'{sig}_sig_exec'].iloc[i-1]))))

    for bname,tkr in [('QQQ B&H','QQQ'),('SPY B&H','SPY')]:
        sig=f'{tkr}_sig_exec'
        fv=next((i for i in range(n) if not np.isnan(bt[sig].iloc[i])),0)
        bh=np.array([np.nan if i<fv else rets[tkr].iloc[i] for i in range(n)])
        dash_strats[bname]=dict(stats=stats(bh),monthly_cum=monthly_cum(bh),
            annual=annual(bh),quarterly=quarterly(bh),dd=dd_monthly(bh),trades=0)

    cur_sigs={}
    for t in ['QQQ','SPY']:
        s=bt[f'{t}_sig_exec'].iloc[-1]
        cur_sigs[t]=dict(signal=int(s) if not np.isnan(s) else -1,
            price=round(float(bt[t].iloc[-1]),2),
            ma25=round(float(bt[f'{t}_MA{MA_SHORT}'].iloc[-1]),2),
            ma50=round(float(bt[f'{t}_MA{MA_LONG}'].iloc[-1]),2),
            ma150=round(float(bt[f'{t}_MA150'].iloc[-1]),2),
            ma200=round(float(bt[f'{t}_MA200'].iloc[-1]),2))

    def enc_sig(arr): return ''.join('0' if np.isnan(v) else str(int(v)+1) for v in arr)
    def enc_below(arr): return ''.join('0' if np.isnan(v) else str(int(v)+1) for v in arr)
    def enc_rets(arr): return [0 if np.isnan(v) else int(round(v*10000)) for v in arr]

    opt_data=dict(dates=dates,
        signals={t:enc_sig(bt[f'{t}_sig_exec'].values) for t in ['QQQ','SPY']},
        below={t:{str(ma):enc_below(bt[f'{t}_below{ma}'].values) for ma in LARGE_MAS} for t in ['QQQ','SPY']},
        returns={t:enc_rets(rets[t].values) for t in TICKERS})

    dash_data=dict(strategies=dash_strats,signals=cur_sigs,last_updated=last_date)

    dash_json=json.dumps(dash_data,separators=(',',':'))
    opt_json=json.dumps(opt_data,separators=(',',':'))
    print(f"  Dashboard data: {len(dash_json)//1024}KB | Optimizer data: {len(opt_json)//1024}KB")

    # Read HTML template and inject data
    template=open(os.path.join(os.path.dirname(__file__),'template.html')).read()
    html=template.replace('__DASH_DATA__',dash_json).replace('__OPT_DATA__',opt_json)

    # Inline Chart.js if still using CDN placeholder (avoids corporate firewall blocks)
    cdn_tags=['<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>',
              '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>']
    for tag in cdn_tags:
        if tag in html:
            try:
                import urllib.request
                chartjs_url='https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
                with urllib.request.urlopen(chartjs_url,timeout=30) as resp:
                    chartjs=resp.read().decode('utf-8')
                html=html.replace(tag,f'<script>{chartjs}</script>')
                print(f'  Inlined Chart.js ({len(chartjs)//1024}KB)')
            except Exception as e:
                print(f'  Warning: could not inline Chart.js: {e}')
            break
    # Write to root index.html (for GitHub Actions git add index.html)
    out=os.path.join(os.path.dirname(__file__),'index.html')
    open(out,'w').write(html)
    # Also write to public/ for Cloudflare Pages (output directory = public)
    public_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),'public')
    os.makedirs(public_dir,exist_ok=True)
    pub_out=os.path.join(public_dir,'index.html')
    open(pub_out,'w').write(html)
    print(f"  Also written: {pub_out}")
    print(f"  Generated: {out} ({len(html)//1024}KB)")
    print(f"[OK] Build complete — data through {last_date}")

if __name__=='__main__':
    run()
