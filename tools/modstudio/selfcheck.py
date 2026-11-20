r"""FL26ModStudio.exe --selfcheck <folder>     (python modstudio_main.py --selfcheck <folder>)

The window walks itself and writes down what a player would have seen (0.3.1, mato 11.11.: "da nam
se ne ponovi zadnji beta build s hrpom gresaka"). It is the real window of the real exe with the
real settings folder (%APPDATA%) and game folder, so it is run on the very file that ships:

  - every page is opened the way a click opens it; how long the window stood still for it
    (open_ms: the click until the page is painted) and the longest single stop while the page
    filled itself afterwards (stall_ms), with a picture of the page (<lang>_<page>.png);
  - every menu of the top bar is opened and pictured;
  - on each page the texts that do not fit: a label or a button narrower than its text
    ("clipped"), a wrapped label lower than its text ("cut"), a button outside the window
    ("outside");
  - every error a click raised (errors.log) and every Python error of the walk itself;
  - whether the window fits the screen it is on.

FL26_SELFCHECK_DO='[["activate", "_FL26MyWorld"], ["rename", "_FL26MyWorld", "_FL26Other"]]' does those
things first, each the way its button does it (My world's Activate and Rename), and writes how long
it took, how long the window stood still meanwhile, when the files were done and how long the
window went on saying it was working after that ("actions" in the report). They change the game
folder like the buttons do. A box that asks or tells is pictured and written down ("dialogs"): in
such an action it is answered Yes / OK, anywhere else it is closed and counts as a fault, so a walk
never waits for a person.

FL26_SELFCHECK_PAGES=Leagues,Build walks only those pages; FL26_SELFCHECK_PROFILE=1 also writes
profile_<page>_<round>.txt for every page that took more than 0.3 s to open (the times are then
longer than a player's: use it to find the cause, not to judge).

report.json in the folder says all of it; tools/uitour.py runs it for each language and makes the
table and the contact sheets. Nothing is saved: the walk ends the process without closing the
window, so settings.json and the world stay as they were.
"""
import json, os, sys, time, traceback

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import (QAbstractButton, QAbstractScrollArea, QApplication, QLabel, QMenu, QTabBar,
                               QToolButton, QWidget)

from . import anim

QUIET_S = 0.45          # a page is settled when the window was idle this long ...
SETTLE_CAP_S = 90       # ... or after this long at the latest (it is then reported as not settled)
START_CAP_S = 600       # the first start unpacks the game's tables: wait for it this long


def _plain(text):
    t = text or ""
    if "<" in t and ">" in t:                       # rich text: what is drawn, without the tags
        from PySide6.QtGui import QTextDocument
        d = QTextDocument()
        d.setHtml(t)
        t = d.toPlainText()
    return t.replace("&&", "\0").replace("&", "").replace("\0", "&")


def _in_scroll(w, top):
    p = w.parentWidget()
    while p is not None and p is not top:
        if isinstance(p, QAbstractScrollArea):
            return True
        p = p.parentWidget()
    return False


def misfits(top):
    """the visible texts of `top` that do not fit: [(kind, widget class, object name, text, need, have)]"""
    out = []
    edge = top.rect()
    for w in top.findChildren(QWidget):
        if not w.isVisible() or w.visibleRegion().isEmpty() or w.property("clip_ok"):
            continue
        cls, name = type(w).__name__, w.objectName()
        if isinstance(w, QLabel):
            text = _plain(w.text())
            if not text.strip() or (w.pixmap() is not None and not w.pixmap().isNull()):
                continue
            room = w.contentsRect()
            fm = w.fontMetrics()
            if w.wordWrap():
                need = w.heightForWidth(w.width())
                if need > w.height() + 3:
                    out.append(("cut", cls, name, text[:90], need, w.height()))
            elif "\n" not in text:
                # rich text draws in its own fonts: ask the label what it needs, not the font
                rich = "<" in w.text() and ">" in w.text()
                need = w.sizeHint().width() - (w.width() - room.width()) if rich else fm.horizontalAdvance(text)
                if need > room.width() + 2:
                    out.append(("clipped", cls, name, text[:90], need, room.width()))
        elif isinstance(w, QAbstractButton):
            text = _plain(w.text())
            if not text.strip():
                continue
            need = w.fontMetrics().horizontalAdvance(text)
            if need > w.width() + 1:
                out.append(("clipped", cls, name, text[:90], need, w.width()))
            if not _in_scroll(w, top):
                r = w.rect()
                tl = w.mapTo(top, r.topLeft())
                if tl.x() + r.width() > edge.width() + 1 or tl.y() + r.height() > edge.height() + 1 or tl.x() < -1:
                    out.append(("outside", cls, name, text[:90], tl.x() + r.width(), edge.width()))
        elif isinstance(w, QTabBar):
            for i in range(w.count()):
                text = _plain(w.tabText(i))
                r = w.tabRect(i)
                need = w.fontMetrics().horizontalAdvance(text)
                if text and need > r.width() + 1:
                    out.append(("clipped", cls, name, text[:90], need, r.width()))
    return out


class Walk:
    def __init__(self, app, w, out):
        if os.environ.get("FL26_SELFCHECK_PROFILE"):
            self._watch_threads(out)
        self.app, self.w, self.out = app, w, out
        os.makedirs(out, exist_ok=True)
        from modstudio import VERSION, app as A
        self.errors_log = os.path.join(A.APPDIR, "errors.log")
        self.lang = w.settings.get("lang", "en")
        self.rep = {"version": VERSION, "exe": sys.executable, "frozen": bool(getattr(sys, "frozen", False)),
                    "lang": self.lang, "appdata": A.APPDIR, "game": getattr(w.game, "folder", None),
                    "started": time.strftime("%Y-%m-%d %H:%M:%S"), "pages": [], "menus": [], "errors": [],
                    "done": False}
        t0 = os.environ.get("FL26_SELFCHECK_T0")          # the driver's clock when it started the exe
        if t0:
            self.rep["window_ms"] = int((time.time() - float(t0)) * 1000)
        self._err_at = os.path.getsize(self.errors_log) if os.path.exists(self.errors_log) else 0
        self._hooked = sys.excepthook
        sys.excepthook = self._hook

    def _hook(self, kind, err, tb):
        self.rep["errors"].append({"where": getattr(self, "at", "?"),
                                   "text": "".join(traceback.format_exception(kind, err, tb))[-2000:]})
        try:
            self._hooked(kind, err, tb)
        except Exception:
            pass

    def write(self):
        with open(os.path.join(self.out, "report.json"), "w", encoding="utf-8") as f:
            json.dump(self.rep, f, indent=1, ensure_ascii=False)

    def new_errors(self):
        try:
            size = os.path.getsize(self.errors_log)
        except OSError:
            return ""
        if size <= self._err_at:
            return ""
        with open(self.errors_log, "rb") as f:
            f.seek(self._err_at)
            text = f.read().decode("utf-8", "replace")
        self._err_at = size
        return text

    def settle(self, cap=SETTLE_CAP_S):
        """let the window work until it is idle; (seconds it took, longest single stop, settled?)"""
        t0 = time.perf_counter()
        worst, quiet_from = 0.0, time.perf_counter()
        while True:
            a = time.perf_counter()
            self.app.processEvents()
            took = time.perf_counter() - a
            worst = max(worst, took)
            now = time.perf_counter()
            # (a picture is taken of what stands still; the open world's small pictures are part of
            # opening it, as they are after Put in the game)
            warm = getattr(self.w, "_warming", None)
            if took > 0.03 or self.w._busy or anim.busy() or (warm is not None and warm.is_alive()):
                quiet_from = now
            if now - quiet_from >= QUIET_S:
                return now - t0 - QUIET_S, worst, True
            if now - t0 > cap:
                return now - t0, worst, False
            time.sleep(0.004)

    def beat(self):
        """the window's pulse: the longest time between two beats is how long it stood still"""
        now = time.perf_counter()
        self._gap = max(self._gap, now - self._beat_at)
        self._beat_at = now
        if self._stalls is not None and now - self._armed > 0.1:
            # stalls.txt: where every thread is when the window has not beaten for half a second
            import faulthandler
            self._armed = now
            faulthandler.dump_traceback_later(0.6, file=self._stalls)       # (arming again replaces the last)

    def answer_boxes(self):
        """a box that waits for an answer: its picture and words, then an answer"""
        from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox
        d = QApplication.activeModalWidget()
        if d is None or not d.isVisible():
            return
        now = time.perf_counter()
        if d is self._answered:
            if now - self._answered_at > 5:           # it did not take the answer: close it
                self._answered_at = now
                QTimer.singleShot(0, d.reject if isinstance(d, QDialog) else d.close)
            return
        self._answered, self._answered_at = d, now
        doing = bool(self._doing)
        boxes = self.rep.setdefault("dialogs", [])
        rec = {"at": self.at, "class": type(d).__name__, "title": d.windowTitle(), "in_action": doing}
        try:
            rec["shot"] = self.shot("dialog_%d" % len(boxes), d)
        except Exception:
            pass
        if isinstance(d, QMessageBox):
            rec["text"] = d.text()
            b = (d.button(QMessageBox.Yes) or d.button(QMessageBox.Ok) or d.defaultButton()) if doing else None
            rec["answer"] = _plain(b.text()) if b else "closed"
            QTimer.singleShot(0, b.click if b else d.reject)
        elif isinstance(d, QInputDialog):
            want = self._typed.pop(0) if doing and self._typed else None
            rec["text"] = d.labelText()
            if want is not None:
                d.setTextValue(want)
            rec["answer"] = "OK: %s" % want if want is not None else "closed"
            QTimer.singleShot(0, d.accept if want is not None else d.reject)
        else:
            rec["answer"] = "closed"
            QTimer.singleShot(0, d.reject if isinstance(d, QDialog) else d.close)
        boxes.append(rec)
        self._beat_at = time.perf_counter()           # the picture is not the window's stop

    def until(self, over, cap, files=None):
        """work until over() says so: (seconds, longest stop of the window, over?, seconds until files())"""
        t0 = time.perf_counter()
        self._gap, self._beat_at = 0.0, t0
        at_files, asked = None, 0.0
        while True:
            self.app.processEvents()
            now = time.perf_counter()
            if files is not None and at_files is None and now - asked > 0.5:
                asked = now
                try:
                    if files():
                        at_files = now - t0
                except Exception:
                    pass
                self._beat_at = time.perf_counter()   # the check is the walk's own work
            if over():
                self.beat()
                return now - t0, self._gap, True, at_files
            if now - t0 > cap:
                return now - t0, self._gap, False, at_files
            time.sleep(0.005)

    def act(self, what):
        """one thing done the way its button does it, and what the window did meanwhile"""
        from modstudio import worlds as WL
        w, mw = self.w, self.w.my_world
        kind, name = what[0], what[1]
        self.at = "%s %s" % (kind, name)
        d = {"do": list(what), "live_before": WL.live(w.game)}
        w.open_page("Leagues")
        self.settle(30)
        self._doing, self._typed = kind, []
        # the steps of the window's own work, timed from the click: [name, started, seconds]
        steps, undo = [], []
        def timed(obj, attr, t_click):
            real = getattr(obj, attr)
            def run(*a, **k):
                s = time.perf_counter()
                one = None
                if os.environ.get("FL26_SELFCHECK_PROFILE") == attr:      # this step alone
                    import cProfile
                    one = cProfile.Profile()
                    one.enable()
                try:
                    return real(*a, **k)
                finally:
                    if one is not None:
                        one.disable()
                        one.dump_stats(os.path.join(self.out, "raw_%d_%d.prof" % (os.getpid(), int(time.perf_counter() * 1000))))
                        import io, pstats
                        txt = io.StringIO()
                        pstats.Stats(one, stream=txt).sort_stats("cumulative").print_stats(60)
                        with open(os.path.join(self.out, "profile_step_%s_%d.txt" % (attr, len(steps))), "w",
                                  encoding="utf-8") as f:
                            f.write(txt.getvalue())
                    steps.append([attr if obj is w else "%s.%s" % (type(obj).__name__, attr),
                                  round(s - t_click, 2), round(time.perf_counter() - s, 2)])
            setattr(obj, attr, run)
            undo.append(lambda: delattr(obj, attr))
        prof = None
        if os.environ.get("FL26_SELFCHECK_PROFILE") == "1":   # the whole of it (every thread)
            import cProfile
            prof = cProfile.Profile()
            prof.enable()
        a = time.perf_counter()
        for obj, attr in ((w, "live_recipe"), (w, "open_live_world"), (mw, "refresh"), (w, "update_header"),
                          (w.pages.get("Install"), "refresh"), (w.pages.get("Restore"), "refresh"),
                          (w.pages.get("Build"), "refresh"), (w.pages.get("Trophies"), "queue_refresh")):
            if obj is not None and hasattr(obj, attr):
                timed(obj, attr, a)
        try:
            if kind == "activate":
                mw.put_in_game(name)
                click = time.perf_counter() - a
                d["started"] = getattr(mw, "_switching", None) == name
                took, worst, ok, at_files = self.until(
                    lambda: getattr(mw, "_switching", None) is None and not w._busy, 1800,
                    files=lambda: WL.live(w.game) == [name])
            elif kind == "rename":
                new = what[2]
                self._typed = [new]
                mw.rename(name)
                click = time.perf_counter() - a
                d["started"] = getattr(mw, "_renaming", None) == name
                took, worst, ok, at_files = self.until(
                    lambda: getattr(mw, "_renaming", None) is None and not w._busy, 1800,
                    files=lambda: os.path.isdir(os.path.join(w.game.livecpk_dir, new))
                    and not os.path.isdir(os.path.join(w.game.livecpk_dir, name)))
            else:
                raise ValueError("selfcheck does not know how to %s" % kind)
            tail, worst2, ok2 = self.settle(120)
        finally:
            self._doing = None
            for u in undo:
                u()
            d["steps"] = steps
            if prof is not None:
                prof.disable()
                prof.dump_stats(os.path.join(self.out, "raw_%d_%d.prof" % (os.getpid(), int(time.perf_counter() * 1000))))
                import io, pstats
                s = io.StringIO()
                pstats.Stats(prof, stream=s).sort_stats("cumulative").print_stats(60)
                with open(os.path.join(self.out, "profile_do_%s_%d.txt" % (kind, len(self.rep.get("actions") or []))),
                          "w", encoding="utf-8") as f:
                    f.write(s.getvalue())
        d.update({"click_ms": int(click * 1000), "total_s": round(took, 1), "stall_ms": int(worst * 1000),
                  "settle_stall_ms": int(worst2 * 1000), "over": bool(ok and ok2),
                  "files_s": None if at_files is None else round(at_files, 1),
                  "after_files_s": None if at_files is None else round(took - at_files, 1),
                  "live_after": WL.live(w.game), "shot": self.shot("after_%s_%d" % (kind, len(self.rep.get("actions") or [])))})
        err = self.new_errors()
        if err:
            self.rep["errors"].append({"where": self.at, "text": err[-2000:]})
        self.rep.setdefault("actions", []).append(d)
        self.write()

    def film(self):
        """FL26_SELFCHECK_FILM=1 (uitour --film): the animations as they look, in film_*.gif. They
        run three times slower while the pictures are taken, one every 60 ms, and the film shows a
        picture every 20 ms: their real speed. From the sources only (it needs Pillow)"""
        try:
            from PIL import Image
        except ImportError:
            return {"error": "no Pillow here"}
        from PySide6.QtCore import QEvent, QPointF, QRect
        from PySide6.QtGui import QEnterEvent, QImage, QMouseEvent
        w, slow, out = self.w, 3, {}
        names = ("PAGE_MS", "HOVER_MS", "DIALOG_MS", "NOTICE_MS", "CARD_MS", "CARD_STEP_MS",
                 "SLIDE_MS", "LEAVE_MS", "MENU_MS", "SCROLL_MS", "LINE_MS")
        was = {n: getattr(anim, n) for n in names}

        def roll(frames, rect, seconds):
            end = time.perf_counter() + seconds * slow
            while time.perf_counter() < end:
                a = time.perf_counter()
                self.app.processEvents()
                img = w.grab(rect).toImage().convertToFormat(QImage.Format_RGB888)
                frames.append(Image.frombuffer("RGB", (img.width(), img.height()), bytes(img.constBits()), "raw",
                                               "RGB", img.bytesPerLine()).copy())
                while time.perf_counter() - a < 0.06:
                    self.app.processEvents()
                    time.sleep(0.002)

        def save(name, frames):
            if not frames:
                return
            if frames[0].width > 1100:
                k = 960.0 / frames[0].width
                frames = [f.resize((960, int(f.height * k)), Image.LANCZOS) for f in frames]
            path = os.path.join(self.out, "film_%s.gif" % name)
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=20, loop=0)
            out[name] = [os.path.basename(path), len(frames)]

        def around(widget, dx, dy):
            return QRect(widget.mapTo(w, QPoint(0, 0)), widget.size()).adjusted(-dx, -dy, dx, dy).intersected(w.rect())

        def point(b, kind):
            p = QPointF(5, 5)
            g = QPointF(b.mapToGlobal(QPoint(5, 5)))
            if kind == "enter":
                QApplication.sendEvent(b, QEnterEvent(p, p, g))
                QApplication.sendEvent(b, QMouseEvent(QEvent.MouseMove, p, g, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
            else:
                QApplication.sendEvent(b, QEvent(QEvent.Leave))

        def scene(name, fn):
            try:
                frames = []
                fn(frames)
                save(name, frames)
            except Exception as e:
                out[name] = "error: %r" % (e,)
            anim.finish_all()
            self.settle(15)

        def pages(frames):
            first = w.settings.get("page")
            tour = [n for n in ("Leagues", "Settings", "Cups", "Modules", first) if n in w.pages]
            for n in tour:                            # each built once: the film is of the change alone
                w.open_page(n)
                self.settle(30)
            anim.finish_all()
            roll(frames, w.rect(), 0.15)
            for n in tour:
                w.open_page(n)
                roll(frames, w.rect(), 0.45)

        def tabs(frames):
            """the tabs of My world, there and back: what is under them slides"""
            tour = [n for n in ("Build", "Leagues", "Clubs", "Players", "Leagues", "Build") if n in w.pages]
            for n in tour:
                w.open_page(n)
                self.settle(30)
            anim.finish_all()
            roll(frames, w.rect(), 0.15)
            for n in tour[1:]:
                w.open_page(n)
                roll(frames, w.rect(), 0.5)

        def wheel(frames):
            """the mouse wheel over the open page: it glides"""
            from PySide6.QtCore import QPoint as P
            from PySide6.QtGui import QWheelEvent
            from PySide6.QtWidgets import QScrollArea
            if "Settings" in w.pages:
                w.open_page("Settings")
                self.settle(30)
            anim.finish_all()
            area = next((a for a in w.findChildren(QScrollArea) if a.isVisible() and a.height() > 200
                         and a.verticalScrollBar().maximum() > 100), None)
            if area is None:
                return
            v = area.viewport()

            def turn(notches):
                p = QPointF(40, 40)
                QApplication.sendEvent(v, QWheelEvent(p, QPointF(v.mapToGlobal(P(40, 40))), P(0, 0), P(0, -120 * notches),
                                                      Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
            roll(frames, w.rect(), 0.1)
            for n in (1, 1, -2):
                turn(n)
                roll(frames, w.rect(), 0.3)

        def buttons(frames):
            mw = w.my_world
            got = [c.go for c in getattr(mw, "cards", []) if c.go.isVisible() and c.go.isEnabled()]
            got += [b for b in (getattr(w, "play_btn", None),) if b is not None and b.isVisible() and b.isEnabled()]
            got += [b for b in w.findChildren(QAbstractButton) if b.isVisible() and b.isEnabled()
                    and b.objectName() in ("primary", "")][:2]
            for i, b in enumerate(got[:4]):
                one = []
                rect = around(b, 60, 30)
                roll(one, rect, 0.1)
                point(b, "enter")
                roll(one, rect, 0.4)
                point(b, "leave")
                roll(one, rect, 0.4)
                save("button%d" % (i + 1), one)

        def status(frames):
            bar, old = w.statusBar(), w.status_left.text()
            end = time.perf_counter() + 1.7           # (lines closer than 1.5 s do not slide)
            while time.perf_counter() < end:
                self.app.processEvents()
            roll(frames, around(bar, 0, 4), 0.1)
            w.status("%s: %s" % (w.windowTitle(), old))
            roll(frames, around(bar, 0, 4), 0.6)
            w.status(old)

        def cards(frames):
            mw = w.my_world
            if not mw.isVisible():
                return
            roll(frames, around(mw, 0, 0), 0.1)
            mw.shown()
            roll(frames, around(mw, 0, 0), 0.8)

        try:
            for n in names:
                setattr(anim, n, was[n] * slow)
            scene("pages", pages)
            scene("tabs", tabs)
            scene("wheel", wheel)
            scene("cards", cards)
            scene("buttons", buttons)
            scene("status", status)
        finally:
            for n in names:
                setattr(anim, n, was[n])
        out["on"] = bool(anim.on())
        return out

    def shot(self, name, widget=None):
        p = os.path.join(self.out, "%s_%s.png" % (self.lang, name))
        (widget or self.w).grab().save(p)
        return os.path.basename(p)

    @staticmethod
    def _watch_threads(out):
        """walks.txt: who lists folders, and from which thread (a profile of the window's thread
        does not say who took its turn away: a reader in the background holds Python's lock too)"""
        import atexit, collections, threading
        seen = collections.Counter()
        main = threading.main_thread()

        def counted(real, name):
            def call(*a, **k):
                fr = sys._getframe(1)
                who = []
                while fr is not None and len(who) < 4:
                    who.append("%s %s" % (os.path.basename(fr.f_code.co_filename), fr.f_code.co_name))
                    fr = fr.f_back
                seen[("window" if threading.current_thread() is main else "other") + "  " + name + "  " + " < ".join(who)] += 1
                if sum(seen.values()) % 2000 == 0:
                    save()
                return real(*a, **k)
            return call

        def save():
            try:
                with open(os.path.join(out, "walks.txt"), "w", encoding="utf-8") as f:
                    for k, v in seen.most_common(40):
                        f.write("%7d  %s" % (v, k) + chr(10))
            except OSError:
                pass
        os.walk, os.listdir, os.scandir = counted(os.walk, "walk"), counted(os.listdir, "listdir"), counted(os.scandir, "scandir")
        Walk._save_walks = staticmethod(save)

    def start(self):
        self._answered, self._answered_at, self._doing, self._typed = None, 0.0, None, []
        self._gap, self._beat_at = 0.0, time.perf_counter()
        self._stalls, self._armed = None, 0.0
        if os.environ.get("FL26_SELFCHECK_PROFILE"):
            self._stalls = open(os.path.join(self.out, "stalls.txt"), "w", encoding="utf-8")
        self._pulse = QTimer(interval=10, timeout=self.beat)                # beats inside a box's own loop too
        self._pulse.start()
        self._boxes = QTimer(interval=100, timeout=self.answer_boxes)
        self._boxes.start()
        try:
            self.run()
        except BaseException:
            self.rep["errors"].append({"where": "selfcheck", "text": traceback.format_exc()[-3000:]})
        self.write()
        getattr(self, "_save_walks", lambda: None)()
        if sys.stdout is not None:                    # (the exe has no console: None there, and the
            sys.stdout.flush()                        # walk's window then never left, 11.11.)
        if os.environ.get("FL26_SELFCHECK_END") == "close":      # the way a person leaves: File > Exit
            self._pulse.stop()
            self._boxes.stop()
            QTimer.singleShot(0, self.w.close)
            return
        try:
            # (os._exit unloads the DLLs with the worker threads still alive, and PySide then fell
            # over in its own unloading: a crash in Windows' log at the end of every walk)
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.TerminateProcess(ctypes.c_void_p(k32.GetCurrentProcess()), 0)
        except Exception:
            pass
        os._exit(0)                                   # no closeEvent: nothing is saved

    def run(self):
        w, rep = self.w, self.rep
        self.at = "start"
        # the first start unpacks the game's tables and opens the world in the game after them
        t0 = time.perf_counter()
        took, worst, ok = self.settle(START_CAP_S)
        rep["start"] = {"settle_ms": int(took * 1000), "stall_ms": int(worst * 1000), "settled": ok,
                        "tables": w.project.base is not None}
        rec = w.project.recipe or {}
        rep["world"] = {"name": rec.get("world"), "leagues": len(rec.get("leagues") or []),
                        "live": list(w.project.live_worlds() or [])}
        scr = w.screen().availableGeometry()
        fr = w.frameGeometry()
        rep["window"] = {"size": [w.width(), w.height()], "frame": [fr.width(), fr.height()],
                         "screen": [scr.width(), scr.height()],
                         "min_hint": [w.minimumSizeHint().width(), w.minimumSizeHint().height()],
                         "fits": fr.width() <= scr.width() + 16 and fr.height() <= scr.height() + 16}
        todo = json.loads(os.environ.get("FL26_SELFCHECK_DO") or "[]")
        for what in todo:
            self.act(what)
        if os.environ.get("FL26_SELFCHECK_FILM"):
            rep["film"] = self.film()
        if todo:
            rec = w.project.recipe or {}
            rep["world_walked"] = {"name": rec.get("world"), "leagues": len(rec.get("leagues") or []),
                                   "live": list(w.project.live_worlds() or [])}
        only = [n for n in (os.environ.get("FL26_SELFCHECK_PAGES") or "").split(",") if n]
        names = [n for n in w.pages if not only or n in only]
        for rnd in (1, 2):                            # the second round: every page already built once
            for name in names:
                self.at = name
                prof = None
                if os.environ.get("FL26_SELFCHECK_PROFILE"):      # where a slow page spends its time
                    import cProfile
                    prof = cProfile.Profile()
                    prof.enable()
                a = time.perf_counter()
                w.open_page(name)
                w.repaint()
                self.app.processEvents()
                open_s = time.perf_counter() - a
                if prof is not None:
                    prof.disable()
                    prof.dump_stats(os.path.join(self.out, "raw_%d_%d.prof" % (os.getpid(), int(time.perf_counter() * 1000))))
                    if open_s > 0.3:
                        import io, pstats
                        s = io.StringIO()
                        pstats.Stats(prof, stream=s).sort_stats("cumulative").print_stats(45)
                        with open(os.path.join(self.out, "profile_%s_%d.txt" % (name, rnd)), "w", encoding="utf-8") as f:
                            f.write(s.getvalue())
                took, worst, ok = self.settle()
                d = {"page": name, "round": rnd, "open_ms": int(open_s * 1000), "settle_ms": int(took * 1000),
                     "stall_ms": int(worst * 1000), "settled": ok}
                if rnd == 1:
                    d["shot"] = self.shot(name)
                    d["misfits"] = misfits(w)
                err = self.new_errors()
                if err:
                    rep["errors"].append({"where": name, "text": err[-2000:]})
                rep["pages"].append(d)
                self.write()
        # the menus of the top bar
        self.at = "menus"
        for b in w.findChildren(QToolButton):
            m = b.menu()
            if not isinstance(m, QMenu) or not b.isVisible():
                continue
            title = _plain(b.text()).replace("▾", "").strip()
            m.popup(b.mapToGlobal(QPoint(0, b.height())))
            self.settle(5)
            texts = [a.text() for a in m.actions() if not a.isSeparator()]
            scr = m.screen().availableGeometry()
            g = m.geometry()
            rep["menus"].append({"menu": title, "items": texts, "shot": self.shot("menu_%d" % len(rep["menus"]), m),
                                 "fits": g.right() <= scr.right() + 1 and g.bottom() <= scr.bottom() + 1})
            m.hide()
            self.settle(5)
        err = self.new_errors()
        if err:
            rep["errors"].append({"where": "menus", "text": err[-2000:]})
        rep["total_s"] = round(time.perf_counter() - t0, 1)
        rep["done"] = True


def begin(app, w, out):
    walk = Walk(app, w, out)
    QTimer.singleShot(800, walk.start)
    return walk
