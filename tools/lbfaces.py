r"""player faces for a world: copy a face made for one player id to the id a player was given.

A face is a folder named by its player id:

    Asset\model\character\face\real\<id>\#Win\face.fpk          (face_high.fmdl, hair_high.fmdl)
    Asset\model\character\face\real\<id>\#Win\face.fpkd
    Asset\model\character\face\real\<id>\sourceimages\#windx11\*.ftex

and a portrait, common\render\symbol\player\<id>.dds.  The game finds face.fpk by the player's
id alone (no flag in Player.bin); the models inside find their textures by a text path that
carries the id, "/Assets/pes16/model/character/face/real/<id>/sourceimages/", written once in
each model's string table.

A new player's id is only known when the world is built, so a face is moved at build: the folder
goes under the new id, and the path in face.fpk is rewritten.  The rewrite never changes the
file's length: when the new id has as many digits as the old one it takes its place; when not,
the textures go to a folder of a made-up name with as many characters as the old id ("m" and a
number -- no player id has a letter, so it meets nothing of the game's), and the path points
there.  Nothing in the models moves, so nothing else needs fixing.

What a face folder may be, as a person picks it: the <id> folder itself, a folder holding one
(any depth, e.g. a whole face mod with Asset\...), or a folder with #Win\face.fpk in it.
A portrait.dds or <id>.dds next to #Win is taken as the portrait.
"""
import os, re, shutil

FACES = os.path.join("Asset", "model", "character", "face", "real")
PORTRAITS = os.path.join("common", "render", "symbol", "player")
PATH = re.compile(rb"/Assets/pes16/model/character/face/real/([^/\x00]{1,12})/sourceimages/")


class Error(Exception):
    pass


def find(folder):
    r"""the face folder (the one with #Win\face.fpk) under folder, or None"""
    folder = os.path.abspath(folder)
    if os.path.isfile(os.path.join(folder, "#Win", "face.fpk")):
        return folder
    hits = []
    for d, subs, files in os.walk(folder):
        if os.path.basename(d).lower() == "#win" and "face.fpk" in (f.lower() for f in files):
            hits.append(os.path.dirname(d))
        if len(hits) > 1:
            break
    return hits[0] if len(hits) == 1 else None


def old_id(face):
    """the id the face was made for: the one in its texture path"""
    b = open(os.path.join(face, "#Win", "face.fpk"), "rb").read()
    ids = set(m.group(1) for m in PATH.finditer(b))
    if not ids:
        raise Error("%s: face.fpk has no texture path (not a PES 2021 face?)" % face)
    if len(ids) > 1:
        raise Error("%s: face.fpk points at %d texture folders" % (face, len(ids)))
    return ids.pop().decode("ascii", "replace")


def portrait(face):
    oid = None
    try:
        oid = old_id(face)
    except Error:
        pass
    for n in ["portrait.dds"] + (["%s.dds" % oid] if oid else []):
        p = os.path.join(face, n)
        if os.path.isfile(p):
            return p
    return None


def check(folder):
    """problems with a face folder, as sentences (empty = fine)"""
    face = find(folder) if folder and os.path.isdir(folder) else None
    if not face:
        return ["%s: no face (a folder with #Win\\face.fpk)" % folder]
    try:
        old_id(face)
    except Error as e:
        return [str(e)]
    if not os.path.isdir(os.path.join(face, "sourceimages")):
        return ["%s: no sourceimages folder next to #Win" % face]
    return []


def token(n, length):
    """a texture folder name of length characters for the n-th moved face of a world"""
    t = "m" + _b36(n).rjust(length - 1, "0")
    if length < 2 or len(t) > length:
        raise Error("too many faces with a %d-digit id in one world" % length)
    return t


def _b36(n):
    s = ""
    while True:
        n, r = divmod(n, 36)
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + s
        if not n:
            return s


def install(root, pid, folder, n=0, log=print):
    """put the face in folder on player pid in the world root; n numbers the made-up texture
    folders of this build (pass a different one per face).  Returns where the textures went."""
    face = find(folder)
    if not face:
        raise Error("%s: no face (a folder with #Win\\face.fpk)" % folder)
    oid = old_id(face)
    new = str(pid)
    tex = new if len(new) == len(oid) else token(n, len(oid))
    dst = os.path.join(root, FACES, new)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.join(dst, "#Win"))
    old_path = b"/Assets/pes16/model/character/face/real/%s/sourceimages/" % oid.encode("ascii")
    new_path = b"/Assets/pes16/model/character/face/real/%s/sourceimages/" % tex.encode("ascii")
    for f in os.listdir(os.path.join(face, "#Win")):
        src = os.path.join(face, "#Win", f)
        if not os.path.isfile(src):
            continue
        b = open(src, "rb").read()
        nb = b.replace(old_path, new_path)
        assert len(nb) == len(b)
        open(os.path.join(dst, "#Win", f), "wb").write(nb)
    tdst = os.path.join(root, FACES, tex, "sourceimages")
    if os.path.exists(tdst):
        shutil.rmtree(tdst)
    shutil.copytree(os.path.join(face, "sourceimages"), tdst)
    p = portrait(face)
    if p:
        os.makedirs(os.path.join(root, PORTRAITS), exist_ok=True)
        shutil.copyfile(p, os.path.join(root, PORTRAITS, "%s.dds" % new))
    log("  face %s -> player %s%s" % (oid, new, "" if tex == new else " (textures in %s)" % tex))
    return tex


def pack(face, out):
    r"""copy a face into out (a package's faces\<n> folder): #Win, sourceimages, portrait.dds"""
    src, face = face, find(face)
    if not face:
        raise Error("no face in %s" % src)
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(face, "#Win"), os.path.join(out, "#Win"))
    shutil.copytree(os.path.join(face, "sourceimages"), os.path.join(out, "sourceimages"))
    p = portrait(face)
    if p:
        shutil.copyfile(p, os.path.join(out, "portrait.dds"))
    return out
