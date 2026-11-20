--[[
fl26slot7 -- a club's Master League league slot may be 0..511 (needs fl26slots250).

GENERATED FILE by mkslot7.py.  Every byte below was read from the exe at that address.

Summary: team league slot 7 -> 9 bits (+0x41c low byte, +0x41b high byte, flag moved to +0x41a), 93 patches

A team record keeps its league slot in bits 0-6 of +0x41c; bit 7 is a flag of the game's own
and bits 8-31 are other fields.  With fl26slots250 a league can sit on slots 124..464, but a
club of a league on 130 got slot 130 & 0x7f = 2 when a Master League was created (the slot of
another competition), and every Master League lookup by club slot then went wrong.

This module moves the flag to +0x41a and the slot's high byte to +0x41b (padding next to the
country word +0x418), so the slot is +0x41c | +0x41b << 8:
  * every reader jumps to a stub that loads both bytes (9 bits); a byte compare right after
    the load is done on the whole register there,
  * every writer stores both bytes,
  * the flag is set, read, edited and copied at +0x41a,
  * the six callers of 0x141509c00 get the real slot (not 7 above 127),
  * the Master League slot choice (0x141263b40) is the game's own: the first slot holding a
    league-format competition wins, so a league on 344 gets 344 when fl26comptab gives its
    row slot 344.
B391 (10.11.2026): the 8-bit version stored 344 as 88, so Team Info put the clubs of a league
on 256..464 under the league on slot - 256.

Careers: a Master League created without this module stores the flag in bit 7; loading it
with this module reads every flagged club's slot as slot+128.  Start a NEW career after
installing (fl26slots250 already asks for that), and keep the module for that career.  A
career made with the 8-bit version of this module loads as it was (+0x41b is 0 there).

Load order: after fl26caps and fl26slots250 is fine; no byte overlaps any shipped module.
Page 0x163c00000 is its own.  Needs luajit.ext.enabled = 1 in sider.ini.

Install:
  1. copy this file to <game>\SiderAddons\modules\fl26slot7.lua
  2. add to sider.ini:   lua.module = "fl26slot7.lua"   (after fl26slots250.lua)
  3. start the game and read sider.log ("fl26slot7: applied all ...")
--]]

local m = {}

local patches = {
  {va=0x163c00000, old="000000000000000000000000000000000000000000000000000000000000000000000000000000", new="4883ec280fb709e8d4b28cdd83f87b740c3d0002000073054883c428c3b8070000004883c428c3",
   why="league slot of a competition id: id2slot, 7 only for 123 or >= 512 (0x141509c00 caps at 128)"},
  {va=0x163c00030, old="00000000000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff01000083f949e92f8ff0dc",
   why="stub of slot reader 0x140b08f6b: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, 0x49 -> stub 0x163c00030 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00050, old="00000000000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff01000083f949e95bc006dd",
   why="stub of slot reader 0x140c6c0b7: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, 0x49 -> stub 0x163c00050 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00070, old="000000000000000000000000000000000000000000000000", new="0fb7811b04000066c1c00825ff01000083f87be9f22f3add",
   why="stub of slot reader 0x140fa306f: movzx eax, byte ptr [rcx + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00070 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00088, old="000000000000000000000000000000000000000000000000", new="0fb7851b04000066c1c00825ff01000083f87be9e2293ddd",
   why="stub of slot reader 0x140fd2a77: movzx eax, byte ptr [rbp + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00088 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c000a0, old="000000000000000000000000000000000000000000000000", new="0fb7861b04000066c1c00825ff01000083f87be9f98d3ddd",
   why="stub of slot reader 0x140fd8ea6: movzx eax, byte ptr [rsi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c000a0 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c000b8, old="00000000000000000000000000000000000000000000000000", new="450fb7bd1b0400006641c1c7084181e7ff010000e9b42266dd",
   why="stub of slot reader 0x141262379: movzx r15d, byte ptr [r13 + 0x41c] ; and r15d, 0x7f -> stub 0x163c000b8 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c000d8, old="000000000000000000000000000000000000000000", new="0fb7801b04000066c1c00825ff010000e9082866dd",
   why="stub of slot reader 0x1412628ec: movzx eax, byte ptr [rax + 0x41c] ; and al, 0x7f -> stub 0x163c000d8 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c000f0, old="000000000000000000000000000000000000000000", new="0fb7801b04000066c1c00825ff010000e9802a66dd",
   why="stub of slot reader 0x141262b7c: movzx eax, byte ptr [rax + 0x41c] ; and al, 0x7f -> stub 0x163c000f0 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00108, old="000000000000000000000000000000000000000000000000", new="0fb7861b04000066c1c00825ff01000083f87be9d84c72dd",
   why="stub of slot reader 0x141324ded: movzx eax, byte ptr [rsi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00108 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00120, old="000000000000000000000000000000000000000000000000", new="0fb7871b04000066c1c00825ff01000083f87be9109f72dd",
   why="stub of slot reader 0x14132a03d: movzx eax, byte ptr [rdi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00120 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00138, old="000000000000000000000000000000000000000000", new="0fb7861b04000066c1c00825ff010000e9213873dd",
   why="stub of slot reader 0x141333964: movzx eax, byte ptr [rsi + 0x41c] ; and eax, 0x7f -> stub 0x163c00138 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00150, old="000000000000000000000000000000000000000000000000", new="0fb7811b04000066c1c00825ff01000083f846e96c4c75dd",
   why="stub of slot reader 0x141354dc9: movzx eax, byte ptr [rcx + 0x41c] ; and al, 0x7f ; cmp al, 0x46 -> stub 0x163c00150 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00168, old="000000000000000000000000000000000000000000", new="0fb7811b04000066c1c00825ff010000e95a5775dd",
   why="stub of slot reader 0x1413558cd: movzx eax, byte ptr [rcx + 0x41c] ; and eax, 0x7f -> stub 0x163c00168 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00180, old="00000000000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff01000083f945e9e88d75dd",
   why="stub of slot reader 0x141358f74: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, 0x45 -> stub 0x163c00180 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c001a0, old="000000000000000000000000000000000000000000000000", new="0fb7831b04000066c1c00825ff01000083f846e918a775dd",
   why="stub of slot reader 0x14135a8c5: movzx eax, byte ptr [rbx + 0x41c] ; and al, 0x7f ; cmp al, 0x46 -> stub 0x163c001a0 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c001b8, old="000000000000000000000000000000000000000000000000", new="0fb7811b04000066c1c00825ff01000083f84be944ac75dd",
   why="stub of slot reader 0x14135ae09: movzx eax, byte ptr [rcx + 0x41c] ; and al, 0x7f ; cmp al, 0x4b -> stub 0x163c001b8 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c001d0, old="000000000000000000000000000000000000000000000000", new="0fb7831b04000066c1c00825ff01000083f849e998af75dd",
   why="stub of slot reader 0x14135b175: movzx eax, byte ptr [rbx + 0x41c] ; and al, 0x7f ; cmp al, 0x49 -> stub 0x163c001d0 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c001e8, old="00000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff010000e993d575dd",
   why="stub of slot reader 0x14135d787: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c001e8 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00200, old="00000000000000000000000000000000000000000000000000", new="440fb7b81b0400006641c1c7084181e7ff010000e9650176dd",
   why="stub of slot reader 0x141360372: movzx r15d, byte ptr [rax + 0x41c] ; and r15b, 0x7f -> stub 0x163c00200 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00220, old="00000000000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff0100004439f9e9bf0176dd",
   why="stub of slot reader 0x1413603eb: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, r15b -> stub 0x163c00220 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00240, old="000000000000000000000000000000000000000000000000", new="0fb7871b04000066c1c00825ff0100004189c0e9ce0e76dd",
   why="stub of slot reader 0x141361119: movzx eax, byte ptr [rdi + 0x41c] ; and al, 0x7f ; movzx r8d, al -> stub 0x163c00240 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00258, old="00000000000000000000000000000000000000000000000000", new="440fb7b81b0400006641c1c7084181e7ff010000e9a15676dd",
   why="stub of slot reader 0x141365906: movzx r15d, byte ptr [rax + 0x41c] ; and r15b, 0x7f -> stub 0x163c00258 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00278, old="00000000000000000000000000000000000000000000", new="0fb7b81b04000066c1c70881e7ff010000e9ad5676dd",
   why="stub of slot reader 0x141365930: movzx edi, byte ptr [rax + 0x41c] ; and dil, 0x7f -> stub 0x163c00278 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00290, old="00000000000000000000000000000000000000000000", new="0fb7a81b04000066c1c50881e5ff010000e9d09290dd",
   why="stub of slot reader 0x14150956c: movzx ebp, byte ptr [rax + 0x41c] ; and ebp, 0x7f -> stub 0x163c00290 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c002a8, old="00000000000000000000000000000000000000000000", new="0fb7901b04000066c1c20881e2ff010000e931d290dd",
   why="stub of slot reader 0x14150d4e5: movzx edx, byte ptr [rax + 0x41c] ; and edx, 0x7f -> stub 0x163c002a8 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c002c0, old="00000000000000000000000000000000000000000000", new="0fb7901b04000066c1c20881e2ff010000e953d290dd",
   why="stub of slot reader 0x14150d51f: movzx edx, byte ptr [rax + 0x41c] ; and edx, 0x7f -> stub 0x163c002c0 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c002d8, old="00000000000000000000000000000000000000000000", new="0fb78a1b04000066c1c10881e1ff010000e95c0f91dd",
   why="stub of slot reader 0x141511243: movzx ecx, byte ptr [rdx + 0x41c] -> stub 0x163c002d8 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c002f0, old="000000000000000000000000000000000000000000", new="0fb7811b04000066c1c00825ff010000e9d88e91dd",
   why="stub of slot reader 0x1415191d3: movzx eax, byte ptr [rcx + 0x41c] ; and eax, 0x7f -> stub 0x163c002f0 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00308, old="000000000000000000000000000000000000000000000000", new="0fb7861b04000066c1c00825ff01000083f87be9a27b92dd",
   why="stub of slot reader 0x141527eb7: movzx eax, byte ptr [rsi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00308 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00320, old="00000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff010000e9361c94dd",
   why="stub of slot reader 0x141541f62: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c00320 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00338, old="00000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff010000e9c56694dd",
   why="stub of slot reader 0x141546a09: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c00338 (9 bits from +0x41c/+0x41b)"},
  {va=0x163c00350, old="00000000000000000000000000000000000000000000", new="0fb7881b04000066c1c10881e1ff010000e98d7c94dd",
   why="stub of slot reader 0x141547fe9: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c00350 (9 bits from +0x41c/+0x41b)"},
  {va=0x140ae3de8, old="e8135ea200", new="e813c21123",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x140ae44d3, old="e82857a200", new="e828bb1123",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x14126275b, old="e8a0742a00", new="e8a0d89922",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x141262e8b, old="e8706d2a00", new="e870d19922",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x14135964b, old="e8b0051b00", new="e8b0698a22",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x14135a50b, old="e8f0f61a00", new="e8f05a8a22",
   why="call 0x141509c00 -> our slot function 0x163c00000"},
  {va=0x140b08f6b, old="0fb6881c04000080e17f80f949", new="e9c0700f239090909090909090",
   why="slot reader 0x140b08f6b: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, 0x49 -> stub 0x163c00030 (9 bits from +0x41c/+0x41b)"},
  {va=0x140c6c0b7, old="0fb6881c04000080e17f80f949", new="e9943ff9229090909090909090",
   why="slot reader 0x140c6c0b7: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, 0x49 -> stub 0x163c00050 (9 bits from +0x41c/+0x41b)"},
  {va=0x140fa306f, old="0fb6811c040000247f3c7b", new="e9fccfc522909090909090",
   why="slot reader 0x140fa306f: movzx eax, byte ptr [rcx + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00070 (9 bits from +0x41c/+0x41b)"},
  {va=0x140fd2a77, old="0fb6851c040000247f3c7b", new="e90cd6c222909090909090",
   why="slot reader 0x140fd2a77: movzx eax, byte ptr [rbp + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00088 (9 bits from +0x41c/+0x41b)"},
  {va=0x140fd8ea6, old="0fb6861c040000247f3c7b", new="e9f571c222909090909090",
   why="slot reader 0x140fd8ea6: movzx eax, byte ptr [rsi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c000a0 (9 bits from +0x41c/+0x41b)"},
  {va=0x141262379, old="450fb6bd1c0400004183e77f", new="e93add992290909090909090",
   why="slot reader 0x141262379: movzx r15d, byte ptr [r13 + 0x41c] ; and r15d, 0x7f -> stub 0x163c000b8 (9 bits from +0x41c/+0x41b)"},
  {va=0x1412628ec, old="0fb6801c040000247f", new="e9e7d7992290909090",
   why="slot reader 0x1412628ec: movzx eax, byte ptr [rax + 0x41c] ; and al, 0x7f -> stub 0x163c000d8 (9 bits from +0x41c/+0x41b)"},
  {va=0x141262b7c, old="0fb6801c040000247f", new="e96fd5992290909090",
   why="slot reader 0x141262b7c: movzx eax, byte ptr [rax + 0x41c] ; and al, 0x7f -> stub 0x163c000f0 (9 bits from +0x41c/+0x41b)"},
  {va=0x141324ded, old="0fb6861c040000247f3c7b", new="e916b38d22909090909090",
   why="slot reader 0x141324ded: movzx eax, byte ptr [rsi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00108 (9 bits from +0x41c/+0x41b)"},
  {va=0x14132a03d, old="0fb6871c040000247f3c7b", new="e9de608d22909090909090",
   why="slot reader 0x14132a03d: movzx eax, byte ptr [rdi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00120 (9 bits from +0x41c/+0x41b)"},
  {va=0x141333964, old="0fb6861c04000083e07f", new="e9cfc78c229090909090",
   why="slot reader 0x141333964: movzx eax, byte ptr [rsi + 0x41c] ; and eax, 0x7f -> stub 0x163c00138 (9 bits from +0x41c/+0x41b)"},
  {va=0x141354dc9, old="0fb6811c040000247f3c46", new="e982b38a22909090909090",
   why="slot reader 0x141354dc9: movzx eax, byte ptr [rcx + 0x41c] ; and al, 0x7f ; cmp al, 0x46 -> stub 0x163c00150 (9 bits from +0x41c/+0x41b)"},
  {va=0x1413558cd, old="0fb6811c04000083e07f", new="e996a88a229090909090",
   why="slot reader 0x1413558cd: movzx eax, byte ptr [rcx + 0x41c] ; and eax, 0x7f -> stub 0x163c00168 (9 bits from +0x41c/+0x41b)"},
  {va=0x141358f74, old="0fb6881c04000080e17f80f945", new="e907728a229090909090909090",
   why="slot reader 0x141358f74: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, 0x45 -> stub 0x163c00180 (9 bits from +0x41c/+0x41b)"},
  {va=0x14135a8c5, old="0fb6831c040000247f3c46", new="e9d6588a22909090909090",
   why="slot reader 0x14135a8c5: movzx eax, byte ptr [rbx + 0x41c] ; and al, 0x7f ; cmp al, 0x46 -> stub 0x163c001a0 (9 bits from +0x41c/+0x41b)"},
  {va=0x14135ae09, old="0fb6811c040000247f3c4b", new="e9aa538a22909090909090",
   why="slot reader 0x14135ae09: movzx eax, byte ptr [rcx + 0x41c] ; and al, 0x7f ; cmp al, 0x4b -> stub 0x163c001b8 (9 bits from +0x41c/+0x41b)"},
  {va=0x14135b175, old="0fb6831c040000247f3c49", new="e956508a22909090909090",
   why="slot reader 0x14135b175: movzx eax, byte ptr [rbx + 0x41c] ; and al, 0x7f ; cmp al, 0x49 -> stub 0x163c001d0 (9 bits from +0x41c/+0x41b)"},
  {va=0x14135d787, old="0fb6881c04000083e17f", new="e95c2a8a229090909090",
   why="slot reader 0x14135d787: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c001e8 (9 bits from +0x41c/+0x41b)"},
  {va=0x141360372, old="440fb6b81c0400004180e77f", new="e989fe892290909090909090",
   why="slot reader 0x141360372: movzx r15d, byte ptr [rax + 0x41c] ; and r15b, 0x7f -> stub 0x163c00200 (9 bits from +0x41c/+0x41b)"},
  {va=0x1413603eb, old="0fb6881c04000080e17f413acf", new="e930fe89229090909090909090",
   why="slot reader 0x1413603eb: movzx ecx, byte ptr [rax + 0x41c] ; and cl, 0x7f ; cmp cl, r15b -> stub 0x163c00220 (9 bits from +0x41c/+0x41b)"},
  {va=0x141361119, old="0fb6871c040000247f440fb6c0", new="e922f189229090909090909090",
   why="slot reader 0x141361119: movzx eax, byte ptr [rdi + 0x41c] ; and al, 0x7f ; movzx r8d, al -> stub 0x163c00240 (9 bits from +0x41c/+0x41b)"},
  {va=0x141365906, old="440fb6b81c0400004180e77f", new="e94da9892290909090909090",
   why="slot reader 0x141365906: movzx r15d, byte ptr [rax + 0x41c] ; and r15b, 0x7f -> stub 0x163c00258 (9 bits from +0x41c/+0x41b)"},
  {va=0x141365930, old="0fb6b81c0400004080e77f", new="e943a98922909090909090",
   why="slot reader 0x141365930: movzx edi, byte ptr [rax + 0x41c] ; and dil, 0x7f -> stub 0x163c00278 (9 bits from +0x41c/+0x41b)"},
  {va=0x14150956c, old="0fb6a81c04000083e57f", new="e91f6d6f229090909090",
   why="slot reader 0x14150956c: movzx ebp, byte ptr [rax + 0x41c] ; and ebp, 0x7f -> stub 0x163c00290 (9 bits from +0x41c/+0x41b)"},
  {va=0x14150d4e5, old="0fb6901c04000083e27f", new="e9be2d6f229090909090",
   why="slot reader 0x14150d4e5: movzx edx, byte ptr [rax + 0x41c] ; and edx, 0x7f -> stub 0x163c002a8 (9 bits from +0x41c/+0x41b)"},
  {va=0x14150d51f, old="0fb6901c04000083e27f", new="e99c2d6f229090909090",
   why="slot reader 0x14150d51f: movzx edx, byte ptr [rax + 0x41c] ; and edx, 0x7f -> stub 0x163c002c0 (9 bits from +0x41c/+0x41b)"},
  {va=0x141511243, old="0fb68a1c040000", new="e990f06e229090",
   why="slot reader 0x141511243: movzx ecx, byte ptr [rdx + 0x41c] -> stub 0x163c002d8 (9 bits from +0x41c/+0x41b)"},
  {va=0x141511251, old="83e17f", new="0f1f00",
   why="slot reader 0x141511243: its `and ecx, 0x7f` -> nop (the stub masks)"},
  {va=0x1415191d3, old="0fb6811c04000083e07f", new="e918716e229090909090",
   why="slot reader 0x1415191d3: movzx eax, byte ptr [rcx + 0x41c] ; and eax, 0x7f -> stub 0x163c002f0 (9 bits from +0x41c/+0x41b)"},
  {va=0x141527eb7, old="0fb6861c040000247f3c7b", new="e94c846d22909090909090",
   why="slot reader 0x141527eb7: movzx eax, byte ptr [rsi + 0x41c] ; and al, 0x7f ; cmp al, 0x7b -> stub 0x163c00308 (9 bits from +0x41c/+0x41b)"},
  {va=0x141541f62, old="0fb6881c04000083e17f", new="e9b9e36b229090909090",
   why="slot reader 0x141541f62: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c00320 (9 bits from +0x41c/+0x41b)"},
  {va=0x141546a09, old="0fb6881c04000083e17f", new="e92a996b229090909090",
   why="slot reader 0x141546a09: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c00338 (9 bits from +0x41c/+0x41b)"},
  {va=0x141547fe9, old="0fb6881c04000083e17f", new="e962836b229090909090",
   why="slot reader 0x141547fe9: movzx ecx, byte ptr [rax + 0x41c] ; and ecx, 0x7f -> stub 0x163c00350 (9 bits from +0x41c/+0x41b)"},
  {va=0x141262760, old="4183a51c040000800fb6c083e07f4109851c040000", new="4188851c040000c1e8084188851b04000090909090",
   why="user's club: slot (eax) from 0x141509c00 -> +0x41c / +0x41b"},
  {va=0x1412627df, old="4183a4241c040000800fb645ef83e07f410984241c040000", new="0fb745ef418884241c040000c1e808418884241b04000090",
   why="user's club path: other club gets the saved slot [rbp-0x11] (a dword) -> +0x41c / +0x41b"},
  {va=0x1412628f5, old="4183a51c040000800fb6c04109851c040000", new="4188851c040000c1e8084188851b04000090",
   why="user's club takes another club's slot (eax, our reader) -> +0x41c / +0x41b"},
  {va=0x141262930, old="418b8704030000c1e807a80175060fbaf207eb040fbaea074189951c040000", new="418b8704030000c1e80724014188851a040000909090909090909090909090",
   why="flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"},
  {va=0x14126294f, old="83a11c040000800fb645ef83e07f09811c040000", new="0fb745ef88811c04000088a11b04000090909090",
   why="other club gets the saved slot [rbp-0x11] -> +0x41c / +0x41b"},
  {va=0x141262b85, old="4183a51c040000800fb6c04109851c040000", new="4188851c040000c1e8084188851b04000090",
   why="user's club takes another club's slot (eax, our reader) -> +0x41c / +0x41b"},
  {va=0x141262bc0, old="8b8604030000c1e807a80175060fbaf207eb040fbaea074189951c040000", new="8b8604030000c1e80724014188851a040000909090909090909090909090",
   why="flag of the regulation (+0x304 bit 7) -> +0x41a instead of bit 7 of +0x41c"},
  {va=0x141262bde, old="83a11c04000080410fb6c783e07f09811c040000", new="410fb7c788811c04000088a11b04000090909090",
   why="other club gets slot r15 (the user's club's, our reader 0x141262379) -> +0x41c / +0x41b"},
  {va=0x141262e90, old="0fb6c841338d1c04000083e17f41338d1c04000041898d1c040000418b8704030000c1e807a80175060fbaf107eb040fbae90741898d1c040000", new="4188851c040000c1e8084188851b040000418b8704030000c1e80724014188851a04000090909090909090909090909090909090909090909090",
   why="user's club: slot (eax) -> +0x41c / +0x41b, regulation flag -> +0x41a"},
  {va=0x141262f77, old="83a01c040000800fb645ef83e07f09811c040000", new="0fb745ef88811c04000088a11b04000090909090",
   why="other club (rax == rcx) gets the saved slot [rbp-0x11] -> +0x41c / +0x41b"},
  {va=0x1413658e1, old="41b77b410fb6ff", new="6a7b415f4489ff",
   why="season mover: 'no slot' default 123 in the whole of r15 and edi (the writers store them whole)"},
  {va=0x14136595f, old="83a01c04000080400fb6cf09881c040000", new="89f988881c04000088a81b040000909090",
   why="season mover: club takes slot edi -> +0x41c / +0x41b"},
  {va=0x14136599f, old="83a01c04000080410fb6cf09881c040000", new="4489f988881c04000088a81b0400009090",
   why="season mover: club takes slot r15d -> +0x41c / +0x41b"},
  {va=0x14126655e, old="8b856c03000083e0fb83c87b", new="66c7856b030000007beb7890",
   why="staged world: no slot -> +0x41c = 123, +0x41b = 0 (skips the dword store at 0x1412665db; eax is dead past the call at 0x1412665f7)"},
  {va=0x1412665cb, old="0fb6c88b856c03000033c883e17f33c1", new="8b8d6c03000088c188a56b03000089c8",
   why="staged world: slot (eax) from 0x141263b40 -> byte +0x41c, high byte +0x41b of the staged copy"},
  {va=0x1414c5b41, old="818b1c04000080000000", new="c6831a04000001909090",
   why="team init: flag = 1 now in +0x41a (was or [+0x41c],0x80)"},
  {va=0x141f12004, old="81a61c0400007fffffff098e1c040000", new="c1e907888e1a04000090909090909090",
   why="edit field setter: flag (ecx = 0x80 or 0) -> +0x41a bit 0"},
  {va=0x141eddb4f, old="8b801c040000c1e8072401", new="0fb6801a04000024019090",
   why="flag reader: +0x41a bit 0"},
  {va=0x141f116af, old="8b851c040000458bc6c1e8072401", new="0fb6851a0400004589f024019090",
   why="edit field getter: flag from +0x41a bit 0"},
  {va=0x140b15aa9, old="0fb78718040000", new="8b871804000090",
   why="team copy: country word +0x418 copied as a dword, so +0x41a (flag) and +0x41b (slot high) travel"},
  {va=0x140b15ab0, old="66898318040000", new="89831804000090",
   why="team copy: store the dword +0x418..+0x41b"},
}

local PAGES = { 0x163c00000 }

local function unhex(s)
  local out = {}
  for i = 1, #s, 2 do
    out[#out + 1] = string.char(tonumber(string.sub(s, i, i + 1), 16))
  end
  return table.concat(out)
end

local function tohex(s)
  if s == nil then return "nil" end
  local out = {}
  for i = 1, #s do
    out[#out + 1] = string.format("%02x", string.byte(s, i))
  end
  return table.concat(out)
end

local function reserve(page)
  if ffi == nil then
    log("fl26slot7: global ffi is nil -- set luajit.ext.enabled = 1 in sider.ini")
    return false
  end
  if not m.cdef then
    -- a name of our own: another module may already have declared VirtualAlloc, and
    -- declaring it twice is an error
    ffi.cdef([[ void* fl26slot7_VirtualAlloc(void*, size_t, uint32_t, uint32_t) asm("VirtualAlloc"); ]])
    m.cdef = true
  end
  local function try(kind)
    local p = ffi.C.fl26slot7_VirtualAlloc(ffi.cast("void*", page), 0x1000, kind, 0x40)
    return p ~= nil and tonumber(ffi.cast("uint64_t", p)) or 0
  end
  -- MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE; MEM_COMMIT alone if the page was
  -- already reserved (fl26cave.lua from an older install does that)
  local got = try(0x3000)
  if got ~= page then got = try(0x1000) end
  if got ~= page then
    log(string.format("fl26slot7: could not get the page at 0x%x (got 0x%x)", page, got))
    return false
  end
  log(string.format("fl26slot7: page 0x%x..0x%x ready", page, page + 0x1000))
  return true
end

function m.init(ctx)
  local n = #patches
  for _, page in ipairs(PAGES) do
    if not reserve(page) then
      log("fl26slot7: ABORTED before verifying. Nothing was written; the game is unmodified.")
      return
    end
  end
  log(string.format("fl26slot7: set '%s', %d patches, verifying", "slot7", n))

  -- pass 1: read only. Nothing is written until every single site has been confirmed.
  local bad = 0
  for i = 1, n do
    local p = patches[i]
    local want = unhex(p.old)
    local cur = memory.read(p.va, #want)
    if cur ~= want then
      log(string.format("fl26slot7: MISMATCH at 0x%x: found %s, expected %s  [%s]",
                        p.va, tohex(cur), p.old, p.why))
      bad = bad + 1
    end
  end
  if bad > 0 then
    log(string.format("fl26slot7: ABORTED, %d of %d sites did not match. "
                      .. "Nothing was written; the game is unmodified. "
                      .. "This usually means the exe is a different build than the one "
                      .. "the patch set was generated from.", bad, n))
    return
  end

  -- pass 2: write, then read back, because writing to the code section can silently fail
  -- if the page is not made writable for us. Each site is logged as it goes, so that if a
  -- write throws and Sider stops the module, the log still names the last one that worked.
  local written, failed = 0, 0
  for i = 1, n do
    local p = patches[i]
    local new = unhex(p.new)
    memory.write(p.va, new)
    local back = memory.read(p.va, #new)
    if back == new then
      written = written + 1
      log(string.format("fl26slot7: [%d/%d] 0x%x %s -> %s  %s",
                        i, n, p.va, p.old, p.new, p.why))
    else
      failed = failed + 1
      log(string.format("fl26slot7: WRITE FAILED at 0x%x (%s) -- read back %s",
                        p.va, p.why, tohex(back)))
    end
  end

  -- The patch has to land before the game allocates the edit block, and the log proves
  -- that it does: everything above is written during module init, which Sider finishes
  -- before it reports "Sider initialization complete", and the first `read_file::` line
  -- comes thousands of lines later. An earlier version of this file also registered a
  -- livecpk_get_filepath handler to re-read the first site at the first file request. It
  -- worked, but it made Sider log "lua ERROR from module_get_filepath" on every single
  -- file lookup -- 27811 of them in one session -- so it is gone. The ordering was never
  -- in doubt; the check was.

  if failed == 0 then
    log(string.format("fl26slot7: applied all %d patches -- %s", written, "team league slot 7 -> 9 bits (+0x41c low byte, +0x41b high byte, flag moved to +0x41a), 93 patches"))
  else
    log(string.format("fl26slot7: PARTIAL: %d written, %d failed. The game is now in an "
                      .. "inconsistent state -- quit and report the addresses above.",
                      written, failed))
  end
end

return m
