import struct, sys, os
def utf_table(b):
    assert b[:4]==b'@UTF', b[:4]
    size=struct.unpack('>I',b[4:8])[0]; t=b[8:8+size]
    rows_off,str_off,data_off,name_off,ncol,rowlen,nrows=struct.unpack('>IIIIHHI',t[0:24])
    rows_off+=0; strs=t[str_off:data_off]
    def s(o):
        e=strs.index(b'\0',o); return strs[o:e].decode('latin1')
    cols=[]; p=24; const={}
    for i in range(ncol):
        fl=t[p]; p+=1; nm=s(struct.unpack('>I',t[p:p+4])[0]); p+=4
        typ=fl&0xf; stor=fl&0xf0
        val=None
        if stor==0x30:
            val,p=read(t,p,typ,s,data_off)
        cols.append((nm,typ,stor,val))
    out=[]
    for r in range(nrows):
        p=rows_off+r*rowlen; row={}
        for nm,typ,stor,val in cols:
            if stor==0x50: v,p=read(t,p,typ,s,data_off)
            elif stor==0x30: v=val
            else: v=None
            row[nm]=v
        out.append(row)
    return out
def read(t,p,typ,s,data_off):
    if typ in (0,1): return t[p],p+1
    if typ in (2,3): return struct.unpack('>H',t[p:p+2])[0],p+2
    if typ in (4,5): return struct.unpack('>I',t[p:p+4])[0],p+4
    if typ in (6,7): return struct.unpack('>Q',t[p:p+8])[0],p+8
    if typ==8: return struct.unpack('>f',t[p:p+4])[0],p+4
    if typ==0xa: return s(struct.unpack('>I',t[p:p+4])[0]),p+4
    if typ==0xb: o,l=struct.unpack('>II',t[p:p+8]); return (o,l),p+8
    raise Exception('typ %x'%typ)
def toc(f):
    h=open(f,'rb'); h.seek(0x10); hdr=h.read(0x800)
    H=utf_table(hdr)[0]
    to=H.get('TocOffset'); co=H.get('ContentOffset') or 0
    if not to: return []
    h.seek(to+0x10); raw=h.read(H['TocSize'])
    rows=utf_table(raw)
    base=min(to,co) if co else to
    res=[]
    for r in rows:
        name=(r.get('DirName') or '')+'/'+(r.get('FileName') or '')
        res.append((name, base+r['FileOffset'], r['FileSize'], r.get('ExtractSize')))
    return res
if __name__=='__main__':
    pat=sys.argv[1].encode().decode()
    for f in sys.argv[2:]:
        try:
            for n,o,sz,es in toc(f):
                if pat in n: print(f, n, o, sz, es)
        except Exception as e: print(f, 'ERR', e)
