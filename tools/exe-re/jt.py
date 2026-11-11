import pefile, struct, sys
EXE=sys.argv[1]
pe=pefile.PE(EXE, fast_load=True); f=open(EXE,"rb")
def rd(rva,n): f.seek(pe.get_offset_from_rva(rva)); return f.read(n)
idx=rd(0x15802e8,0xaf); offs=rd(0x15801ec,4*64)
from collections import defaultdict
m=defaultdict(list)
for r in range(1,0xb0):
    i=idx[r-1]; o=struct.unpack_from("<i",offs,4*i)[0]
    m[0x140000000+o].append(r)
want={0x14157f924:"e7c0 (224/227,28/31,...)",0x14157fa3c:"f308 167/174",0x14157f9e7:"f168 170/171"}
for t,regs in sorted(m.items()):
    print(hex(t), regs)
