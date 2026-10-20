r"""python tools/test_trophies.py [folder with the game's tables]

Trophies of the competitions (0.2.5, mato 21.10.: "only pairing trophy models with a competition;
no visibly borrowed trophy; with no model paired nothing changes"; through FL26's own Entrance.lua).

Offline: the phase folders of a trophy (FL26's layout), the plan's problems (a folder gone), the
block Switch on writes in Entrance.lua run in Lua (lupa) as Sider runs the module: a paired
competition's matches and final get the world's trophy folder and entry 16, every other
tournament id gets exactly what it got before; a world gone (no trophies.json) changes nothing;
Switch on of a world with no trophies gives the file back byte for byte; twice is one block.
FL26's own Entrance.lua as well when it is in E:\instalacija or %FL26_DIR%.
With the game's tables: Build copies the folders into the world with every regulation id of the
competition (the group rows too), and Switch on writes them.
"""
import json, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lbtrophies as T

N = 0
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ok(name, cond):
    global N
    assert cond, name
    N += 1
    print("ok %d - %s" % (N, name))


# the shape of FL26's Entrance.lua (FuNZoTiK / VirtuaRed), cut down to a few competitions
SAMPLE = r'''--Entrances / Trophies / Animations for PES 2021

local fileroot = ".\\content\\Entrance"
local entry
local tid

local function set_random(ctx)
	rdm = math.random (1,4)
	tid = ctx.tournament_id
	home = ctx.home_team
	away = ctx.away_team
end

function make_key(ctx, filename)
    	if tid == 2 or tid == 1026 then
	     entry = 16
	     Entrance = "UEFA Champions League\\Group_Knockout"
	elseif tid == 59 then
	 	 entry = 16
	     if ctx.match_info == 53 then
			Entrance = "Copa Argentina\\Final"
		 else
			Entrance = "Copa Argentina\\Eliminatorias"
		 end
	elseif tid == 65535 then
		entry = 16
		Entrance = "Default"
	else
	   entry = nil
    end

    if tid then
       return string.format("%s:%s", Entrance, filename)
    end
end

function trophy_rewrite(ctx, tournament_id)
   if entry ~= nil then
      local tid = entry
      if tid then
	     Entrance = string.gsub(Entrance, "\\Final", "")
	     Entrance = string.gsub(Entrance, "\\Group_Knockout", "")
    	 return tid
      end
   end
end

local function get_filepath(ctx, filename, key)
    if key then
        return string.format("%s\\%s\\%s", fileroot, Entrance, filename)
    end
end

function init(ctx)
    if fileroot:sub(1,1)=='.' then
        fileroot = ctx.sider_dir .. fileroot
    end
	math.randomseed(os.time())
    ctx.register("set_teams", set_random)
    ctx.register("trophy_rewrite", trophy_rewrite)
    ctx.register("livecpk_make_key", make_key)
    ctx.register("livecpk_get_filepath", get_filepath)
end

return { init = init }
'''.replace("\n", "\r\n")

TIDS = [2, 1026, 59, 60, 182, 262, 1286, 65535, 0]


def lua():
    try:
        from lupa import luajit21 as lj
    except ImportError:
        try:
            from lupa import lua51 as lj
        except ImportError:
            from lupa import LuaRuntime
            return LuaRuntime()
    return lj.LuaRuntime()


def run(sider, text, tids=TIDS):
    """{tid: (make_key, trophy_rewrite, get_filepath) for a match and a final} of the module <text>
    loaded the way Sider loads it, with sider_dir <sider>"""
    out = {}
    for t in tids:
        for mi in (1, 53):
            # a Lua of its own each time: Entrance.lua keeps the last folder in a global, so what an
            # id gets would hang on the ones asked before it
            L = lua()
            L.globals().log = lambda *a: None          # Sider's
            reg = L.eval("{}")
            ctx = L.eval("{}")
            ctx["sider_dir"] = sider + "\\"
            ctx["register"] = lambda name, fn, reg=reg: reg.__setitem__(name, fn)
            mod = L.execute(text)
            mod["init"](ctx)
            c = L.eval("{}")
            c["tournament_id"], c["match_info"], c["home_team"], c["away_team"] = t, mi, 101, 102
            reg["set_teams"](c)
            k = reg["livecpk_make_key"](c, "x.fmdl")
            r = reg["trophy_rewrite"](c, t)
            p = reg["livecpk_get_filepath"](c, "x.fmdl", k)
            out[(t, mi)] = (k, r, p)
    return out


def trophy(folder, *subs):
    for s in subs:
        d = os.path.join(folder, s, "common", "demo", "prop", "cup_afc_cl_hi")
        os.makedirs(d)
        open(os.path.join(d, "cup_afc_cl_hi.fmdl"), "wb").write(b"x")
    return folder


def offline():
    tmp = tempfile.mkdtemp(prefix="trophies-")
    try:
        a = trophy(os.path.join(tmp, "a"), "Eliminatorias", "Final")
        ok("phases: a phase folder for the matches, Final for the final", T.phases(a) == ("Eliminatorias", "Final"))
        b = trophy(os.path.join(tmp, "b"), "")
        ok("phases: the files at the top serve every match", T.phases(b) == ("", ""))
        c = trophy(os.path.join(tmp, "c"), "Final")
        ok("phases: Final alone serves the final and the rest", T.phases(c) == ("Final", "Final"))
        d = trophy(os.path.join(tmp, "d"), "Group_Knockout", "Final", "Zzz")
        ok("phases: a known phase folder first", T.phases(d)[0] == "Group_Knockout")
        os.makedirs(os.path.join(tmp, "empty"))
        p = T.problems({"trophies": {"49": a, "50": os.path.join(tmp, "gone"), "51": os.path.join(tmp, "empty"),
                                     "x": a}})
        ok("problems: a folder gone, an empty one, a key that is no id (%d)" % len(p),
           len(p) == 3 and any("gone" in t for t in p) and any("no files" in t for t in p))
        ok("problems: none for good folders", T.problems({"trophies": {"49": a}}) == [])

        sider = os.path.join(tmp, "SiderAddons")
        os.makedirs(os.path.join(sider, "modules"))
        os.makedirs(os.path.join(sider, "content", "Entrance"))
        path = os.path.join(sider, "modules", "Entrance.lua")
        open(path, "w", encoding="latin-1", newline="").write(SAMPLE)
        ok("module_path finds FL26's Entrance.lua", os.path.normcase(T.module_path(sider) or "") == os.path.normcase(path))
        check_module(sider, path, SAMPLE, a)
        real = [os.path.join(r, "SiderAddons", "modules", "Entrance.lua")
                for r in (os.environ.get("FL26_DIR", ""), r"E:\instalacija", r"C:\Football Life 2026") if r]
        real = next((p for p in real if os.path.exists(p)), None)
        if real:
            text = open(real, encoding="latin-1", newline="").read()
            open(path, "w", encoding="latin-1", newline="").write(text)
            print("   FL26's own: %s" % real)
            check_module(sider, path, text, a)
        else:
            print("skip - FL26's own Entrance.lua (not on this PC)")
        open(path, "w", encoding="latin-1", newline="").write("-- another Entrance.lua\nfunction init(ctx) end\n")
        ok("a module of another shape is left alone", T.module_path(sider) is None
           and not T.switch_on(sider, "_FL26T", os.path.join(sider, "livecpk", "_FL26T"), log=lambda t: None))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_module(sider, path, text, folder):
    before = run(sider, text)
    world = os.path.join(sider, "livecpk", "_FL26T")
    shutil.rmtree(world, ignore_errors=True)
    os.makedirs(os.path.join(world, T.FOLDER))
    shutil.copytree(folder, os.path.join(world, T.FOLDER, "49"))
    index = {"49": {"rids": [59, 1083], "match": "Eliminatorias", "final": "Final"},
             "222": {"rids": [262, 1286], "match": "", "final": ""}}
    shutil.copytree(folder, os.path.join(world, T.FOLDER, "222"))
    json.dump(index, open(os.path.join(world, T.FOLDER, T.INDEX), "w"))
    said = []
    T.switch_on(sider, "_FL26T", world, said.append)
    once = open(path, encoding="latin-1", newline="").read()
    ok("Switch on writes the block (%s)" % said[-1], once != text and T.BEGIN in once)
    T.switch_on(sider, "_FL26T", world, said.append)
    ok("Switch on again: still one block", open(path, encoding="latin-1", newline="").read() == once)
    ok("the line ends of the file are kept", once.count("\r\n") == once.count("\n") if "\r\n" in text else "\r\n" not in once)
    moved = "".join(T.rename_lines(once.splitlines(True), "_FL26T", "_FL26T2"))
    ok("Rename: our block follows the world's new name, the rest of the file as it was",
       "\\\\livecpk\\\\_FL26T2\\\\trophies" in moved and "\\\\livecpk\\\\_FL26T\\\\" not in moved
       and "".join(T.strip(moved.split("\n"))) == "".join(T.strip(once.split("\n"))))
    after = run(sider, once)
    norm = lambda p: os.path.normcase(os.path.normpath(p))
    k, r, p = after[(59, 1)]
    ok("a paired competition's match: its trophy's phase folder (%s), entry 16" % k,
       k.endswith("trophies\\49\\Eliminatorias:x.fmdl") and r == 16
       and norm(p) == norm(os.path.join(world, T.FOLDER, "49", "Eliminatorias", "x.fmdl")))
    k, r, p = after[(59, 53)]
    ok("its final: the Final folder, and the ceremony from the trophy's own (%s)" % p,
       k.endswith("trophies\\49\\Final:x.fmdl") and r == 16
       and norm(p) == norm(os.path.join(world, T.FOLDER, "49", "x.fmdl")))
    ok("a group row of a paired new cup (1286) and the cup itself (262): its folder",
       all(after[(t, 1)][1] == 16 and norm(after[(t, 1)][2]) == norm(os.path.join(world, T.FOLDER, "222", "x.fmdl"))
           for t in (262, 1286)))
    same = [t for t in TIDS if t not in (59, 262, 1286, 1083)]
    ok("every other tournament id gets what it got before (%s)" % same,
       all(after[(t, m)] == before[(t, m)] for t in same for m in (1, 53)))
    os.remove(os.path.join(world, T.FOLDER, T.INDEX))
    ok("the world gone (no trophies.json): nothing changes, no trophy borrowed", run(sider, once) == before)
    os.makedirs(os.path.join(sider, "livecpk", "_FL26Other"), exist_ok=True)
    T.switch_on(sider, "_FL26Other", os.path.join(sider, "livecpk", "_FL26Other"), said.append)
    ok("Switch on of a world with no trophies: the file back byte for byte",
       open(path, encoding="latin-1", newline="").read() == text)


def built(tables):
    import leaguebuilder as B
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    game = tempfile.mkdtemp(prefix="trophies-game-")
    try:
        sider = os.path.join(game, "SiderAddons")
        os.makedirs(os.path.join(sider, "livecpk"))
        os.makedirs(os.path.join(sider, "modules"))
        open(os.path.join(sider, "modules", "Entrance.lua"), "w", encoding="latin-1", newline="").write(SAMPLE)
        with open(os.path.join(sider, "sider.ini"), "w") as f:
            f.write("[sider]\ncpk.root = \".\\livecpk\\root\"\n")
        a = trophy(os.path.join(game, "mine"), "Eliminatorias", "Final")
        recipe = {"world": "_FL26Trophy", "leagues": [{"name": "Liga Trofeo", "country": "Colombia", "clubs": 10,
                                                       "legs": 2}]}
        cups = {c: rids for c, _n, rids in B.game_competitions(base)}
        cid = next(c for c, rids in sorted(cups.items()) if 59 in rids)
        pl = B.plan(dict(recipe, trophies={str(cid): a, "999": a}), base)
        ok("the plan carries the trophies", pl["trophies"] == {str(cid): a, "999": a})
        said = []
        B.build(pl, base, game, False, log=lambda t: said.append(str(t)))
        root = os.path.join(sider, "livecpk", "_FL26Trophy")
        index = json.load(open(os.path.join(root, T.FOLDER, T.INDEX), encoding="utf-8"))
        ok("Build: the trophy of competition %d with all its regulation ids %s" % (cid, index[str(cid)]["rids"]),
           59 in index[str(cid)]["rids"] and os.path.isfile(os.path.join(root, T.FOLDER, str(cid), "Final", "common",
                                                                          "demo", "prop", "cup_afc_cl_hi",
                                                                          "cup_afc_cl_hi.fmdl")))
        ok("a competition the world does not have is left out, with a warning",
           "999" not in index and any("999" in t and "warning" in t for t in said))
        key = B.input_key(pl, base, game)
        open(os.path.join(a, "Final", "new.ftex"), "wb").write(b"y")
        ok("a file put in a trophy folder makes the next Build a full one", B.input_key(pl, base, game) != key)
        B.switch_on("_FL26Trophy", game, log=lambda t: said.append(str(t)))
        text = open(os.path.join(sider, "modules", "Entrance.lua"), encoding="latin-1", newline="").read()
        ok("Switch on writes the world's trophies in Entrance.lua",
           T.BEGIN in text and "_FL26Trophy" in text and "[59] =" in text)
    finally:
        shutil.rmtree(game, ignore_errors=True)


def ui(tables):
    """Leagues > More > Trophies in this process (offscreen): pick a folder for a competition of
    the game, see it in its row with the competition's ids, take it off, keep it in the recipe"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFileDialog
    QApplication.instance() or QApplication([])
    import leaguebuilder as B
    from modstudio.project import Project
    from modstudio.pages import builder as PB
    deep = os.path.join(tables, "common", "etc", "pesdb")
    base = B.base_dir(deep if os.path.isdir(deep) else tables)
    tmp = tempfile.mkdtemp(prefix="trophies-ui-")
    try:
        a = trophy(os.path.join(tmp, "mine"), "Final")
        p = Project(None)
        p.base = base
        p.recipe["world"] = "_FL26TrophyUI"
        d = PB.TrophiesDialog(None, p, os.path.join(tmp, "no world yet"))
        rows = {d.table.topLevelItem(i).data(0, Qt.UserRole): d.table.topLevelItem(i)
                for i in range(d.table.topLevelItemCount())}
        cid = next(c for c, it in rows.items() if "59" in it.text(3).split(", "))
        ok("Trophies lists the game's competitions with their ids (%d; %s = %s)" % (len(rows), cid, rows[cid].text(0)),
           len(rows) > 50 and rows[cid].text(4) == "")
        d.table.setCurrentItem(rows[cid])
        was = QFileDialog.getExistingDirectory
        QFileDialog.getExistingDirectory = staticmethod(lambda *x, **k: a)
        d.pick()
        it = next(d.table.topLevelItem(i) for i in range(d.table.topLevelItemCount())
                  if d.table.topLevelItem(i).data(0, Qt.UserRole) == cid)
        ok("Pick a trophy folder: the folder in the competition's row", d.trophies == {cid: os.path.normpath(a)}
           and it.text(4) == os.path.normpath(a))
        d.table.setCurrentItem(it)
        d.clear()
        ok("No trophy of its own takes it off", d.trophies == {})
        d.table.setCurrentItem(next(d.table.topLevelItem(i) for i in range(d.table.topLevelItemCount())
                                    if d.table.topLevelItem(i).data(0, Qt.UserRole) == cid))
        d.pick()
        QFileDialog.getExistingDirectory = was
        ok("the dialog fits a 1920x1080 screen", d.minimumWidth() <= 1920 and d.minimumHeight() <= 1000)
        p.recipe["trophies"] = d.trophies
        again = PB.TrophiesDialog(None, p, None)
        ok("opened again it shows the pairing", again.trophies == {cid: os.path.normpath(a)})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    offline()
    tables = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("APPDATA", ""), "FL26ModStudio", "tables")
    if os.path.isdir(tables):
        ui(tables)
        built(tables)
    else:
        print("skip - the build (no game's tables at %s)" % tables)
    print("test_trophies: ok (%d)" % N)
