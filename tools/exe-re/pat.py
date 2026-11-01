import pefile, re, sys
EXE=sys.argv[1]
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
# movzx r32, byte ptr [r64+7]: 0f b6 (modrm with disp8 07) ; or with REX 4x 0f b6
pat=re.compile(rb"\x0f\xb6[\x40-\x7f]\x07.{0,6}?(?:\x83[\xe0-\xe7]\x30|\x24\x30|\x80[\xe0-\xe7]\x30).{0,3}?(?:\x83[\xf8-\xff]\x20|\x3c\x20|\x80[\xf8-\xff]\x20)", re.S)
hits=[base+m.start() for m in pat.finditer(b)]
print(len(hits)); print(" ".join(hex(h) for h in hits[:80]))
