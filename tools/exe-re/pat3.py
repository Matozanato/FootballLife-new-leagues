import pefile, re, sys
EXE=sys.argv[1]
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
for name,p in {"cmp eax,0x350000":rb"\x3d\x00\x00\x35\x00","cmp r,0x350000":rb"\x81[\xf8-\xff]\x00\x00\x35\x00","cmp r,0x360000":rb"(?:\x3d|\x81[\xf8-\xff])\x00\x00\x36\x00"}.items():
    hits=[base+m.start() for m in re.finditer(p,b)]
    near=[h for h in hits if b.find(b"\x00\x00\x00\x20",h-base-40,h-base+40)!=-1]
    print(name,len(hits),"near 0x20000000:",[hex(h) for h in near][:20])
