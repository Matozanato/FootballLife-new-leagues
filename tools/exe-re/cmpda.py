import pefile,sys,capstone,re
E=sys.argv[1]; pe=pefile.PE(E,fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(E,'rb'); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData); base=0x140000000+s.VirtualAddress
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
hits=[]
for m in re.finditer(rb'\x81[\xf8-\xff]\xda\x00\x00\x00|\x83[\xf8-\xff]\xda|\x3d\xda\x00\x00\x00|\x81[\xf8-\xff]\xd9\x00\x00\x00|\x3d\xd9\x00\x00\x00', b):
    p=m.start()
    for back in (0,1):
        ins=list(md.disasm(b[p-back:p-back+12], base+p-back, count=1))
        if ins and ('0xda' in ins[0].op_str or '0xd9' in ins[0].op_str) and ins[0].mnemonic=='cmp':
            hits.append((ins[0].address, ins[0].op_str)); break
print(len(hits))
for a,o in hits: print(hex(a),o)
