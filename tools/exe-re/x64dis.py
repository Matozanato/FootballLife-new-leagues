import sys, pefile, capstone, mmap
EXE=sys.argv[1]; rva=int(sys.argv[2],16); n=int(sys.argv[3]) if len(sys.argv)>3 else 200
pe=pefile.PE(EXE, fast_load=True)
base=pe.OPTIONAL_HEADER.ImageBase
off=pe.get_offset_from_rva(rva)
f=open(EXE,"rb"); f.seek(off); code=f.read(n*8)
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.skipdata=True
for i,ins in enumerate(md.disasm(code, base+rva)):
    print("%x  %-8s %s"%(ins.address, ins.mnemonic, ins.op_str))
    if i>=n: break
