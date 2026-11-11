import pefile, sys, numpy as np
EXE=sys.argv[1]; targets=[int(x,16) for x in sys.argv[2:]]
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
d=np.frombuffer(b,dtype=np.uint8); n=len(b)-5
op=d[0:n]
v=(d[1:n+1].astype(np.int64) | (d[2:n+2].astype(np.int64)<<8) | (d[3:n+3].astype(np.int64)<<16) | (d[4:n+4].astype(np.int64)<<24))
v=np.where(v>=2**31, v-2**32, v)
tgt=np.arange(n,dtype=np.int64)+base+5+v
for t in targets:
    hits=np.nonzero((tgt==t)&((op==0xe8)|(op==0xe9)))[0]
    print(hex(t), [hex(base+h) for h in hits[:400]])
