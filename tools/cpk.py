import struct, sys

def utf_parse(data):
    assert data[:4]==b'@UTF', data[:4]
    size, = struct.unpack('>I', data[4:8])
    b = data[8:8+size]
    rows_off, strings_off, data_off, table_name, n_cols, row_len, n_rows = struct.unpack('>IIIIHHI', b[:24])
    def gstr(o):
        e=b.index(b'\0', strings_off+o)
        return b[strings_off+o:e].decode('utf-8','replace')
    cols=[]; p=24
    for _ in range(n_cols):
        flags=b[p]; p+=1
        noff,=struct.unpack('>I', b[p:p+4]); p+=4
        name=gstr(noff)
        storage=flags&0xf0; typ=flags&0x0f
        const=None
        if storage==0x30:  # constant
            const,p = read_val(b,p,typ,gstr)
        cols.append((name,storage,typ,const))
    rows=[]
    for r in range(n_rows):
        p = rows_off + r*row_len
        row={}
        for name,storage,typ,const in cols:
            if storage==0x30: row[name]=const
            elif storage==0x10: row[name]=None
            else:
                v,p = read_val(b,p,typ,gstr)
                row[name]=v
        rows.append(row)
    return rows

def read_val(b,p,typ,gstr):
    fmt={0:('>B',1),1:('>b',1),2:('>H',2),3:('>h',2),4:('>I',4),5:('>i',4),6:('>Q',8),7:('>q',8),8:('>f',4)}
    if typ in fmt:
        f,n=fmt[typ]; v,=struct.unpack(f,b[p:p+n]); return v,p+n
    if typ==0xa:
        o,=struct.unpack('>I',b[p:p+4]); return gstr(o),p+4
    if typ==0xb:
        o,s=struct.unpack('>QI',b[p:p+12]); return ('DATA',o,s),p+12
    raise Exception('type %x'%typ)

f=open(sys.argv[1],'rb')
hdr=f.read(16)
assert hdr[:4]==b'CPK '
f.seek(16)
utfsize,=struct.unpack('<Q', hdr[8:16])
cpk=utf_parse(f.read(utfsize+8) if False else open(sys.argv[1],'rb').read(16+utfsize+8)[16:])[0]
toc=cpk.get('TocOffset')
f.seek(toc)
t=f.read(16)
assert t[:4]==b'TOC ', t[:4]
tsize,=struct.unpack('<Q', t[8:16])
f.seek(toc+16)
rows=utf_parse(f.read(tsize+8))
for r in rows:
    print('%12d  %s/%s'%(r.get('FileSize',0), r.get('DirName',''), r.get('FileName','')))
