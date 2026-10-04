import struct, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec=importlib.util.spec_from_file_location("cpkmod", os.path.join(os.path.dirname(os.path.abspath(__file__)),"cpk.py"))
# reuse parser by copy
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"cpk.py")).read().split("f=open(sys.argv[1]")[0])

def crilayla(src, exsize):
    # CRILAYLA decompression
    assert src[:8]==b'CRILAYLA'
    usize, hsize = struct.unpack('<II', src[8:16])
    out = bytearray(src[16+hsize:16+hsize+0x100])  # raw header (uncompressed prefix)
    dest = bytearray(usize)
    # bit reader from end backwards
    data = src[16:16+hsize]
    pos = len(data)-1
    bitpool=0; bitcount=0
    def getbits(n):
        nonlocal pos,bitpool,bitcount
        v=0
        while n>0:
            if bitcount==0:
                bitpool=data[pos]; pos-=1; bitcount=8
            t=min(n,bitcount)
            v=(v<<t)|((bitpool>>(bitcount-t))&((1<<t)-1))
            bitcount-=t; n-=t
        return v
    outpos=usize-1
    vle=[2,3,5,8]
    while outpos>=0:
        if getbits(1):
            ref = getbits(13)+3
            lvl=0; ln=3
            while True:
                b=getbits(vle[lvl] if lvl<4 else 8)
                ln+=b
                if lvl<3:
                    if b!=(1<<vle[lvl])-1: break
                    lvl+=1
                else:
                    if b!=255: break
            for _ in range(ln):
                dest[outpos]=dest[outpos+ref]; outpos-=1
        else:
            dest[outpos]=getbits(8); outpos-=1
    return bytes(out)+bytes(dest)

path=sys.argv[1]; outdir=sys.argv[2]; pats=sys.argv[3:]
f=open(path,'rb')
hdr=f.read(16); utfsize,=struct.unpack('<Q',hdr[8:16])
cpk=utf_parse(f.read(utfsize+8))[0]
toc=cpk['TocOffset']; ca=cpk.get('ContentOffset',0)
base=min(toc,ca) if ca else toc
f.seek(toc); t=f.read(16); tsize,=struct.unpack('<Q',t[8:16])
rows=utf_parse(f.read(tsize+8))
for r in rows:
    full=r['DirName']+'/'+r['FileName']
    if pats and not any(p in full for p in pats): continue
    f.seek(toc+r['FileOffset'] if False else base+r['FileOffset'])
    d=f.read(r['FileSize'])
    if r['ExtractSize']>r['FileSize'] and d[:8]==b'CRILAYLA':
        d=crilayla(d,r['ExtractSize'])
    op=os.path.join(outdir, full.replace('/',os.sep))
    os.makedirs(os.path.dirname(op),exist_ok=True)
    open(op,'wb').write(d)
    print(len(d), full)
