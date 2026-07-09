# -*- coding: utf-8 -*-
"""Find flash-free footage windows using per-frame luma profiles (/tmp/lum_<stem>.txt).
A window is 'clean' if no frame is near-black and no frame is a bright/dark 1-2 frame spike
vs its local neighbours. Avoids overlapping other scenes' windows in the same source."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as S

DUR = {d['id']: d['dur'] for d in json.load(open(os.path.join(os.path.dirname(__file__),'durations.json')))}

def load(stem):
    rows=[]; pt=None
    for line in open(f'/tmp/lum_{stem}.txt'):
        line=line.strip()
        if line.startswith('frame:'):
            for tok in line.split():
                if tok.startswith('pts_time:'): pt=float(tok.split(':')[1])
        elif 'YAVG' in line:
            try: rows.append((pt, float(line.split('=')[1])))
            except: pass
    rows.sort()
    return rows

PROF={}
def prof(stem):
    if stem not in PROF: PROF[stem]=load(stem)
    return PROF[stem]

def clean(stem, t0, t1, black=18, spike=32):
    seg=[(t,y) for t,y in prof(stem) if t0-0.05<=t<=t1+0.05]
    if len(seg)<5: return False,'thin'
    for i,(t,y) in enumerate(seg):
        if y<black: return False, f'black{y:.0f}@{t:.1f}'
        lo=max(0,i-4); hi=min(len(seg),i+5)
        nb=sorted(v for _,v in seg[lo:hi]); m=nb[len(nb)//2]
        if y>m+spike or y<m-spike: return False, f'spike{y:.0f}/{m:.0f}@{t:.1f}'
    return True,'ok'

def windows_per_source(skip):
    out={}
    for sc in S.SCENES:
        if sc['id']==skip: continue
        d=DUR[sc['id']]
        if sc.get('clips'):
            seg=d/len(sc['clips'])
            for stem,t in sc['clips']: out.setdefault(stem,[]).append((t,t+seg))
        else: out.setdefault(sc['src'],[]).append((sc['tin'],sc['tin']+d))
    return out

def free(stem, t0, t1, taken, margin=0.5):
    for a,b in taken.get(stem,[]):
        if min(t1,b)-max(t0,a) > -margin: return False
    return True

def find(sid, cands, margin_in=0.25):
    D=DUR[sid]; taken=windows_per_source(sid)
    for stem,(rs,re) in cands:
        t=rs
        while t+D <= re:
            # keep window edges margin_in inside (away from region ends)
            ok,why=clean(stem, t, t+D)
            if ok and free(stem, t, t+D, taken):
                return stem, round(t,1), why
            t+=0.2
    return None

# scene -> candidate (stem, (region_start, region_end)) list, in priority order
PLAN = {
  'S11': [('ao2022',(477,503))],
  'S15': [('wimby2008',(38,58)), ('wimby2008',(170,210)), ('wimby2008',(210,250))],
  'S18': [('rg_tribute',(46,64)), ('rg_tribute',(208,243)), ('rg_tribute',(158,176))],
  'S20': [('trailer_main',(37,71)), ('firstlook',(26,55)), ('nadal_djok',(200,260))],
  'S23': [('rg_tribute',(74,100)), ('rg_tribute',(208,243))],
}
for sid,cands in PLAN.items():
    r=find(sid,cands)
    print(f"{sid} (D={DUR[sid]:.1f}s): {r}")
