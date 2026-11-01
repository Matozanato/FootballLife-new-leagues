import pefile, struct, sys
EXE=sys.argv[1]
pe=pefile.PE(EXE, fast_load=True)
for s in pe.sections:
    print(s.Name.rstrip(b"\0"), hex(s.VirtualAddress), hex(s.Misc_VirtualSize), hex(s.SizeOfRawData))
