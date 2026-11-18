import osmium, struct, math, sys
from collections import defaultdict
W,S,E,N = 74.45, 42.76, 74.76, 42.97
WALK = {"footway","path","pedestrian","steps","living_street","residential","service","unclassified","tertiary","tertiary_link",
        "secondary","secondary_link","primary","primary_link","trunk","trunk_link","track","corridor","road","cycleway","bridleway"}
def inb(lon,lat): return W-0.01<=lon<=E+0.01 and S-0.01<=lat<=N+0.01
class H(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.ways=[]; s.loc={}
    def way(s,w):
        t=w.tags; hw=t.get("highway")
        if hw not in WALK: return
        foot=t.get("foot"); acc=t.get("access")
        if foot=="no" or (acc in ("private","no") and foot not in ("yes","designated","permissive")): return
        if hw in ("trunk","trunk_link") and t.get("sidewalk","") in ("no","none") : return
        refs=[]
        try:
            for n in w.nodes:
                if not n.location.valid(): refs=None; break
                refs.append(n.ref); s.loc[n.ref]=(n.location.lon, n.location.lat)
        except Exception: return
        if refs and any(inb(*s.loc[r]) for r in refs): s.ways.append(refs)
h=H(); h.apply_file(sys.argv[1], locations=True)
print("ways", len(h.ways))
use=defaultdict(int)
for refs in h.ways:
    for i,r in enumerate(refs): use[r]+= 2 if i in (0,len(refs)-1) else 1
lat0=math.radians((S+N)/2); KX=111320*math.cos(lat0); KY=110540
def d(a,b):
    return math.hypot((a[0]-b[0])*KX,(a[1]-b[1])*KY)
vid={}; V=[]; edges=[]
def v(r):
    if r not in vid: vid[r]=len(V); V.append(h.loc[r])
    return vid[r]
for refs in h.ways:
    start=0
    for i in range(1,len(refs)):
        if use[refs[i]]>=2 or i==len(refs)-1:
            seg=refs[start:i+1]
            if len(seg)>=2 and seg[0]!=seg[-1] or len(seg)>2:
                L=sum(d(h.loc[seg[k]],h.loc[seg[k+1]]) for k in range(len(seg)-1))
                if L>0.05: edges.append((v(seg[0]),v(seg[-1]),L,[h.loc[x] for x in seg[1:-1]]))
            start=i
print("V",len(V),"E",len(edges))
# largest component
adj=defaultdict(list)
for i,(a,b,L,p) in enumerate(edges): adj[a].append(b); adj[b].append(a)
comp=[-1]*len(V); best=None; c=0; sizes=[]
for s0 in range(len(V)):
    if comp[s0]!=-1: continue
    st=[s0]; comp[s0]=c; n=0
    while st:
        x=st.pop(); n+=1
        for y in adj[x]:
            if comp[y]==-1: comp[y]=c; st.append(y)
    sizes.append(n); c+=1
big=max(range(c), key=lambda i:sizes[i]); print("components",c,"largest",sizes[big],"of",len(V))
keep=[i for i in range(len(V)) if comp[i]==big]; remap={o:n for n,o in enumerate(keep)}
V2=[V[i] for i in keep]; E2=[(remap[a],remap[b],L,p) for a,b,L,p in edges if comp[a]==big]
# encode: header, vertices int32 µdeg, edges (a,b uint32, len float32, npts uint16), points as int16 deltas from previous point (escape if too big)
pts=bytearray(); ebuf=bytearray()
def q(x): return int(round(x*1e6))
for a,b,L,p in E2:
    prev=(q(V2[a][0]),q(V2[a][1])); enc=bytearray(); n=0
    for (lo,la) in p:
        cur=(q(lo),q(la)); dx=cur[0]-prev[0]; dy=cur[1]-prev[1]
        if abs(dx)>32000 or abs(dy)>32000: raise SystemExit("delta too big")
        enc+=struct.pack("<hh",dx,dy); prev=cur; n+=1
    ebuf+=struct.pack("<IIfH",a,b,L,n); pts+=enc
vbuf=b"".join(struct.pack("<ii",q(lo),q(la)) for lo,la in V2)
out=b"RWG1"+struct.pack("<III",len(V2),len(E2),len(pts)//4)+vbuf+bytes(ebuf)+bytes(pts)
open(sys.argv[2],"wb").write(out); print("bytes",len(out), "km", round(sum(e[2] for e in E2)/1000))
