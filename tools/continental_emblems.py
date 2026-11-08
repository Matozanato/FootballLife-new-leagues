"""Optional continental emblem paths; competition IDs and generated cup numbers are distinct.

Recipe: continental_emblems[game:<CID>|generated:<number>|uecl][dark|light].
Only overlays the existing asset pipeline; absent variants keep its previous output.
"""
import mkleague as M

ROOT = "continental_emblems"
MODES = ("dark", "light")


def key(storage, number=None):
    return "uecl" if storage == "uecl" else "%s:%s" % (storage, number)


def native_ids(base):
    """Actual native continental club slots, excluding FIFA/world competitions."""
    raw = M.load(base, "Competition.bin")
    return {raw[o + M.CID_OFF] for o in range(0, len(raw), M.COMP)
            if raw[o + M.CID_OFF] in range(1, 9)
            and raw[o + M.FLAG_OFF] & 7 in (2, 3, 4, 5, 6, 7)}


def suffix(mode):
    # Existing game convention: white/full-colour for dark backgrounds, black/full-colour for light.
    return "_w" if mode == "dark" else "_b"


def files(cid, mode):
    return ["common/render/symbol/emblemLc/emb_%04d%s%s.png" % (cid, suffix(mode), size)
            for size in ("_l", "_ll")]
