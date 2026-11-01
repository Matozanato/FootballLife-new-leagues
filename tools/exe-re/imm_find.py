import pefile, sys, capstone, re
EXE=sys.argv[1]; vals=[int(x,16) for x in sys.argv[2:]]
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
for v in vals:
    pat=v.to_bytes(4,'little'); n=0
    for m in re.finditer(re.escape(pat), b):
        p=m.start()
        for back in range(1,10):
            ins=list(md.disasm(b[p-back:p-back+15], base+p-back, count=1))
            if ins and ins[0].size>=back+4 and hex(v) in ins[0].op_str:
                print("%#x %x %s %s"%(v,ins[0].address,ins[0].mnemonic,ins[0].op_str)); n+=1; break
    print("#",hex(v),n)
