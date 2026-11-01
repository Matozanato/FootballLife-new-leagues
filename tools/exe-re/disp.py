import pefile, re, sys, collections
EXE=sys.argv[1]; lo=int(sys.argv[2],16); hi=int(sys.argv[3],16)
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
c=collections.defaultdict(list)
for m in re.finditer(rb"[\x80-\xbf].[\x00-\xff][\x00-\xff]\x79\x01|[\x80-\xbf][\x00-\xff][\x00-\xff]\x79\x01", b):
    pass
import struct
for i in range(len(b)-4):
    if b[i+3]==0x01 and b[i+2] in (0x79,0x7a,0x7b):
        v=struct.unpack_from("<I",b,i)[0]
        if lo<=v<hi: c[v].append(base+i)
for v in sorted(c): print(hex(v), len(c[v]), " ".join(hex(x) for x in c[v][:6]))
