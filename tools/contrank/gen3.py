# fl26contrank: the clubs the world ranking leaves out (past its 750 entries), for the filtered screens
import struct, capstone
MODE, ADDED, TABLE = 0x000, 0x008, 0x100
EXTRA = 0x1000
D_TEAMS, D_COUNT, D_RCOUNT, D_SENT = 0x1200, 0x1208, 0x1210, 0x1218
D_SLOT9 = 0x1220   # dword: 1 = fl26slot7 is in, the slot is +0x41c | +0x41b << 8 (9 bits)
POINTS, PUSH, BACK = 0x1413225d0, 0x140b115c0, 0x140b10ac9
class Asm:
    def __init__(s, at): s.at=at; s.b=bytearray(); s.lab={}; s.fix=[]
    def raw(s,h): s.b+=bytes.fromhex(h.replace(' ',''))
    def label(s,n): s.lab[n]=s.at+len(s.b)
    def rip(s,h,target,tail=b''):
        s.raw(h); s.fix.append(('rip',len(s.b),target,len(tail))); s.b+=b'\0'*4+tail
    def j(s,h,n): s.raw(h); s.fix.append(('j',len(s.b),n,0)); s.b+=b'\0'*4
    def imm64(s,h,v): s.raw(h); s.b+=struct.pack('<Q',v)
    def done(s):
        for k,o,t,tail in s.fix:
            end=s.at+o+4+tail
            tgt=t if k=='rip' else s.lab[t]
            s.b[o:o+4]=struct.pack('<i',tgt-end)
        return bytes(s.b)
a=Asm(EXTRA)
a.rip('833d',MODE,b'\0')             # cmp dword [mode],0
a.j('0f84','out')
a.raw('53 56 57 55 4154 4155 4156 4157 4883ec40')
a.raw('4d89fc')                      # mov r12,r15 (block)
a.rip('488b05',D_TEAMS); a.raw('4d8d2c04')    # r13 = block + team array
a.rip('488b05',D_COUNT); a.raw('458b3404')    # r14d = team count
a.rip('488b05',D_RCOUNT); a.raw('418b2c04')   # ebp = world ranking count
a.rip('488b05',D_SENT); a.raw('8b30')         # esi = empty-slot id
a.raw('31ff 4531ff')                 # i = 0, eligible = 0
a.label('loop')
a.raw('4439f7'); a.j('0f83','renum')
a.raw('89f8 4869c090060000 498d540500')   # rdx = team i
a.raw('8b02 39f0'); a.j('0f84','next')
a.raw('f782200400000000001c'); a.j('0f85','next')
# the slot test of the world ranking build (0x141324ded), as it is now: fl26slot7's stub
# (0x163c00108: 9 bits from +0x41c/+0x41b) or the game's 7 bits. Slots 251 and 379 are not 123.
a.rip('833d',D_SLOT9,b'\0'); a.j('0f84','slot7')
a.raw('0fb7821b040000 66c1c008 25ff010000 83f87b'); a.j('0f84','next'); a.j('e9','slotok')
a.label('slot7')
a.raw('8a821c040000 247f 3c7b'); a.j('0f84','next')
a.label('slotok')
a.raw('41ffc7 4139ef'); a.j('0f86','next')   # still inside the world ranking
a.raw('0fb78218040000 3d00020000'); a.j('0f83','next')
a.rip('488d0d',TABLE); a.raw('0fb60401'); a.rip('3b05',MODE); a.j('0f85','next')
a.raw('4889542430 31c9'); a.imm64('48b8',POINTS); a.raw('ffd0')
a.raw('488b542430 8b0a 894c2420 c744242400000000 6689442428 668944242a')
a.raw('488d8b98000000 488d542420'); a.imm64('48b8',PUSH); a.raw('ffd0')
a.rip('ff05',ADDED)
a.label('next'); a.raw('ffc7'); a.j('e9','loop')
a.label('renum')                     # key +4 = 0x10000 - points, for every entry
a.raw('488b8398000000 488b8ba0000000')
a.label('k'); a.raw('4839c8'); a.j('0f83','done')
a.raw('0fb7500a f7da 81c200000100 895004 4883c010'); a.j('e9','k')
a.label('done'); a.raw('4883c440 415f 415e 415d 415c 5d 5f 5e 5b')
a.label('out'); a.raw('488b93a0000000 ff2500000000'); a.b+=struct.pack('<Q',BACK)
code=a.done()
print(len(code)); print(code.hex())
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
for i in md.disasm(code,EXTRA):
    x=''
    if 'rip' in i.op_str:
        t=i.op_str.split('rip')[1].split(']')[0].replace(' ',''); x='  -> page+%x'%(i.address+i.size+(int(t,16) if t else 0))
    print('  %x %s %s%s'%(i.address,i.mnemonic,i.op_str,x))
