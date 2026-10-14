r"""python test_group_ours.py -> Mod Studio's modules sit together in sider.ini, in one block
between two comment lines (0.2.4); their order and every other line's stay; a second run
changes nothing"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

L = ['[sider]', 'lua.enabled = 1', r'lua.module = "lib\CommonLib.lua"',
     'lua.module = "fl26caps.lua"', '', 'lua.module = "dimision_alpha.lua"',
     ';lua.module = "fl26nullguard.lua"', '; off 25.09. lua.module = "fl26probe.lua"',
     'lua.module = "fl26swiss.lua"', r'lua.module = "before-builder-1\fl26old.lua"', 'lua.module = "kserv.lua"']
x = list(L)
assert B.group_ours(x)
want = ['[sider]', 'lua.enabled = 1', r'lua.module = "lib\CommonLib.lua"', B.OURS_HEAD,
        'lua.module = "fl26caps.lua"', ';lua.module = "fl26nullguard.lua"',
        '; off 25.09. lua.module = "fl26probe.lua"', 'lua.module = "fl26swiss.lua"', B.OURS_END,
        'lua.module = "dimision_alpha.lua"', r'lua.module = "before-builder-1\fl26old.lua"', 'lua.module = "kserv.lua"']
assert x == want, "\n".join(x)
y = list(x)
assert not B.group_ours(y) and y == x
z = ['[sider]', 'lua.module = "kserv.lua"']
assert not B.group_ours(z) and z == ['[sider]', 'lua.module = "kserv.lua"']
print("group ours: ok")
