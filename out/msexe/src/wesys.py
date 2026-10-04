import sys,zlib,struct,os
p=sys.argv[1]; d=open(p,'rb').read()
if d[3:8]==b'WESYS':
    csz,usz=struct.unpack('<II',d[8:16])
    out=zlib.decompress(d[16:16+csz])
    print(p,'csz',csz,'usz',usz,'got',len(out))
    open(p+'.dec','wb').write(out)
else:
    print(p,'not wesys')
