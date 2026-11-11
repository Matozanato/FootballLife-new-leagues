import sys,pefile,capstone
E=sys.argv[1]; lo=int(sys.argv[2],16); hi=int(sys.argv[3],16); pats=sys.argv[4:]
pe=pefile.PE(E,fast_load=True); f=open(E,'rb'); f.seek(pe.get_offset_from_rva(lo-0x140000000)); b=f.read(hi-lo)
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64); md.skipdata=True
for ins in md.disasm(b,lo):
    s=ins.mnemonic+' '+ins.op_str
    if any(p in s for p in pats): print(hex(ins.address), s)
