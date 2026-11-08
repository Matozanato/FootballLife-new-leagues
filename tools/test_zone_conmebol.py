"""Compile and execute the real native zone lookup without a game.

Supports the documented x86-64 Windows GCC/zig toolchains. Does not test live hooks,
executable offsets, UI rendering or the game's runtime cup-winner fallback.
"""
import glob
import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

native = Path(__file__).resolve().parent / 'native'


def world_header(path):
    """Marshal relevant built-world records into the existing Lua->DLL ABI.

    This exercises real native loaders/render lookup; it does not run Sider/Lua
    or game hooks. Optional argv[1] can check the reported installed world read-only.
    """
    access, cups, pres, flags, singles, alts = [], [], [], [], [], []
    ncup = npre = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        if words[0] == 'uefa':
            access.extend(map(int, words[1:5]))
        if words[0] not in ('ccup', 'lpre'):
            continue
        reg = int(words[1])
        fields = dict(w.split('=', 1) for w in words[2:] if '=' in w)
        entries = [int(x) for entry in fields['entry'].split(',') for x in entry.split(':')]
        if words[0] == 'ccup':
            cups.extend([reg, int(fields['ko']), int(fields['groups']), len(entries)//2, *entries])
            ncup += 1
        else:
            days = list(map(int, fields['days'].split(',')))
            pres.extend([reg, int(fields['cup']), int(fields['fill']), *days, len(entries)//2, *entries])
            npre += 1
            bits = sum(bit for name, bit in (('po', 1), ('feed', 2), ('poko', 4))
                       if fields.get(name) == ('8' if name == 'feed' else '1'))
            if bits:
                flags.extend([reg, bits])
            if fields.get('single') == '1':
                singles.append(reg)
            for entry in fields.get('alt', '').split(','):
                if entry:
                    alts.extend([reg, *map(int, entry.split(':'))])
    lines = ['static void load_world_fixture(void) {']
    for name, data, fn, count in (
            ('wa', access, 'access', len(access)//4),
            ('wc', cups, 'ccup', ncup), ('wp', pres, 'lpre', npre),
            ('wf', flags, 'lpre_flags', len(flags)//2),
            ('ws', singles, 'lpre_single', len(singles)),
            ('wb', alts, 'lpre_alt', len(alts)//4)):
        if data:
            lines.append('const uint16_t %s[] = {%s};' % (name, ','.join(map(str, data))))
            lines.append('assert(fl26_swiss_%s(%s, %d) == %d);' % (fn, name, count, count))
    return '\n'.join(lines + ['}'])

zig = os.environ.get('ZIG') or shutil.which('zig')
if not zig:
    found = sorted(glob.glob('D:/dev/tools/zig-*/zig.exe'))
    zig = found[-1] if found else None
gcc = shutil.which('gcc')
compiler = [zig, 'cc'] if zig else [gcc] if gcc else None
if compiler is None:
    raise SystemExit('SKIPPED: requires a Windows x86-64 GCC/zig compiler')
with tempfile.TemporaryDirectory(prefix='fl26-zones-') as folder:
    target = Path(folder) / 'test_zone_conmebol.exe'
    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else native.parent / 'testdata/zone_conmebol_bolivia.txt'
    Path(folder, 'zone_world_fixture.h').write_text(world_header(fixture), encoding='utf-8')
    subprocess.run(compiler + ['-O2', '-w', '-DFL26_ZONE_WORLD_FIXTURE', '-I', folder,
                               str(native / 'test_zone_conmebol.c'), '-o', str(target)], check=True)
    subprocess.run([str(target)], check=True)
    # A correct source test is insufficient if the distributed DLL is stale.
    repository = native.parent.parent
    copies = [native / 'fl26swiss.dll', repository / 'sider/experimental/fl26swiss.dll']
    binaries = [path.read_bytes() for path in copies]
    assert binaries[0] == binaries[1], 'Native and distributable Swiss DLLs differ'
    assert b'standings zones v2 -- modern CONMEBOL' in binaries[0], 'Rebuild the distributed Swiss DLL'
    print('Both repository DLL copies match and contain the runtime zone marker')
