import pefile, struct, sys
EXE=sys.argv[1]; rva=int(sys.argv[2],16); n=int(sys.argv[3])
pe=pefile.PE(EXE, fast_load=True)
f=open(EXE,"rb"); f.seek(pe.get_offset_from_rva(rva)); b=f.read(n)
for i in range(0,n,16): print(hex(0x140000000+rva+i), b[i:i+16].hex(" "))
