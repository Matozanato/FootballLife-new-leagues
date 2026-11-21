r"""matchid32.py [--review]  -> the patches that stop the game cutting a match id to 16 bits

u32 match ids, step M4 (notes/plan-zahtjevi-limiti-0411.md, 05.11.). With `fl26match` handing out
ids from 65536 up, every lookup of an id below 65536 is a site that cut it on its way; fl26match
finds the record anyway (the id's low word + 65536, unique while the table is under 131072) and
logs the call site (modules\fl26match.stats, "cut ... from"). This rewrites the cuts those logs
lead to, round by round, each read by hand:

    movzx r32, r16       ->  mov r32, r32         (the id came in whole, in a dword register)
    movzx r32, ax        ->  nop                  (the register already holds the dword it was read as)
    movzx r32, word [m]  ->  mov r32, dword [m]   (m is a dword: the u32 day list, a dword vector)

None of them grows. An empty slot stays 0x0000ffff, so every `cmp r32, 0xffff` after them keeps
its meaning (fl26match never hands out an id whose low word is 0xffff).

Not here (they are storage, not code): the fixture slot's two ids (+8/+0xa of a slot, accessors
0x1414d6380 / 0x1414d6420 / 0x1414d6450), the per-club schedule (writer 0x14158cfb0) and the
block fields +0x17894b8 / +0x181c570. Round 1 (05.11., m4a: 31 sites, 22.7 M cuts to 20.09)
leaves them cut; the lookup still finds their records while the table is under 131072.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# va: (the instruction as shipped, what it becomes) -- every one read in place (05.11.)
SITES = {
    # 0x141350290 puts a match on a calendar day: id in r8w, cut into r12d, stored into the day
    # (a dword since M2) and handed on four times
    0x1413502a0: ("movzx r12d, r8w", "mov r12d, r8d"),
    0x1413502e0: ("movzx edx, r12w", "mov edx, r12d"),
    0x1413503f9: ("movzx edx, r12w", "mov edx, r12d"),
    0x141350415: ("movzx r8d, r12w", "mov r8d, r12d"),
    0x141350461: ("movzx ebx, r12w", "mov ebx, r12d"),
    # 0x1413504b0 (called from it): id in r8w
    0x1413504c4: ("movzx ebx, r8w", "mov ebx, r8d"),
    0x1413504cf: ("movzx edx, bx", "mov edx, ebx"),
    # 0x141341b00 and 0x141349300: id in edx, cut on the way to the lookup
    0x141341b15: ("movzx edx, bx", "mov edx, ebx"),
    0x141349316: ("movzx edx, r14w", "mov edx, r14d"),
    # readers of a day's list (dword reads since M2) that cut what they read
    0x14151cd2f: ("movzx ecx, ax", "mov ecx, eax"),
    0x14151cd3e: ("movzx edx, cx", "mov edx, ecx"),
    0x1415252b3: ("movzx eax, ax", "nop"),
    0x1415252ba: ("movzx edx, ax", "mov edx, eax"),
    0x1414c9043: ("movzx esi, ax", "mov esi, eax"),
    0x1414c904e: ("movzx edx, si", "mov edx, esi"),
    0x14134bd3d: ("movzx ecx, ax", "mov ecx, eax"),
    0x14134bd4c: ("movzx edx, cx", "mov edx, ecx"),
    0x141333b88: ("movzx eax, ax", "nop"),
    0x141333b9d: ("movzx edx, ax", "mov edx, eax"),
    0x1412f9130: ("movzx ecx, ax", "mov ecx, eax"),
    0x1412f913f: ("movzx edx, cx", "mov edx, ecx"),
    0x1414c91c5: ("movzx ecx, ax", "mov ecx, eax"),
    0x1414c91d0: ("movzx edx, cx", "mov edx, ecx"),
    # 0x14158cb30 walks a vector of dword ids (cmp dword [rdi], 0xffff; add rdi, 4)
    0x14158cb38: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
}


# Round 2 (05.11. evening): fl26match now reads a fixture slot itself (0x1414d6380, the slot's
# clubs pick between L and L + 65536) and hands the id back whole in eax. Its 67 callers cut it at
# once (`movzx r32, ax`); these are the cuts on the way to a lookup, a dword store, or a call that
# takes the id (0x141350290 from round 1, 0x141343820 whose only callers are these). Found by
# following eax forward from every call, both branch ways (scratchpad idflow.py), each flagged
# path read by hand. Left cut on purpose: 0x141349e2a (compared with a word read from a store),
# 0x1414d647c (only compared with 0xffff), and the per-club schedule's word store 0x14158d263 /
# 0x14158d39f (32 clubs, its entry has no room left).
ROUND2 = {
    0x140af8b24: ("movzx eax, ax", "mov eax, eax"),
    0x140af8b3f: ("movzx eax, ax", "mov eax, eax"),
    0x140af9e60: ("movzx edx, ax", "mov edx, eax"),
    0x140af9e79: ("movzx edx, ax", "mov edx, eax"),
    0x140afa932: ("movzx eax, ax", "mov eax, eax"),
    0x140ca1b94: ("movzx edx, ax", "mov edx, eax"),
    0x140ca1baf: ("movzx edx, ax", "mov edx, eax"),
    0x140ca1d83: ("movzx edx, ax", "mov edx, eax"),
    0x140ca28f3: ("movzx edx, ax", "mov edx, eax"),
    0x140ca60df: ("movzx ebx, ax", "mov ebx, eax"),
    0x140ca60f7: ("movzx ebx, ax", "mov ebx, eax"),
    0x140ca60ff: ("movzx edx, bx", "mov edx, ebx"),
    0x140ca6380: ("movzx edx, ax", "mov edx, eax"),
    0x140ca67bd: ("movzx edi, ax", "mov edi, eax"),
    0x140ca67d6: ("movzx edi, ax", "mov edi, eax"),
    0x140ca67d9: ("movzx edx, di", "mov edx, edi"),
    0x140ca6a86: ("movzx edx, ax", "mov edx, eax"),
    0x140ca776a: ("movzx ebx, ax", "mov ebx, eax"),
    0x140ca7782: ("movzx ebx, ax", "mov ebx, eax"),
    0x140ca778a: ("movzx edx, bx", "mov edx, ebx"),
    0x140ca7a5f: ("movzx edx, ax", "mov edx, eax"),
    0x140ca801e: ("movzx edx, ax", "mov edx, eax"),
    0x140ca811c: ("movzx edx, ax", "mov edx, eax"),
    0x140ca8137: ("movzx edx, ax", "mov edx, eax"),
    0x140ca85ec: ("movzx edi, ax", "mov edi, eax"),
    0x140ca8605: ("movzx edi, ax", "mov edi, eax"),
    0x140ca8608: ("movzx edx, di", "mov edx, edi"),
    0x140ca886f: ("movzx edx, ax", "mov edx, eax"),
    0x140cab4bb: ("movzx eax, ax", "mov eax, eax"),
    0x140cab4d3: ("movzx eax, ax", "mov eax, eax"),
    0x140cabe3f: ("movzx eax, ax", "mov eax, eax"),
    0x140cabe57: ("movzx eax, ax", "mov eax, eax"),
    0x140cac162: ("movzx eax, ax", "mov eax, eax"),
    0x140cac179: ("movzx eax, ax", "mov eax, eax"),
    0x140fc910a: ("movzx eax, ax", "mov eax, eax"),
    0x140fc9114: ("movzx edx, ax", "mov edx, eax"),
    0x14134379f: ("movzx r8d, ax", "mov r8d, eax"),
    0x1413437bf: ("movzx r8d, ax", "mov r8d, eax"),
    0x1413437e5: ("movzx r8d, ax", "mov r8d, eax"),
    0x141343849: ("movzx edx, bx", "mov edx, ebx"),
    0x141349e4a: ("movzx eax, ax", "mov eax, eax"),
    0x141349e54: ("movzx edx, ax", "mov edx, eax"),
    0x14134dcea: ("movzx eax, ax", "mov eax, eax"),
    0x14134dcf4: ("movzx edx, ax", "mov edx, eax"),
    0x141350c3e: ("movzx esi, ax", "mov esi, eax"),
    0x141350c4d: ("movzx edx, si", "mov edx, esi"),
    0x141350cec: ("movzx r8d, si", "mov r8d, esi"),
    0x1413f61ba: ("movzx eax, ax", "mov eax, eax"),
    0x1413f61c4: ("movzx edx, ax", "mov edx, eax"),
    0x1413f635a: ("movzx eax, ax", "mov eax, eax"),
    0x1413f6364: ("movzx edx, ax", "mov edx, eax"),
    0x1414e330e: ("movzx eax, ax", "mov eax, eax"),
    0x1414e331c: ("movzx edx, ax", "mov edx, eax"),
    0x141510b75: ("movzx eax, ax", "mov eax, eax"),
    0x141510b9a: ("movzx eax, ax", "mov eax, eax"),
    0x141514e44: ("movzx edx, ax", "mov edx, eax"),
    0x141515021: ("movzx edx, ax", "mov edx, eax"),
    0x141515063: ("movzx edx, ax", "mov edx, eax"),
    0x14151507f: ("movzx edx, ax", "mov edx, eax"),
    0x1415153a8: ("movzx edx, ax", "mov edx, eax"),
    0x1415153c3: ("movzx edx, ax", "mov edx, eax"),
    0x14154432a: ("movzx esi, ax", "mov esi, eax"),
    0x141545905: ("movzx edx, ax", "mov edx, eax"),
    0x141545b64: ("movzx edx, ax", "mov edx, eax"),
    0x141546e5a: ("movzx edi, ax", "mov edi, eax"),
    0x141546e89: ("movzx edx, di", "mov edx, edi"),
    0x141548a0a: ("movzx eax, ax", "mov eax, eax"),
    0x141548a18: ("movzx edx, ax", "mov edx, eax"),
    0x14158d0ca: ("movzx r14d, ax", "mov r14d, eax"),
    0x14158d0d8: ("movzx r15d, ax", "mov r15d, eax"),
    0x14158d0e9: ("movzx r12d, ax", "mov r12d, eax"),
    0x14158d234: ("movzx edx, di", "mov edx, edi"),
    0x14158d370: ("movzx edx, di", "mov edx, edi"),
    0x141fc5d5d: ("movzx eax, ax", "mov eax, eax"),
    0x141fc5d6b: ("movzx edx, ax", "mov edx, eax"),
    # round 3 (05.11., the season to 20.09 under the detector): the day rebuild 0x141314350 read
    # every id off the calendar, cut it and wrote it back cut -- after one rebuild all 44796
    # matches sat on their days as low words
    0x141314447: ("movzx esi, ax", "mov esi, eax"),
    0x14131445a: ("movzx edx, si", "mov edx, esi"),
    # day-list readers the elem4 set widened to dword reads and that then cut the id
    0x14151ae75: ("movzx ecx, ax", "mov ecx, eax"),
    0x14151ae84: ("movzx edx, cx", "mov edx, ecx"),
    0x14151c504: ("movzx ecx, ax", "mov ecx, eax"),
    0x14151c513: ("movzx edx, cx", "mov edx, ecx"),
    0x141548247: ("movzx ebx, ax", "mov ebx, eax"),
    0x141548269: ("movzx edx, bx", "mov edx, ebx"),
    0x14152662a: ("movzx edx, ax", "mov edx, eax"),          # 0x1414c8fd0's id, whole
    # the id is handed in by pointer to a dword (both check `cmp dword [rcx], 0xffff` first)
    0x14154fc8f: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
    0x14154ee8a: ("movzx edx, word ptr [rsi]", "mov edx, dword ptr [rsi]"),
    0x14158c378: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),   # a vector of dwords
    0x14154eecc: ("movzx edx, di", "mov edx, edi"),          # edi = that dword, read whole
    0x14154ef16: ("movzx edx, di", "mov edx, edi"),
    0x14154e6ce: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),   # its one caller: ee50's rsi
    # has(ptr) 0x1414bb950: fl26match reads it as a dword (its m_has); 6 of its 7 callers store
    # one here (each slot is a dword the function also uses as one, hand-checked 05.11.), the 7th
    # sits in the protector's code and stores a word, which m_has falls back to
    0x140caef92: ("mov word ptr [rsp + 0x38], r14w", "mov dword ptr [rsp + 0x38], r14d"),
    0x140cb0766: ("mov word ptr [rbp + 0x48], bx", "mov dword ptr [rbp + 0x48], ebx"),
    0x141273022: ("mov word ptr [rbp - 0x4c], ax", "mov dword ptr [rbp - 0x4c], eax"),  # a movzx'd word
    0x1413212c9: ("mov word ptr [rbp + 0x6f], ax", "mov dword ptr [rbp + 0x6f], eax"),
    0x1413212e1: ("movzx edx, word ptr [rbp + 0x6f]", "mov edx, dword ptr [rbp + 0x6f]"),
    0x1414d63bd: ("mov word ptr [rsp + 0x50], cx", "mov dword ptr [rsp + 0x50], ecx"),   # a movzx'd word
    0x141546e65: ("mov word ptr [rsp + 0x90], di", "mov dword ptr [rsp + 0x90], edi"),
    0x141548258: ("mov word ptr [rsp + 0x58], bx", "mov dword ptr [rsp + 0x58], ebx"),
    # dword-held ids (checked as a dword against 0xffff) read back as a word for lookup()
    0x14128064c: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14128085c: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14128113c: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14129d98c: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
    0x14129ddec: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
    0x141350a48: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
    0x141517ea8: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14151b5fb: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14151b7f8: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14151d6a8: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
    0x14151dbd4: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14152b07d: ("movzx edx, word ptr [rdi]", "mov edx, dword ptr [rdi]"),
    0x14152c84a: ("movzx edx, word ptr [r14]", "mov edx, dword ptr [r14]"),
    0x141545368: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14154dd1f: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    # MatchId* helpers (every caller passes a dword id: checked by slotw.py / callers.py)
    0x1415139c2: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x141514bc0: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14154e3bf: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14154f4fe: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14154f69b: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x1415098df: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14151c7f8: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x1415504ec: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    # the day loop 0x141333ad0 hands the match record on: its dword id at +0 read as a word into dword slots
    0x141332137: ("movzx eax, word ptr [rsi]", "mov eax, dword ptr [rsi]"),
    0x14133234e: ("movzx eax, word ptr [rax]", "mov eax, dword ptr [rax]"),
    0x141331d8e: ("movzx eax, word ptr [r14]", "mov eax, dword ptr [r14]"),
    0x14154fffc: ("movzx eax, word ptr [rdi]", "mov eax, dword ptr [rdi]"),
    0x141333e85: ("movzx ecx, word ptr [r15]", "mov ecx, dword ptr [r15]"),
    0x141333f2c: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x141333fb2: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x1413343df: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x141334401: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x14133442d: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x1413344ec: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x14133450e: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x14134af78: ("movzx eax, word ptr [rdi]", "mov eax, dword ptr [rdi]"),
    0x14134aeeb: ("movzx eax, word ptr [rcx]", "mov eax, dword ptr [rcx]"),
    0x14134af0d: ("movzx eax, word ptr [rcx]", "mov eax, dword ptr [rcx]"),
    0x141528314: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    # 0x14151c130 (id by value in ecx) cut it to bx for lookup(); its day-loop caller 0x141331810 read the word
    0x14151c141: ("movzx edx, bx", "mov edx, ebx"),
    0x141331835: ("movzx ecx, word ptr [rdx]", "mov ecx, dword ptr [rdx]"),
    # the rest of that family (byval.py: ecx kept in a register, cut to 16 bits for lookup())
    0x141510b51: ("movzx edx, di", "mov edx, edi"),
    0x141510e4a: ("movzx edx, r14w", "mov edx, r14d"),
    0x141510f28: ("movzx edx, r14w", "mov edx, r14d"),
    0x14151530f: ("movzx edx, si", "mov edx, esi"),
    0x14151bf51: ("movzx edx, bx", "mov edx, ebx"),
    0x14151d591: ("movzx edx, bx", "mov edx, ebx"),
    0x14154ed91: ("movzx edx, bx", "mov edx, ebx"),
    0x141509269: ("movzx edx, bx", "mov edx, ebx"),     # ebx = the id 0x141510b30 hands back
    # and their callers in the day loop's match checks (the register holds the match record)
    0x141331841: ("movzx ecx, word ptr [rdi]", "mov ecx, dword ptr [rdi]"),
    0x141331882: ("movzx ecx, word ptr [rdi]", "mov ecx, dword ptr [rdi]"),
    0x14133191b: ("movzx ecx, word ptr [rdi]", "mov ecx, dword ptr [rdi]"),
    0x141332b11: ("movzx ecx, word ptr [rsi]", "mov ecx, dword ptr [rsi]"),
    0x141332b2a: ("movzx ecx, word ptr [rsi]", "mov ecx, dword ptr [rsi]"),
    0x141332e53: ("movzx ecx, word ptr [rbx]", "mov ecx, dword ptr [rbx]"),
    0x141332ec1: ("movzx ecx, word ptr [rbx]", "mov ecx, dword ptr [rbx]"),
    0x141332e9e: ("movzx ecx, word ptr [rbx]", "mov ecx, dword ptr [rbx]"),   # missed between the two above: a cup tie on a twin id ran its extra time on the other match and the goal list came back empty (m6b crash 0x141333485, 05.11.)
    # the same rereads of the record id in 0x141514c40 and 0x141515300 (rsi = the record, +0x1c.. its goals; wordcall.py)
    0x1415150f0: ("movzx ecx, word ptr [rsi]", "mov ecx, dword ptr [rsi]"),
    0x1415151ce: ("movzx ecx, word ptr [rsi]", "mov ecx, dword ptr [rsi]"),
    0x141515481: ("movzx ecx, word ptr [rsi]", "mov ecx, dword ptr [rsi]"),
    0x1415154a0: ("movzx ecx, word ptr [rsi]", "mov ecx, dword ptr [rsi]"),
    # the line-up builder 0x141332010 (rsi = the record): it handed the cut id to 0x1414ff0e0, which built the
    # squads of the other twin, so 0x141332f90 found nobody of this club to score and crashed (m6c, 17.10., sibword.py)
    0x1413321dc: ("movzx edi, word ptr [rsi]", "mov edi, dword ptr [rsi]"),
    0x1413321ee: ("movzx edx, di", "mov edx, edi"),
    0x141332206: ("movzx r9d, word ptr [rsi]", "mov r9d, dword ptr [rsi]"),
    # 0x1414c9800 (is it a cup tie of this competition) takes the id by value; every caller zero-extends a word or passes the dword
    0x1414c980f: ("movzx edi, dx", "mov edi, edx"),
    0x1414c9815: ("cmp dx, ax", "cmp edx, eax"),
    0x1414c981f: ("movzx edx, di", "mov edx, edi"),
    0x14150990b: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),   # its tail call, rbx = the record (0x1415098df reads it whole)
    # 0x1413340e0 (r15 = the record, 0x1413343df reads it whole) passes the id on in a dword
    0x141334397: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x1413344a9: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    # the same with the id in edx (byval.py on edx), and the result-entry caller 0x14134aa50 (r13 = the record)
    0x141349d41: ("movzx edx, bx", "mov edx, ebx"),
    0x141545259: ("movzx edx, bx", "mov edx, ebx"),     # it already checks the dword against 0xffff
    0x14134ac5a: ("movzx ecx, word ptr [r13]", "mov ecx, dword ptr [r13]"),
    0x14134ac74: ("movzx edx, word ptr [r13]", "mov edx, dword ptr [r13]"),
    # 0x141510000 finds a match on the day lists and returns its record's id (0xffff = none)
    0x14151015a: ("movzx eax, word ptr [r15]", "mov eax, dword ptr [r15]"),
    0x1412ab7a9: ("movzx edx, ax", "mov edx, eax"),
    0x14218a47e: ("movzx edx, ax", "mov edx, eax"),
    0x14218a80e: ("movzx edx, ax", "mov edx, eax"),
    # every day-cap clamp walk: the id read as a dword, then cut back to a word on its way to
    # lookup() (clampcut.py over the 63 clamp sites, 05.11.)
    0x140caea43: ("movzx edx, ax", "mov edx, eax"),
    0x140caea84: ("movzx esi, ax", "mov esi, eax"),
    0x140fc22fa: ("movzx ecx, ax", "mov ecx, eax"),
    0x140fc2309: ("movzx edx, cx", "mov edx, ecx"),
    0x140fc2555: ("movzx ecx, ax", "mov ecx, eax"),
    0x140fc2564: ("movzx edx, cx", "mov edx, ecx"),
    0x140fc2a63: ("movzx ecx, ax", "mov ecx, eax"),
    0x140fc2a6e: ("movzx edx, cx", "mov edx, ecx"),
    0x140fc2f49: ("movzx ecx, ax", "mov ecx, eax"),
    0x140fc2f58: ("movzx edx, cx", "mov edx, ecx"),
    0x140fc7f98: ("movzx ecx, ax", "mov ecx, eax"),
    0x140fc7fa3: ("movzx edx, cx", "mov edx, ecx"),
    0x141280518: ("movzx ecx, ax", "mov ecx, eax"),
    0x141280523: ("movzx edx, cx", "mov edx, ecx"),
    0x14129d5e6: ("movzx ecx, ax", "mov ecx, eax"),
    0x14129d5f1: ("movzx edx, cx", "mov edx, ecx"),
    0x1412a0709: ("movzx esi, ax", "mov esi, eax"),
    0x1412a0710: ("movzx edx, si", "mov edx, esi"),
    0x1412adc2b: ("movzx ecx, ax", "mov ecx, eax"),
    0x1412adc37: ("movzx edx, cx", "mov edx, ecx"),
    0x1412e0695: ("movzx ecx, ax", "mov ecx, eax"),
    0x1412e06a4: ("movzx edx, cx", "mov edx, ecx"),
    0x1412e7458: ("movzx esi, ax", "mov esi, eax"),
    0x1412e7463: ("movzx edx, si", "mov edx, esi"),
    0x14130e3a9: ("movzx ecx, ax", "mov ecx, eax"),
    0x14130e3b4: ("movzx edx, cx", "mov edx, ecx"),
    0x14130e606: ("movzx ecx, ax", "mov ecx, eax"),
    0x14130e611: ("movzx edx, cx", "mov edx, ecx"),
    0x14130e7e9: ("movzx ecx, ax", "mov ecx, eax"),
    0x14130e7f0: ("movzx edx, cx", "mov edx, ecx"),
    0x1413160b7: ("movzx ecx, ax", "mov ecx, eax"),
    0x1413160c2: ("movzx edx, cx", "mov edx, ecx"),
    0x141350384: ("movzx esi, ax", "mov esi, eax"),
    0x14135038a: ("movzx edx, si", "mov edx, esi"),
    0x1415109ec: ("movzx edx, di", "mov edx, edi"),
    0x141510c55: ("movzx esi, ax", "mov esi, eax"),
    0x141510c5b: ("movzx edx, si", "mov edx, esi"),
    0x141510d85: ("movzx esi, ax", "mov esi, eax"),
    0x141510d8b: ("movzx edx, si", "mov edx, esi"),
    0x1415174e9: ("movzx eax, ax", "mov eax, eax"),
    0x1415174f8: ("movzx edx, ax", "mov edx, eax"),
    0x14151e9ff: ("movzx edx, r14w", "mov edx, r14d"),
    0x14154ff7c: ("movzx edx, bx", "mov edx, ebx"),
    0x141578d67: ("movzx ecx, ax", "mov ecx, eax"),
    0x141578d73: ("movzx edx, cx", "mov edx, ecx"),
    0x14157bbd9: ("movzx ebx, ax", "mov ebx, eax"),
    0x14157bbe9: ("movzx edx, bx", "mov edx, ebx"),
    0x14157f4b4: ("movzx edx, bp", "mov edx, ebp"),
    0x141585d13: ("movzx edx, si", "mov edx, esi"),
    0x141fc6e0a: ("movzx edx, r15w", "mov edx, r15d"),
    0x141fc71d8: ("movzx edx, r15w", "mov edx, r15d"),
    0x141fdf68e: ("movzx edx, di", "mov edx, edi"),
}

# Round 3 (06.11., m6g save -> restart -> load): the record's copy (0x140b05450, used when a save is
# written and read) moved the id as a word, so ids from 65536 came back as their low word (slot
# 65536 + k held id k after the load, while the fixtures and cup ties still named 65536 + k:
# 107k misses at the hub). Traced with the fl26match tracer over slots 65536-65551 during the load.
# Bytes +2/+3 of a record are 0 from its init (memset, then word 0xffff), so the dword is the id.
ROUND3 = {
    0x140b05450: ("movzx eax, word ptr [rdx]", "mov eax, dword ptr [rdx]"),
    0x140b05456: ("mov word ptr [rcx], ax", "mov dword ptr [rcx], eax"),
}


# Round 4 (06.11. night, m7 trace: the fl26match tracer over 512 records from slot 80000 for 180 s of
# FF, scratchpad ripsword.py -> notes/limits-fl27/ingame/ripsword_m7t.txt): the instructions that read
# a record's id as a word and hand it on. Two functions return a match id cut to its word:
# 0x14154e940 (the earliest match of a club, 2 callers) and 0x14151adc0 (a day's match, 1 caller);
# their callers look it up and compare it with 0x141510000, which returns the id whole -- so past
# 65535 that compare never held. 0x141332630 passes the id by pointer down to 0x14151dbcc, which
# reads it as a dword. Left as they are: the empty checks `cmp word [rec], 0xffff` (0x14152230f,
# 0x140fc1965, 0x14131dce1: a live id never has 0xffff as its low word), the per-club schedule
# writer 0x14158d047 (storage, see above), the context hook 0x1415500a7 (fl26match keeps it), and the
# copy into the 0x1c-byte stage list 0x14134e588 (its +2 is not known to be free).
ROUND4 = {
    0x14154e9f0: ("movzx r12d, word ptr [r8]", "mov r12d, dword ptr [r8]"),
    0x14154eb31: ("movzx eax, r12w", "mov eax, r12d"),
    0x1413308b4: ("movzx edx, ax", "mov edx, eax"),
    0x14153f648: ("movzx edx, bx", "mov edx, ebx"),
    0x14151afc9: ("movzx eax, word ptr [rdi]", "mov eax, dword ptr [rdi]"),
    0x14133076c: ("movzx edx, r14w", "mov edx, r14d"),
    0x1413307a4: ("movzx edx, r14w", "mov edx, r14d"),
    0x1413307bf: ("movzx edx, r14w", "mov edx, r14d"),
    0x1413307f5: ("movzx edx, r14w", "mov edx, r14d"),
    0x141330974: ("movzx edx, r14w", "mov edx, r14d"),
    0x14153e50c: ("movzx edx, bx", "mov edx, ebx"),
    0x14133263c: ("movzx ecx, word ptr [r15]", "mov ecx, dword ptr [r15]"),
}

# Round 5 (06.11. night, the twins test m9x: lookups of a low id from a site not on the user list while
# the high twin was the user's club's match, fl26match "amb"): 0x1415287a0 takes the id by pointer and
# reads it as a word. All three callers store a whole dword there (0x14133439b from the record,
# 0x1413344xx alike, 0x14134aeb8 a zero-extended word), so it reads the dword.
#
# The hub's list of the user's matches ({id, date}, 8 bytes, 0x14157a820) is filled from the club's
# schedule, whose ids are words: fl26match.dll hooks 0x14157ae1e so the list gets the whole id of the
# record the lookup found (the user's twin). Its readers then take the dword: 0x14157b130 (the
# competition of the next match) and the strip's caller 0x140cd6950 (the list as u32 ids, from
# 0x14157b300), which reread it as a word.
ROUND5 = {
    0x1415287c2: ("movzx edx, word ptr [rbx]", "mov edx, dword ptr [rbx]"),
    0x14157b248: ("movzx edx, si", "mov edx, esi"),
    0x14157b253: ("movzx ecx, word ptr [rax]", "mov ecx, dword ptr [rax]"),
    0x140cd6a21: ("movzx edx, word ptr [rcx + rdx*4]", "mov edx, dword ptr [rcx + rdx*4]"),
}


# Where the slot's id is compared with an id handed in (a function that finds the slot of match X):
# X may come in cut or whole, so both sides are compared as words (inside one competition the
# low words are unique). Several instructions rewritten as one, nop-padded.
SEQ = {
    0x140ca1e9a: (("movzx eax, ax", "cmp eax, ebp"), "cmp ax, bp"),
    0x14134943a: (("movzx eax, ax", "cmp eax, r14d"), "cmp ax, r14w"),
    0x141510eba: (("movzx eax, ax", "cmp eax, r14d"), "cmp ax, r14w"),
    0x14151100b: (("movzx eax, ax", "cmp eax, 0xffff", "je 0x14151101a", "cmp eax, r14d"),
                  "cmp ax, 0xffff; je 0x14151101a; cmp ax, r14w"),
}


def patches(exe, ks=None, overlay=None):
    """-> calwiden-style patches, rewritten in place and nop-padded. `overlay(va, n)`, when given,
    reads the code as the rest of the set leaves it (an M2 site rewritten before this one)."""
    import keystone
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    ks = ks or keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    rd = overlay or exe.read
    out = []
    both = dict(SITES)
    for va, w in list(ROUND2.items()) + list(ROUND3.items()) + list(ROUND4.items()) + list(ROUND5.items()):
        if va in both and both[va] != w:
            raise SystemExit("0x%x in both rounds, differently" % va)
        both[va] = w
    for va in sorted(SEQ):
        wants, new_text = SEQ[va]
        old, at = b"", va
        for want in wants:
            ins = next(md.disasm(rd(at, 16), at))
            text = "%s %s" % (ins.mnemonic, ins.op_str)
            if text != want:
                raise SystemExit("0x%x: %r, not %r -- another exe?" % (at, text, want))
            old += bytes(ins.bytes); at += ins.size
        new = bytes(ks.asm(new_text, va)[0])
        if len(new) > len(old):
            raise SystemExit("0x%x: %s is %d bytes longer" % (va, new_text, len(new) - len(old)))
        new += bytes([0x90]) * (len(old) - len(new))
        out.append({"va": "0x%x" % va, "old": old.hex(), "new": new.hex(),
                    "why": "u32 match id (M4, slot compare): %s -> %s" % (" ; ".join(wants), new_text), "asm": "insn"})
    for va in sorted(both):
        want, new_text = both[va]
        ins = next(md.disasm(rd(va, 16), va))
        text = "%s %s" % (ins.mnemonic, ins.op_str)
        if text != want:
            raise SystemExit("0x%x: %r, not %r -- another exe?" % (va, text, want))
        old = bytes(ins.bytes)
        new = bytes(ks.asm(new_text, va)[0]) if new_text != "nop" else b""
        if len(new) > len(old):
            raise SystemExit("0x%x: %s -> %s is %d bytes longer" % (va, text, new_text, len(new) - len(old)))
        if new_text == "nop":
            new = {3: b"\x0f\x1f\x00", 4: b"\x0f\x1f\x40\x00"}[len(old)]
        new += b"\x90" * (len(old) - len(new))
        out.append({"va": "0x%x" % va, "old": old.hex(), "new": new.hex(),
                    "why": "u32 match id (M4): %s -> %s" % (text, new_text), "asm": "insn"})
    return out


def main(argv):
    sys.path.insert(0, HERE)
    import calwiden
    ps = patches(calwiden.Exe())
    print("%d patches" % len(ps))
    if "--review" in argv:
        for p in ps:
            print("  %s  %s -> %s  %s" % (p["va"], p["old"], p["new"], p["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
