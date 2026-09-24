r"""python playereditor.py [--root <world>] [--cap 51729]

The player editor with a window: pick a club, pick a player, change anything, save.

It edits the same two files as playeredit.py (Player.bin and PlayerAssignment.bin in the
world's common\etc\pesdb) with the same field map and the same checks, so everything said
there holds here: a value the game cannot store is refused, nothing reaches the disk until
Save, and the originals are kept as .bak the first time.

  Clubs      every club that has players; type in the box above the list to filter it.
  Squad      the club's players in squad order.  The first eleven are the starting eleven,
             placed by the formation in a fixed order; for the new clubs' default 4-2-3-1
             that is GK, CB, CB, RB, LB, DMF, DMF, RMF, LMF, AMF, CF.  Up / Down move the
             selected player one place, swapping with the neighbour.
  Player     four tabs -- Profile, Positions, Abilities, Skills -- with every known field.
             Apply checks the values and keeps them (still in memory only).
  New        a new player at the same club, starting as a copy of the selected one; he gets
             a new player id, the first free shirt number and the last place in the squad.
  Save       writes both files.

Without --root it asks for the world folder (the one that holds `common`).
"""
import os, shutil, sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pesdb
import playeredit as E

PROFILE = ["Registered Position", "Height (cm)", "Weight (kg)", "Age", "Nationality",
           "Stronger Foot", "Weak Foot Usage", "Weak Foot Accuracy", "Form",
           "Injury Resistance", "Playing Style"]
SQUAD_COLS = [("order", "#", 36), ("shirt", "No", 40), ("pos", "Pos", 48), ("name", "Name", 200),
              ("Speed", "Spd", 44), ("Finishing", "Fin", 44), ("Low Pass", "Pas", 44),
              ("Defensive Awareness", "Def", 44), ("GK Reflexes", "GK", 44)]
FORMATION = ["GK", "CB", "CB", "RB", "LB", "DMF", "DMF", "RMF", "LMF", "AMF", "CF"]


class World:
    """the two tables of one world, kept in memory until save()"""

    def __init__(self, root):
        self.db = os.path.join(root, "common", "etc", "pesdb")
        self.ppath, self.players = E.load(self.db, "Player.bin")
        self.apath, self.assigns = E.load(self.db, "PlayerAssignment.bin")
        _, teams = E.load(self.db, "Team.bin")
        if len(self.players) % E.P_REC or len(self.assigns) % E.A_REC:
            raise SystemExit("Player.bin or PlayerAssignment.bin is not a whole number of records")
        self.index = {E.u32(self.players, i * E.P_REC + E.P_ID): i * E.P_REC
                      for i in range(len(self.players) // E.P_REC)}
        self.slot = {}
        for i in range(len(self.assigns) // E.A_REC):
            self.slot.setdefault(E.u32(self.assigns, i * E.A_REC + E.A_PID), i * E.A_REC)
        self.names = {E.u32(teams, i * E.T_REC + E.T_ID):
                      E.cstr(teams[i * E.T_REC + E.T_NAME:i * E.T_REC + E.T_NAME + E.T_NAME_LEN])
                      for i in range(len(teams) // E.T_REC)}
        self.dirty = False

    def rows(self):
        return range(0, len(self.assigns), E.A_REC)

    def clubs(self):
        have = {E.u32(self.assigns, r + E.A_TID) for r in self.rows()}
        return sorted((c for c in have if c in self.names), key=lambda c: (self.names[c].lower(), c))

    def squad(self, club):
        """[(order, shirt, pid, row)] of one club in squad order"""
        out = []
        for r in self.rows():
            if E.u32(self.assigns, r + E.A_TID) == club:
                pack = E.u32(self.assigns, r + E.A_PACK)
                out.append(((pack & E.ORDER_MASK) >> E.ORDER_SHIFT, pack & E.SHIRT_MASK,
                            E.u32(self.assigns, r + E.A_PID), r))
        return sorted(out)

    def rec(self, pid):
        o = self.index[pid]
        return self.players[o:o + E.P_REC]

    def name(self, pid):
        o = self.index[pid]
        return E.cstr(self.players[o + E.P_NAME:o + E.P_NAME + E.P_NAME_LEN]).strip()

    def get(self, pid, field):
        return E.getf(self.rec(pid), field)

    def pack(self, row):
        return E.u32(self.assigns, row + E.A_PACK)

    def set_pack(self, row, pack):
        self.assigns[row + E.A_PACK:row + E.A_PACK + 4] = pack.to_bytes(4, "little")
        self.dirty = True

    def write(self, pid, vals, name):
        o = self.index[pid]
        rec = bytearray(self.players[o:o + E.P_REC])
        old = bytes(rec)
        for n, v in vals.items():
            E.setf(rec, n, v)
        E.natural(rec, old)
        if name != self.name(pid):
            nm = name.encode("utf-8")
            for k in range(E.P_NAME_SLOTS):
                at = E.P_NAME + k * E.P_NAME_LEN
                rec[at:at + E.P_NAME_LEN] = nm + bytes(E.P_NAME_LEN - len(nm))
        if rec != self.players[o:o + E.P_REC]:
            self.players[o:o + E.P_REC] = rec
            self.dirty = True

    def new_player(self, club, src, cap):
        if len(self.index) >= cap:
            raise ValueError("the player table is full: %d players, cap %d (see --cap)"
                             % (len(self.index), cap))
        pid = max(self.index) + 1
        rec = bytearray(self.rec(src))
        rec[E.P_ID:E.P_ID + 4] = pid.to_bytes(4, "little")
        self.index[pid] = len(self.players)
        self.players += rec
        squad = self.squad(club)
        taken = {s for _, s, _, _ in squad}
        shirt = next((n for n in range(1, 100) if n not in taken), 0)
        order = max((o for o, _, _, _ in squad), default=-1) + 1
        if order > 63:
            raise ValueError("a squad has at most 64 places")
        eid = max(E.u32(self.assigns, r + E.A_EID) for r in self.rows()) + 1
        e = bytearray(E.A_REC)
        e[E.A_EID:E.A_EID + 4] = eid.to_bytes(4, "little")
        e[E.A_PID:E.A_PID + 4] = pid.to_bytes(4, "little")
        e[E.A_TID:E.A_TID + 4] = club.to_bytes(4, "little")
        e[E.A_PACK:E.A_PACK + 4] = (order << E.ORDER_SHIFT | shirt).to_bytes(4, "little")
        self.slot[pid] = len(self.assigns)
        self.assigns += e
        self.dirty = True
        return pid

    def save(self):
        for path, raw in ((self.ppath, self.players), (self.apath, self.assigns)):
            if not os.path.exists(path + ".bak"):
                shutil.copyfile(path, path + ".bak")
            open(path, "wb").write(pesdb.wesys_pack(bytes(raw)))
        self.dirty = False


class App:
    def __init__(self, tk_root, world, cap):
        self.tk, self.w, self.cap = tk_root, world, cap
        self.club = self.pid = None
        tk_root.title("FL26 player editor - " + world.db)
        tk_root.protocol("WM_DELETE_WINDOW", self.quit)

        left = ttk.Frame(tk_root, padding=6)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Clubs").pack(anchor="w")
        self.filter = tk.StringVar()
        self.filter.trace_add("write", lambda *_: self.fill_clubs())
        ttk.Entry(left, textvariable=self.filter, width=30).pack(fill="x")
        self.clubs = tk.Listbox(left, width=34, exportselection=False)
        self.clubs.pack(fill="y", expand=True, pady=(4, 0))
        self.clubs.bind("<<ListboxSelect>>", lambda e: self.pick_club())

        mid = ttk.Frame(tk_root, padding=6)
        mid.pack(side="left", fill="both", expand=True)
        self.title = ttk.Label(mid, text="Squad", font=("", 11, "bold"))
        self.title.pack(anchor="w")
        self.tree = ttk.Treeview(mid, columns=[c for c, _, _ in SQUAD_COLS], show="headings",
                                 selectmode="browse")
        for c, h, wd in SQUAD_COLS:
            self.tree.heading(c, text=h)
            self.tree.column(c, width=wd, anchor="w" if c == "name" else "center", stretch=c == "name")
        self.tree.tag_configure("starter", background="#e6f2e6")
        self.tree.pack(fill="both", expand=True, pady=(4, 0))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.pick_player())
        bar = ttk.Frame(mid)
        bar.pack(fill="x", pady=4)
        for text, cmd in (("Up", lambda: self.move(-1)), ("Down", lambda: self.move(1)),
                          ("New player", self.new), ("Save", self.save)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=(0, 4))
        self.status = ttk.Label(mid, text="", foreground="#555")
        self.status.pack(anchor="w")

        right = ttk.Frame(tk_root, padding=6)
        right.pack(side="left", fill="y")
        self.vars = {}
        top = ttk.Frame(right)
        top.pack(fill="x")
        for i, (k, label) in enumerate((("name", "Name"), ("shirt", "Shirt"), ("order", "Squad order"))):
            ttk.Label(top, text=label).grid(row=i, column=0, sticky="w")
            self.vars[k] = tk.StringVar()
            ttk.Entry(top, textvariable=self.vars[k], width=34 if k == "name" else 8).grid(
                row=i, column=1, sticky="w", pady=1)
        tabs = ttk.Notebook(right)
        tabs.pack(fill="both", expand=True, pady=6)
        self.form(tabs, "Profile", PROFILE, 1)
        self.form(tabs, "Positions", E.POSITIONS, 1)
        self.form(tabs, "Abilities", [n for n, _ in E.ABILITIES], 2)
        sk = ttk.Frame(tabs, padding=6)
        tabs.add(sk, text="Skills")
        for i, (n, _) in enumerate(E.SKILLS):
            self.vars[n] = tk.IntVar()
            ttk.Checkbutton(sk, text=n, variable=self.vars[n]).grid(
                row=i % 16, column=i // 16, sticky="w", padx=(0, 10))
        ttk.Button(right, text="Apply", command=self.apply).pack(anchor="e")

        self.fill_clubs()
        tk_root.update_idletasks()
        tk_root.minsize(min(tk_root.winfo_reqwidth(), tk_root.winfo_screenwidth()),
                        min(tk_root.winfo_reqheight(), tk_root.winfo_screenheight() - 80))

    def form(self, tabs, title, fields, cols):
        f = ttk.Frame(tabs, padding=6)
        tabs.add(f, text=title)
        per = (len(fields) + cols - 1) // cols
        for i, n in enumerate(fields):
            r, c = i % per, (i // per) * 2
            ttk.Label(f, text=n).grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 14, 4))
            self.vars[n] = tk.StringVar()
            if n == "Registered Position":
                w = ttk.Combobox(f, textvariable=self.vars[n], values=E.POSITIONS, width=8, state="readonly")
            elif n == "Stronger Foot":
                w = ttk.Combobox(f, textvariable=self.vars[n], values=["Right", "Left"], width=8, state="readonly")
            else:
                lo, hi = E.LIMITS[n]
                w = ttk.Spinbox(f, textvariable=self.vars[n], from_=lo, to=hi, width=8)
            w.grid(row=r, column=c + 1, sticky="w", pady=1)
        if title == "Positions":
            ttk.Label(f, text="0 none, 1 can play, 2 natural", foreground="#555").grid(
                row=per, column=0, columnspan=2, sticky="w", pady=(8, 0))

    # ---- lists
    def fill_clubs(self):
        q = self.filter.get().strip().lower()
        self.club_ids = [c for c in self.w.clubs() if q in self.w.names[c].lower() or q == str(c)]
        self.clubs.delete(0, "end")
        for c in self.club_ids:
            self.clubs.insert("end", "%s  (%d)" % (self.w.names[c], c))

    def pick_club(self):
        sel = self.clubs.curselection()
        if sel and self.leave():
            self.club = self.club_ids[sel[0]]
            self.pid = None
            self.fill_squad()

    def fill_squad(self, keep=None):
        self.tree.delete(*self.tree.get_children())
        squad = self.w.squad(self.club)
        for k, (order, shirt, pid, _) in enumerate(squad):
            pos = E.POSITIONS[self.w.get(pid, "Registered Position")] \
                if self.w.get(pid, "Registered Position") < 13 else "?"
            self.tree.insert("", "end", iid=str(pid), tags=("starter",) if k < 11 else (),
                             values=[order, shirt, pos, self.w.name(pid)] +
                                    [self.w.get(pid, c) for c, _, _ in SQUAD_COLS[4:]])
        self.title.config(text="%s  -  %d players" % (self.w.names[self.club], len(squad)))
        want = self.formation_note(squad)
        self.status.config(text=want)
        if keep is not None and self.tree.exists(str(keep)):
            self.tree.selection_set(str(keep))
            self.tree.see(str(keep))

    def formation_note(self, squad):
        off = [(k, E.POSITIONS[self.w.get(p, "Registered Position")], FORMATION[k])
               for k, (_, _, p, _) in enumerate(squad[:11])
               if self.w.get(p, "Registered Position") < 13
               and E.POSITIONS[self.w.get(p, "Registered Position")] != FORMATION[k]]
        if not off:
            return "Starting eleven (green) matches the 4-2-3-1 order: " + ", ".join(FORMATION)
        return "In the 4-2-3-1 order %s, %s" % (
            ", ".join(FORMATION),
            "; ".join("place %d is a %s playing %s" % x for x in off[:4]) + (" ..." if len(off) > 4 else ""))

    def pick_player(self):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        if pid == self.pid:
            return
        if not self.leave():
            self.tree.selection_set(str(self.pid))
            return
        self.pid = pid
        self.load_form()

    def load_form(self):
        pid, row = self.pid, self.w.slot[self.pid]
        pack = self.w.pack(row)
        self.vars["name"].set(self.w.name(pid))
        self.vars["shirt"].set(pack & E.SHIRT_MASK)
        self.vars["order"].set((pack & E.ORDER_MASK) >> E.ORDER_SHIFT)
        for n in E.FIELDS:
            v = self.w.get(pid, n)
            self.vars[n].set(v if n in dict(E.SKILLS) else E.show(n, v))
        self.shown = self.snapshot()

    def snapshot(self):
        return {k: str(v.get()) for k, v in self.vars.items()}

    def leave(self):
        """before switching away from a player: ask about unapplied changes"""
        if self.pid is None or self.snapshot() == self.shown:
            return True
        a = messagebox.askyesnocancel("Unapplied changes",
                                      "Apply the changes to %s first?" % self.w.name(self.pid))
        if a is None:
            return False
        return self.apply() if a else True

    # ---- actions
    def apply(self):
        if self.pid is None:
            return False
        errs, vals = [], {}
        for n in E.FIELDS:
            s = str(self.vars[n].get()).strip()
            try:
                vals[n] = E.parse(n, s)
            except ValueError as e:
                errs.append(str(e))
        name = self.vars["name"].get().strip()
        if not name:
            errs.append("the name is empty")
        elif len(name.encode("utf-8")) > E.P_NAME_LEN - 1:
            errs.append("the name is longer than %d bytes" % (E.P_NAME_LEN - 1))
        nums = {}
        for k, hi in (("shirt", 99), ("order", 63)):
            s = self.vars[k].get().strip()
            if not (s.isdigit() and int(s) <= hi):
                errs.append("%s must be 0-%d" % (k, hi))
            else:
                nums[k] = int(s)
        if "order" in nums:
            for order, _, p, _ in self.w.squad(self.club):
                if p != self.pid and order == nums["order"]:
                    errs.append("squad order %d is taken by %s -- use Up / Down to swap"
                                % (order, self.w.name(p)))
        if errs:
            messagebox.showerror("Not applied", "\n".join(errs))
            return False
        self.w.write(self.pid, vals, name)
        row = self.w.slot[self.pid]
        pack = self.w.pack(row)
        new = pack & ~(E.ORDER_MASK | E.SHIRT_MASK) | nums["order"] << E.ORDER_SHIFT | nums["shirt"]
        if new != pack:
            self.w.set_pack(row, new)
        self.fill_squad(keep=self.pid)
        self.load_form()
        self.note("applied - not saved yet")
        return True

    def move(self, step):
        if self.pid is None or not self.leave():
            return
        squad = self.w.squad(self.club)
        k = next(i for i, t in enumerate(squad) if t[2] == self.pid)
        j = k + step
        if not 0 <= j < len(squad):
            return
        (o1, _, _, r1), (o2, _, _, r2) = squad[k], squad[j]
        p1, p2 = self.w.pack(r1), self.w.pack(r2)
        self.w.set_pack(r1, p1 & ~E.ORDER_MASK | o2 << E.ORDER_SHIFT)
        self.w.set_pack(r2, p2 & ~E.ORDER_MASK | o1 << E.ORDER_SHIFT)
        self.fill_squad(keep=self.pid)
        self.load_form()
        self.note("moved - not saved yet")

    def new(self):
        if self.pid is None:
            messagebox.showinfo("New player", "Select the player the new one should start as a copy of.")
            return
        if not self.leave():
            return
        try:
            pid = self.w.new_player(self.club, self.pid, self.cap)
        except ValueError as e:
            messagebox.showerror("No new player", str(e))
            return
        self.pid = None
        self.fill_squad(keep=pid)
        self.pid = pid
        self.load_form()
        self.note("new player %d - change him, Apply, then Save" % pid)

    def save(self):
        if self.pid is not None and not self.leave():
            return
        self.w.save()
        self.note("saved to " + self.w.db)

    def note(self, s):
        self.tk.title(("* " if self.w.dirty else "") + "FL26 player editor - " + self.w.db)
        self.status.config(text=s)

    def quit(self):
        if self.pid is not None and not self.leave():
            return
        if self.w.dirty:
            a = messagebox.askyesnocancel("Unsaved changes", "Save the changes before closing?")
            if a is None:
                return
            if a:
                self.w.save()
        self.tk.destroy()


def main():
    a = sys.argv[1:]
    get = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    root = tk.Tk()
    world = get("--root") or filedialog.askdirectory(
        title="The world folder (the one that holds 'common')")
    if not world:
        return 1
    try:
        w = World(world)
    except SystemExit as e:
        messagebox.showerror("FL26 player editor", str(e))
        return 1
    App(root, w, int(get("--cap", str(E.DEFAULT_CAP))))
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
