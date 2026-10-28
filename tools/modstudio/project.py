"""what the League Builder pages share: the recipe being edited and the game's tables.

The recipe is the same JSON leaguebuilder.py builds from.  The tables are the game's own
Team/Competition/Player tables, unpacked once from the person's game into
%APPDATA%\\FL26ModStudio\\tables (Settings > Unpack the game's tables).
"""
import copy, json, os, pickle, shutil, time, zlib

from PySide6.QtCore import QObject, Signal

import leaguebuilder as B

NATIONAL, OTHERS = -2, -3          # the two groups of teams in no league (game_groups)


def blank():
    return {"world": "_FL26MyWorld", "leagues": [], "edits": {}, "players": {}}


class Project(QObject):
    changed = Signal()          # the recipe changed (any page)
    saved = Signal()            # it was saved by itself (autosave)
    tables_changed = Signal()   # tables loaded or unloaded

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.recipe = blank()
        self.path = None
        self.dirty = False
        # 0.2.5: Undo and Redo of the whole world (mato 16.10.): a copy of the recipe before each
        # change, up to 30 back; touches within a third of a second are one step
        self._undo, self._redo, self._snap, self._snap_at = [], [], self._clone(self.recipe), 0.0
        self.base = None
        self.overlay = 0            # files of the chosen tables folder laid over the game's (0: a full set)
        self.tables_error = ""
        self.countries, self.parents, self.game_lgs, self.game_cl = [], [], [], {}
        self.calendar_parents = set()
        self.confeds = {}
        self.game_nat, self.game_other = [], []
        self.game_confeds = {}
        self.parent_tiers = {}
        self._squads = None
        self._names = None
        # 0.2.5: World options > Players per new club -- the world's squad is the one every page and
        # Build count new clubs' places with (connected first, so it is set before a page reads it)
        self.changed.connect(lambda: B.use_squad(self.recipe))

    # ---- tables ----
    def tables_dir(self):
        from modstudio.app import APPDIR
        return os.path.join(APPDIR, "tables")

    def _tables_of(self, where):
        """the tables folder to read for the chosen folder where. A mod's database (a pesdb folder
        in livecpk) usually holds only the tables it changes, Team.bin and Player.bin but no
        CompetitionRegulation.bin (jibibi 09.10.): its files then go over a copy of the game's
        unpacked tables, which give the rest"""
        d = where
        for sub in (("common", "etc", "pesdb"), ("etc", "pesdb"), ("pesdb",)):
            if os.path.isdir(os.path.join(where, *sub)):
                d = os.path.join(where, *sub)
                break
        if os.path.exists(os.path.join(d, "CompetitionRegulation.bin")):
            return d
        mine = [n for n in os.listdir(d) if n.lower().endswith(".bin") and os.path.isfile(os.path.join(d, n))]             if os.path.isdir(d) else []
        if not mine:
            raise B.BuildError("no tables in that folder")
        game = self._default_tables()
        if not os.path.exists(os.path.join(game, "CompetitionRegulation.bin")):
            raise B.BuildError("only part of the tables: unpack the game's tables first")
        out = os.path.join(self.tables_dir() + "-with-your-database", "pesdb")
        os.makedirs(out, exist_ok=True)
        for n in set(os.listdir(game)) | set(mine):
            src = os.path.join(d if n in mine else game, n)
            dst = os.path.join(out, n)
            if not os.path.isfile(src):
                continue
            a = os.stat(src)
            b = os.stat(dst) if os.path.exists(dst) else None
            if b is None or b.st_size != a.st_size or int(b.st_mtime) != int(a.st_mtime):
                shutil.copy2(src, dst)
        # the game's kits file beside them: Build draws the new clubs' kits from it (B143: with
        # your own tables it found none and drew no kit)
        rel = B.UNIPAR.replace("/", os.sep)
        src = B.kits_file(d) or os.path.join(self.tables_dir(), rel)
        dst = os.path.join(os.path.dirname(out), rel)
        if os.path.isfile(src):
            a = os.stat(src)
            b = os.stat(dst) if os.path.exists(dst) else None
            if b is None or b.st_size != a.st_size or int(b.st_mtime) != int(a.st_mtime):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        self.overlay = len(mine)
        return out

    def load_tables(self, where=None):
        where = where or self.app.settings.get("tables") or None
        # B218: a whole database mod as the tables has no kits file beside it; the game's unpacked one then
        B.KITS_FALLBACK[:] = [os.path.join(self.tables_dir(), B.UNIPAR.replace("/", os.sep))]
        self.overlay, self.tables_error = 0, ""
        try:
            self.base = B.base_dir(self._tables_of(where)) if where else B.base_dir(self._default_tables())
            self.countries = B.country_names(self.base)
            self.confeds = B.country_confederations(self.base)
            self.parents = B.shipped_parents(self.base)
            self.parent_tiers = B.shipped_tiers(self.base)
            self.calendar_parents = B.shipped_calendar(self.base)
            self.game_lgs = B.game_leagues(self.base)
            self.game_cl = B.game_clubs(self.base)
            self.game_nat, self.game_other = B.game_others(self.base, self.game_lgs)
            self.game_confeds = B.game_league_confeds(self.base, self.game_lgs)
        except (B.BuildError, OSError, ValueError, SystemExit, AssertionError, zlib.error) as e:
            # a .bin that is not one of the game's packed tables (a patch's files copied over them)
            self.tables_error = (str(e) if isinstance(e, (B.BuildError, OSError, ValueError, SystemExit))
                                 else "one of the .bin files in the tables folder is not a game table "
                                      "(a patch's files copied over it?) -- put the original tables back "
                                      "or choose another tables folder in Settings")
            self.base = None
            self.countries, self.parents, self.game_lgs, self.game_cl = [], [], [], {}
            self.confeds = {}
            self.game_nat, self.game_other = [], []
            self.game_confeds = {}
            self.parent_tiers = {}
            self.calendar_parents = set()
        self._squads = None
        self._names = None
        self.tables_changed.emit()
        return self.base

    def formations(self):
        """the formations a new club can take (leaguebuilder.formations), [] with no tables"""
        return B.formations(self.base) if self.base else []

    def club_places(self, key):
        """the formation's places of a new club ("<league>/<k>"): its own, the league's, or
        None for the engine's fixed 4-2-3-1"""
        lg, _s, k = key.rpartition("/")
        L = self.league(lg)
        if not L or not k.isdigit():
            return None
        own = list(L.get("club_formations") or [])
        want = (own[int(k)] if int(k) < len(own) else "") or L.get("formation") or ""
        return next((e["places"] for e in self.formations() if want and e["label"] == want), None)

    def game_groups(self):
        """[(group id, name, [team ids])] of the teams in no league (the game's "Others"
        sections); group ids are negative so they never meet a regulation id"""
        from modstudio.i18n import _
        return [(g, name, t) for g, name, t in ((NATIONAL, _("National teams"), self.game_nat),
                                                  (OTHERS, _("Other clubs (no league)"), self.game_other)) if t]

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

    def other_databases(self):
        """the database mods (UML ...) switched on in sider.ini whose own tables a world built from
        the game's plain tables would hide (#36): enabled roots, not ours, with a pesdb folder
        holding competition or team tables. Empty when the tables in Settings are a mod's own."""
        if self.app.settings.get("tables"):
            return []
        from modstudio.siderini import root_path
        ini = self.app.ini() if hasattr(self.app, "ini") else None
        out = []
        for e in (ini.entries("cpk.root") if ini else []):
            d = root_path(self.app.game.sider_dir, e.value)
            db = os.path.join(d, "common", "etc", "pesdb")
            if e.enabled and not os.path.basename(d).startswith("_FL26") and any(
                    os.path.exists(os.path.join(db, f)) for f in ("Competition.bin", "CompetitionRegulation.bin",
                                                                     "CompetitionEntry.bin", "Team.bin")):
                out.append(os.path.basename(d))
        return out

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

    def live_worlds(self):
        """names of the League Builder worlds switched on in sider.ini, the way it lists them"""
        return [os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(db))))
                for db in self.world_tables()]

    def drop_names(self):
        """a world built or switched on in this session has clubs of its own: drop the cached
        club lists so the pickers (Kits > Add a line and every other club picker) read them
        again (GitHub #87)"""
        self._names = None

    def names(self):
        """({team id: name}, {tournament id: name}); tournament id = regulation id, and the
        later stages of a competition are id + 1024 * k"""
        if self._names is None:
            teams, comps, cid_of = {}, {65535: "Exhibition"}, {}
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
                        cid_of[rid] = g[B.M.R_CID]          # a world's own wins over the game's
                except (OSError, ValueError, B.BuildError):
                    pass
            self._stages = {}
            for rid, cid in sorted(cid_of.items()):
                self._stages.setdefault(cid, []).append(rid)
            self._names = (teams, comps)
        return self._names

    def comp_stages(self, cid):
        """the tournament ids (regulations) of competition cid: the Conference League (174) is
        186, 1210, 187, 189 and its later rounds 1213 ... 8381. A content server is asked by
        tournament id, so a line keyed by the competition id itself is never used (mauro1977doni:
        "174" gave the Conference League no scoreboard)."""
        self.names()
        return list(self._stages.get(cid, []))

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
        self._remember()
        self.dirty = True
        self.changed.emit()
        self._autosave_soon()

    def mark(self):
        """a change the page shows by itself (Players): kept and saved like touch(), without the
        changed signal that fills the pages again. Players set dirty alone, so nothing saved it
        and closing asked about changes while the status bar said the world was saved"""
        self._remember()
        self.dirty = True
        self._autosave_soon()

    # ---- undo ----
    # B267 (JoJofiaz 29.10.): each step kept a full copy of the recipe, about 160 MB in memory for a
    # world of 1,300 new clubs (its players are most of it), so 30 steps took 5 GB and more. A step
    # is now the recipe pickled and zlib-packed: 5-9 MB, and quicker to make than a deepcopy.
    @staticmethod
    def _pack(state):
        return zlib.compress(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL), 3)

    @staticmethod
    def _unpack(blob):
        return pickle.loads(zlib.decompress(blob))

    @staticmethod
    def _clone(state):
        try:
            return pickle.loads(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            return copy.deepcopy(state)

    def _remember(self):
        """keep the recipe as it was before this change (one step for touches close together)"""
        if self.recipe == self._snap:
            return
        now = time.monotonic()
        if now - self._snap_at > 0.3:
            self._undo.append(self._pack(self._snap))
            del self._undo[:-30]
        self._redo.clear()
        self._snap, self._snap_at = self._clone(self.recipe), now

    def _forget(self):
        self._undo, self._redo, self._snap, self._snap_at = [], [], self._clone(self.recipe), 0.0

    def can_undo(self):
        return bool(self._undo)

    def can_redo(self):
        return bool(self._redo)

    def _restore(self, blob):
        """the recipe becomes the packed state `blob` in place: the pages keep their references to
        the dict"""
        state = self._unpack(blob)
        self.recipe.clear()
        self.recipe.update(state)
        self._snap, self._snap_at = self._unpack(blob), 0.0
        self.dirty = True
        self.changed.emit()
        self._autosave_soon()

    def undo(self):
        """back one change; True when there was one"""
        if not self._undo:
            return False
        self._redo.append(self._pack(self.recipe))
        self._restore(self._undo.pop())
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self._pack(self.recipe))
        self._restore(self._redo.pop())
        return True

    def _autosave_soon(self):
        """0.2.4: your world keeps itself (no Save recipe to remember): a change is saved a moment
        after the last one"""
        from PySide6.QtCore import QCoreApplication, QTimer
        if QCoreApplication.instance() is None or getattr(self.app, "settings", None) is None:
            return
        if getattr(self, "_timer", None) is None:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(1500)
            self._timer.timeout.connect(self.autosave)
        self._timer.start()

    def autosave(self):
        """into the world's own file when it has one, else into the copy the next start opens
        (recipes\\<world>.json, keep_copy); a write that fails leaves it marked not saved, and
        closing asks as before"""
        if not self.dirty:
            return
        try:
            if self.path:
                self._write(self.path)
            else:
                self.app.settings["last_recipe"] = self.keep_copy()
                self.app.save_settings()
        except (OSError, KeyError, TypeError):
            return
        self.dirty = False
        self.saved.emit()

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
        me = self.league(new)
        if me is not None:      # the last Build's ids follow it there (leaguebuilder.plan, built_as)
            me["built_as"] = [x for x in me.get("built_as") or [] if x not in (old, new)] + [old]
        for L in self.recipe["leagues"]:
            if L.get("above") == old:
                L["above"] = new
        pl = self.players()
        for k in list(pl):
            lg, _s, n = k.rpartition("/")
            if lg == old:
                pl["%s/%s" % (new, n)] = pl.pop(k)
        for c in self.recipe.get("preseason_cups") or []:
            c["clubs"] = ["%s/%s" % (new, x.rpartition("/")[2]) if isinstance(x, str) and x.rpartition("/")[0] == old
                          else x for x in c.get("clubs") or []]
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
        for c in self.recipe.get("preseason_cups") or []:      # its clubs leave the pre-season cups
            c["clubs"] = [x for x in c.get("clubs") or [] if not (
                isinstance(x, str) and x.rpartition("/")[0] == name
                and x.rpartition("/")[2].isdigit() and int(x.rpartition("/")[2]) >= keep)]
        L = self.league(name)
        if L and L.get("game_clubs"):                          # and so do its clubs of the game
            for e in L["game_clubs"]:                          # with the release's squads they got
                if int(e.get("at", 0)) >= keep and (pl.get(str(e["id"])) or {}).get("newlife_game"):
                    pl.pop(str(e["id"]))
        if L and keep and L.get("game_clubs"):
            L["game_clubs"] = [e for e in L["game_clubs"] if int(e.get("at", 0)) < keep]
            if not L["game_clubs"]:
                L.pop("game_clubs")

    # the lists that hold one value per club of a new league, and what an empty place holds
    # (a league package's Kit Server folders too: they stayed by place, so after Remove club the
    # clubs below wore the next club's kit -- pepponeee98's Serie C, 14.10.)
    PLACE_LISTS = (("club_names", ""), ("club_abbrs", ""), ("club_crests", None), ("club_coaches", ""),
                   ("club_formations", ""), ("club_ids", ""), ("club_kits", ""), ("club_away_kits", ""),
                   ("kit_folders", ""))

    def move_club(self, name, k, dst):
        """move the new club at place k of league `name` to the end of league `dst`, with its name,
        short name, crest, manager, formation, id, kits, NewLife id, player changes and every
        reference to it (pre-season cups, packs, players who join from it). None, or why not."""
        from modstudio.i18n import _
        A, D = self.league(name), self.league(dst)
        if not A or not D or A is D:
            return "Pick another league."
        if any(int(e.get("at", -1)) == k for e in A.get("game_clubs") or []):
            return "This is a club of the game: take it out with Club of the game and add it in the other league."
        nA, nD = int(A.get("clubs", 0)), int(D.get("clubs", 0))
        if not 0 <= k < nA:
            return "No such club."
        if nA - 1 < B.CLUBS_MIN or nD + 1 > B.CLUBS_MAX:       # translated, then filled in (the page's _(bad) finds no key)
            return _("A league takes %d to %d clubs.") % (B.CLUBS_MIN, B.CLUBS_MAX)
        vals = {key: (list(A.get(key) or []) + [empty] * nA)[k] for key, empty in self.PLACE_LISTS}
        nl_a = list((A.get("newlife") or {}).get("clubs") or [])
        nl_id = nl_a.pop(k) if k < len(nl_a) else None
        src, to = "%s/%d" % (name, k), "%s/%d" % (dst, nD)
        pl = self.players()
        entry = pl.pop(src, None)
        MOVING = "<the club that moves>"

        def place(j):                  # a place of league `name` after the move: (league, place)
            return (name, j) if j < k else (dst, nD) if j == k else (name, j - 1)
        joins = []                     # player refs "league/place/n" of league `name`, fixed after
        for c in pl.values():
            for i, r in enumerate(c.get("join") or []):
                club, _s, n = str(r).rpartition("/")
                if club.rpartition("/")[0] == name and club.rpartition("/")[2].isdigit():
                    joins.append((c["join"], i, "%s/%d/%s" % (place(int(club.rpartition("/")[2])) + (n,))))
        for c in self.recipe.get("preseason_cups") or []:
            c["clubs"] = [MOVING if x == src else x for x in c.get("clubs") or []]
        for p in (self.recipe.get("packs") or {}).values():
            p["players"] = [MOVING if x == src else x for x in p.get("players") or []]
        if not self.shift_places(name, k, -1) or not self.shift_places(dst, nD, 1):
            return _("A league takes %d to %d clubs.") % (B.CLUBS_MIN, B.CLUBS_MAX)
        for key, empty in self.PLACE_LISTS:
            if vals[key] != empty:
                lst = list(D.get(key) or [])
                D[key] = lst + [empty] * (nD + 1 - len(lst))
                D[key][nD] = vals[key]
        if nl_a or (A.get("newlife") or {}).get("clubs"):
            A.setdefault("newlife", {})["clubs"] = nl_a
        if nl_id:
            lst = list((D.get("newlife") or {}).get("clubs") or [])
            D.setdefault("newlife", {})["clubs"] = lst + [0] * (nD - len(lst)) + [nl_id]
        if entry is not None:
            pl[to] = entry
        for lst, i, r in joins:
            lst[i] = r
        for c in self.recipe.get("preseason_cups") or []:
            c["clubs"] = [to if x == MOVING else x for x in c.get("clubs") or []]
        for p in (self.recipe.get("packs") or {}).values():
            p["players"] = [to if x == MOVING else x for x in p.get("players") or []]
        self.touch()
        return None

    def shift_places(self, name, at, delta):
        """insert (delta 1) a new club before place `at` of league `name`, or remove (delta -1)
        the club at place `at`: every list kept per place, the clubs of the game, the player
        changes and the pre-season cups that name its clubs by place move with it. A split
        league's last group takes the difference. Returns False when the league would leave
        leaguebuilder's CLUBS_MIN..CLUBS_MAX clubs."""
        L = self.league(name)
        if not L or delta not in (1, -1):
            return False
        n = int(L.get("clubs", 0))
        if not B.CLUBS_MIN <= n + delta <= B.CLUBS_MAX or not 0 <= at <= n - (delta < 0):
            return False

        def moved(k):                  # a place's new number, None for the one removed
            if k < at:
                return k
            if delta < 0 and k == at:
                return None
            return k + delta

        for key, empty in self.PLACE_LISTS:
            lst = L.get(key)
            if not lst:
                continue
            lst = list(lst)[:n] + [empty] * max(0, n - len(lst))
            if delta > 0:
                lst.insert(at, empty)
            else:
                lst.pop(at)
            L[key] = lst
        # the NewLife ids by place too: a removed club kept its id, and NewLife's "would play in
        # two leagues" check still found Schalke in a Bundesliga 2 it had left (Discord, lub7628)
        nl = (L.get("newlife") or {}).get("clubs")
        if nl and at < len(nl):
            nl = list(nl)
            if delta > 0:
                nl.insert(at, 0)
            else:
                nl.pop(at)
            L["newlife"]["clubs"] = nl
        gc = []
        for e in L.get("game_clubs") or []:
            k = moved(int(e.get("at", 0)))
            if k is not None:
                gc.append(dict(e, at=k))
        if gc:
            L["game_clubs"] = gc
        else:
            L.pop("game_clubs", None)
        pl = self.players()
        old = {k: pl.pop(k) for k in list(pl) if k.rpartition("/")[0] == name and k.rpartition("/")[2].isdigit()}
        for k, v in old.items():
            m = moved(int(k.rpartition("/")[2]))
            if m is not None:
                pl["%s/%d" % (name, m)] = v

        def ref(x):
            if isinstance(x, str) and x.rpartition("/")[0] == name and x.rpartition("/")[2].isdigit():
                m = moved(int(x.rpartition("/")[2]))
                return "" if m is None else "%s/%d" % (name, m)
            return x
        for c in self.recipe.get("preseason_cups") or []:
            c["clubs"] = [ref(x) for x in c.get("clubs") or []]
        for p in (self.recipe.get("packs") or {}).values():
            p["players"] = [r for r in (ref(k) for k in p.get("players") or []) if r]
        L["clubs"] = n + delta
        sp = L.get("split")
        if sp and not L.get("apertura") and sp.get("groups"):
            sp["groups"] = list(sp["groups"])
            sp["groups"][-1] = int(sp["groups"][-1]) + delta
        elif sp and L.get("apertura"):
            sp["groups"] = [n + delta]
        self.touch()
        return True

    def new(self):
        self.recipe, self.path, self.dirty = blank(), None, False
        self._forget()
        self._open_next(None)
        self.changed.emit()

    def _open_next(self, path):
        """B107: the next start opens the world open now. New world and Open left last_recipe on the
        world before, so a world deleted and replaced by a new, untouched one came back at the next
        start"""
        st = getattr(self.app, "settings", None)
        if not isinstance(st, dict) or st.get("last_recipe") == path:
            return
        st["last_recipe"] = path
        try:
            self.app.save_settings()
        except (AttributeError, OSError):
            pass

    def open(self, path, copy=False):
        """load a recipe; copy=True for the copy Build keeps (keep_copy): Save then asks for a name"""
        self.adopt(json.load(open(path, encoding="utf-8")), path, copy)

    def adopt(self, r, path, copy=False):
        """a recipe read already becomes the open one: open() without the reading, for a recipe read
        off the window's thread (the Modpack's is 132 MB, 1.4 s of json.load)"""
        if not str(r.get("world", "")).startswith("_FL26"):
            raise B.BuildError("the world name must start with _FL26")
        if B.is_plan(r):
            # B224: a world's leaguebuilder-plan.json opened as a world (a tester took the one in
            # a downloaded world's folder, and every start then crashed counting its clubs). The
            # recipe it was built from, read back as My world does; Save asks for a name, so the
            # world's own plan is never written over
            if not self.base:
                raise B.BuildError("this is the plan of a built world, not a world file: "
                                   "put the world in the game and open it in My world")
            r, copy = B.recipe_from_plan(r, self.base), True
        r.setdefault("leagues", [])
        r.setdefault("edits", {})
        r.setdefault("players", {})
        self.recipe, self.path, self.dirty = r, None if copy else path, False
        self._forget()
        self._open_next(path)
        self.changed.emit()

    def save(self, path=None):
        path = path or self.path
        self._write(path)
        self.path, self.dirty = path, False
        self.changed.emit()

    def copies_dir(self):
        from modstudio.app import APPDIR
        return os.path.join(APPDIR, "recipes")

    def keep_copy(self):
        """write the recipe to %APPDATA%\\FL26ModStudio\\recipes\\<world>.json and return that path.
        Build keeps one there each time, and the next start opens the latest recipe again, so the
        leagues are not lost when Mod Studio is closed without Save recipe (GitHub #40). The
        recipe's own file, its name and the unsaved mark are not touched."""
        d = self.copies_dir()
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, self.recipe["world"] + ".json")
        self._write(p)
        return p

    def _write(self, path):
        clean = dict(self.recipe)
        clean["players"] = {k: v for k, v in (clean.get("players") or {}).items()
                            if v.get("edits") or v.get("add") or v.get("remove") or v.get("join")
                            or v.get("coach_portrait") or v.get("stadium")}
        # dumps, not dump: dump() streams through the pure-Python encoder, 2.6 s on the Modpack's
        # 132 MB recipe against 0.9 s (the window stood still on a switch, coldstart 17.10.)
        text = json.dumps(clean, indent=1, ensure_ascii=False)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(path + ".tmp", path)
