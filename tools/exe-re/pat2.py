import pefile, re, sys
EXE=sys.argv[1]
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
pats={
 "dword>>28&3==2": rb"\xc1[\xe8-\xef]\x1c(?:\x83[\xe0-\xe7]\x03|\x24\x03).{0,4}?(?:\x83[\xf8-\xff]\x02|\x3c\x02|\x80[\xf8-\xff]\x02)",
 "byte>>4&3==2": rb"\xc0[\xe8-\xef]\x04(?:\x83[\xe0-\xe7]\x03|\x24\x03|\x80[\xe0-\xe7]\x03).{0,4}?(?:\x83[\xf8-\xff]\x02|\x3c\x02|\x80[\xf8-\xff]\x02)",
 "and 0x30000000 ==0x20000000": rb"\x25\x00\x00\x00\x30.{0,3}\x3d\x00\x00\x00\x20",
 "byte&0x30==0x20": rb"(?:\x24\x30|\x80[\xe0-\xe7]\x30|\x83[\xe0-\xe7]\x30).{0,3}?(?:\x3c\x20|\x80[\xf8-\xff]\x20|\x83[\xf8-\xff]\x20)",
}
for k,p in pats.items():
    hits=[base+m.start() for m in re.finditer(p,b,re.S)]
    print(k,len(hits)," ".join(hex(h) for h in hits[:40]))
