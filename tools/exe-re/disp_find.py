import pefile, sys, capstone, re
EXE=sys.argv[1]; disps=[int(x,16) for x in sys.argv[2:]]
pe=pefile.PE(EXE, fast_load=True)
s=[s for s in pe.sections if s.Name.rstrip(b"\0")==b".trace"][0]
f=open(EXE,"rb"); f.seek(s.PointerToRawData); b=f.read(s.SizeOfRawData)
base=0x140000000+s.VirtualAddress
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
for d in disps:
    pat=d.to_bytes(4,'little'); hits=0
    for m in re.finditer(re.escape(pat), b):
        p=m.start()
        for back in range(2,10):
            st=p-back
            ins=list(md.disasm(b[st:st+15], base+st, count=1))
            if ins and ins[0].size>=back+4 and hex(d) in ins[0].op_str:
                print("%#x  %x  %s %s"%(d, ins[0].address, ins[0].mnemonic, ins[0].op_str)); hits+=1; break
    print("# %#x: %d"%(d,hits))
