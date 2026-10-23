r"""The crest the game shows for a club of the game (B108, David 17.10.: the Leagues page showed a
dash for the game's clubs in a league of yours -- Zamora, Deportivo Tachira in the Liga FUTVE --
as the world holds only the crests Build drew). Looked for as the game does: in the folders
sider.ini switches on (a crest pack first), then in the game's own .cpk files (download, then
Data, newest first). What comes out of a .cpk is kept in %APPDATA%\FL26ModStudio\cache\crests,
so it is read once."""
import glob, os, re, threading

FLAG = "common/render/symbol/flag/"
# licensed, its light version (a club with only light and dark ones: 1600 Spezia, B221), then the game's own
NAMES = ("e_%06d_r_l.png", "e_%06d_r.png", "e_%06d_r_w_l.png", "e_%06d_r_w.png", "e_%06d_f_l.png", "e_%06d_f.png")
CACHE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FL26ModStudio", "cache", "crests")
_toc, _lock = {}, threading.Lock()


def _roots(sider_dir):
    ini = os.path.join(sider_dir, "sider.ini")
    out = []
    try:
        with open(ini, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'\s*cpk\.root\s*=\s*"([^"]+)"', line)
                if m:
                    out.append(os.path.normpath(os.path.join(sider_dir, m.group(1))))
    except OSError:
        pass
    return out


def _cpks(folder):
    return sorted(glob.glob(os.path.join(folder, "download", "*.cpk")), reverse=True) + \
        sorted(glob.glob(os.path.join(folder, "Data", "*.cpk")), reverse=True)


def _names(cpk):
    with _lock:
        if cpk not in _toc:
            import cpkread
            try:
                _toc[cpk] = set(cpkread.names(cpk))
            except (OSError, ValueError, KeyError, IndexError):
                _toc[cpk] = set()
        return _toc[cpk]


def crest(game, tid, cache=CACHE):
    """the path of club `tid`'s crest picture as the game has it, or None. `game`: a Game (folder,
    sider_dir); no game folder -> None"""
    folder = getattr(game, "folder", "") or ""
    if tid is None or not folder or not os.path.isdir(folder):
        return None
    rels = [FLAG + n % int(tid) for n in NAMES]
    sider = getattr(game, "sider_dir", "") or ""
    for root in _roots(sider) if sider else []:
        for rel in rels:
            p = os.path.join(root, *rel.split("/"))
            if os.path.isfile(p):
                return p
    for rel in rels:
        p = os.path.join(cache, *rel.split("/"))
        if os.path.isfile(p):
            return p
    for c in _cpks(folder):
        names = _names(c)
        for rel in rels:
            if rel in names:
                import cpkread
                try:
                    cpkread.extract(c, cache, [rel])
                except OSError:
                    return None
                p = os.path.join(cache, *rel.split("/"))
                return p if os.path.isfile(p) else None
    return None
