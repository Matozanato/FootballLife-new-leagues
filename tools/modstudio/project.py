"""what the League Builder pages share: the recipe being edited and the game's tables.

The recipe is the same JSON leaguebuilder.py builds from.  The tables are the game's own
Team/Competition/Player tables, unpacked once from the person's game into
%APPDATA%\\FL26ModStudio\\tables (Settings > Unpack the game's tables).
"""
import json, os

from PySide6.QtCore import QObject, Signal

import leaguebuilder as B


def blank():
    return {"world": "_FL26MyWorld", "leagues": [], "edits": {}, "players": {}}


class Project(QObject):
    changed = Signal()          # the recipe changed (any page)
    tables_changed = Signal()   # tables loaded or unloaded

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.recipe = blank()
        self.path = None
        self.dirty = False
        self.base = None
        self.countries, self.parents, self.game_lgs, self.game_cl = [], [], [], {}
        self._squads = None
        self._names = None

    # ---- tables ----
    def tables_dir(self):
        from modstudio.app import APPDIR
        return os.path.join(APPDIR, "tables")

    def load_tables(self, where=None):
        where = where or self.app.settings.get("tables") or None
        try:
            self.base = B.base_dir(where) if where else B.base_dir(self._default_tables())
            self.countries = B.country_names(self.base)
            self.parents = B.shipped_parents(self.base)
            self.game_lgs = B.game_leagues(self.base)
            self.game_cl = B.game_clubs(self.base)
        except (B.BuildError, OSError, ValueError, SystemExit):
            self.base = None
            self.countries, self.parents, self.game_lgs, self.game_cl = [], [], [], {}
        self._squads = None
        self._names = None
        self.tables_changed.emit()
        return self.base

    def _default_tables(self):
        d = os.path.join(self.tables_dir(), "common", "etc", "pesdb")
        return d if os.path.exists(os.path.join(d, "Team.bin")) else self.tables_dir()

    def unpack(self, log=lambda t: None):
        """unpack the tables from the game (slow: run it in a Job)"""
        return B.unpack_tables(self.app.game.folder, self.tables_dir(), log=log)

    def squads(self):
        if self._squads is None and self.base:
            import lbplayers
            self._squads = lbplayers.Squads(self.base)
        return self._squads

    # ---- names by id (for the content-server maps) ----
    def world_tables(self):
        """pesdb folders of the League Builder worlds switched on in sider.ini"""
        from modstudio.siderini import root_path
        out = []
        ini = self.app.ini() if hasattr(self.app, "ini") else None
        for e in (ini.entries("cpk.root") if ini else []):
            d = root_path(self.app.game.sider_dir, e.value)
            db = os.path.join(d, "common", "etc", "pesdb")
            if e.enabled and os.path.basename(d).startswith("_FL26") \
                    and os.path.exists(os.path.join(db, "Team.bin")):
                out.append(db)
        return out

    def names(self):
        """({team id: name}, {tournament id: name}); tournament id = regulation id, and the
        later stages of a competition are id + 1024 * k"""
        if self._names is None:
            teams, comps = {}, {65535: "Exhibition"}
            for db in ([self.base] if self.base else []) + self.world_tables():
                try:
                    teams.update({k: v[0] for k, v in B.game_clubs(db).items()})
                    regs = B.M.load(db, "CompetitionRegulation.bin")
                    for i in range(len(regs) // B.M.REG):
                        g = regs[i * B.M.REG:(i + 1) * B.M.REG]
                        rid = B.u16(g, B.M.R_ID)
                        name = B.text(g[B.M.R_NAME:B.M.R_NAME + B.M.NAME_SLOT])
                        if name and rid not in comps:
                            comps[rid] = name
                except (OSError, ValueError, B.BuildError):
                    pass
            self._names = (teams, comps)
        return self._names

    def team_name(self, tid):
        return self.names()[0].get(tid, "")

    def comp_name(self, tid):
        comps = self.names()[1]
        if tid in comps:
            return comps[tid]
        if tid >= 1024 and tid % 1024 in comps:
            return "%s (stage %d)" % (comps[tid % 1024], tid // 1024 + 1)
        return ""

    # ---- recipe ----
    def touch(self):
        self.dirty = True
        self.changed.emit()

    def edits(self, kind):
        return self.recipe.setdefault("edits", {}).setdefault(kind, {})

    def players(self):
        return self.recipe.setdefault("players", {})

    def league(self, name):
        return next((L for L in self.recipe["leagues"] if L["name"] == name), None)

    def rename_league(self, old, new):
        """keep everything that names a league by name pointing at it"""
        if old == new:
            return
        for L in self.recipe["leagues"]:
            if L.get("above") == old:
                L["above"] = new
        pl = self.players()
        for k in list(pl):
            lg, _s, n = k.rpartition("/")
            if lg == old:
                pl["%s/%s" % (new, n)] = pl.pop(k)
        for p in (self.recipe.get("packs") or {}).values():
            p["leagues"] = [new if n == old else n for n in p.get("leagues") or []]
            p["players"] = ["%s/%s" % (new, k.rpartition("/")[2]) if k.rpartition("/")[0] == old else k
                            for k in p.get("players") or []]

    def drop_league(self, name, keep=0):
        """forget player changes of a league's clubs from place `keep` on (all when 0)"""
        pl = self.players()
        for k in list(pl):
            lg, _s, n = k.rpartition("/")
            if lg == name and n.isdigit() and int(n) >= keep:
                pl.pop(k)

    def new(self):
        self.recipe, self.path, self.dirty = blank(), None, False
        self.changed.emit()

    def open(self, path):
        r = json.load(open(path, encoding="utf-8"))
        if not str(r.get("world", "")).startswith("_FL26"):
            raise B.BuildError("the world name must start with _FL26")
        r.setdefault("leagues", [])
        r.setdefault("edits", {})
        r.setdefault("players", {})
        self.recipe, self.path, self.dirty = r, path, False
        self.changed.emit()

    def save(self, path=None):
        path = path or self.path
        clean = dict(self.recipe)
        clean["players"] = {k: v for k, v in (clean.get("players") or {}).items()
                            if v.get("edits") or v.get("add") or v.get("remove")}
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=1, ensure_ascii=False)
        os.replace(path + ".tmp", path)
        self.path, self.dirty = path, False
        self.changed.emit()
