import pefile, struct, sys
EXE=sys.argv[1]
pe=pefile.PE(EXE, fast_load=True)
f=open(EXE,"rb")
def ok(d,r,k): return d<=366 and 0x2a<=r<=0x3f and k<=2
out=[]
for s in pe.sections:
    nm=s.Name.rstrip(b"\0")
    if nm not in (b".rdata",b".data"): continue
    f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
    i=0; n=len(b)-12
    while i<n:
        d,r,k=struct.unpack_from("<III",b,i)
        if ok(d,r,k):
            j=i; recs=[]
            while j<n:
                d,r,k=struct.unpack_from("<III",b,j)
                if not ok(d,r,k): break
                recs.append((d,r,k)); j+=12
            if len(recs)>=2:
                out.append((s.VirtualAddress+i, recs))
                i=j; continue
        i+=4
for rva,recs in out:
    fin=[x for x in recs if x[1]==0x35]
    two = any(x[2]==0 for x in fin) and any(x[2]==1 for x in fin)
    print("%x n=%d %s %s"%(0x140000000+rva,len(recs),"TWO-LEG-FINAL" if two else "", " ".join("%d:%x/%d"%x for x in recs[:24])))
