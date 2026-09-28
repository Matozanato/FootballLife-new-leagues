"""sider.ini as a list of lines that can be read, switched, reordered and written back.

Nothing is normalised.  A line the program does not change is written back byte for byte:
comments, blank lines, the tabs in front of keys, the line ending the file already uses.

    ini = SiderIni.load(path)
    for e in ini.entries("cpk.root"):      # in file order, which is Sider's priority order
        print(e.enabled, e.value)
    ini.set_enabled(e, False)              # "; " in front
    ini.move(e, -1)                        # one place up among the cpk.root lines
    ini.save()                             # keeps a timestamped copy first (backups.py)

A switched-off entry is a cpk.root / lua.module line with a comment mark in front of it:
";", "#", ";OFF-ctl", "# off for ... -- " and so on.  The text before the key is kept, so
switching it back on restores the line exactly as it was before it was switched off.
"""
import os, re

LIST_KEYS = ("cpk.root", "lua.module")
# key = "value"  [; comment]      or  key = value  [; comment]
_ENTRY = re.compile(r'^(?P<pre>.*?)(?P<key>cpk\.root|lua\.module)\s*=\s*'
                    r'(?:"(?P<q>[^"]*)"|(?P<bare>[^;#\s]+))(?P<post>.*)$')
_KEY = re.compile(r'^(?P<ws>\s*)(?P<key>[A-Za-z0-9_.\-]+)\s*=\s*(?P<val>.*?)\s*$')
_OFF = re.compile(r'^\s*[;#]')


class Entry:
    """one cpk.root or lua.module line"""
    __slots__ = ("index", "key", "value", "enabled", "pre", "post", "quoted")

    def __init__(self, index, key, value, enabled, pre, post, quoted):
        self.index, self.key, self.value = index, key, value
        self.enabled, self.pre, self.post, self.quoted = enabled, pre, post, quoted

    @property
    def note(self):
        """the comment after the value, if any (";  off 25.09. ..." -> "off 25.09. ...")"""
        return self.post.strip().lstrip(";#").strip()

    def render(self):
        v = '"%s"' % self.value if self.quoted else self.value
        return "%s%s = %s%s" % (self.pre, self.key, v, self.post)

    def __repr__(self):
        return "<%s%s %s>" % ("" if self.enabled else "off ", self.key, self.value)


def parse_entry(i, line):
    m = _ENTRY.match(line)
    if not m:
        return None
    pre = m.group("pre")
    if pre.strip() and not _OFF.match(pre):
        return None                          # something else with the words in it
    enabled = not pre.strip()
    val = m.group("q") if m.group("q") is not None else m.group("bare")
    return Entry(i, m.group("key"), val, enabled, pre, m.group("post"), m.group("q") is not None)


class SiderIni:
    def __init__(self, lines, path=None, newline="\r\n", encoding="utf-8"):
        self.lines, self.path, self.newline, self.encoding = lines, path, newline, encoding

    # ---- reading ------------------------------------------------------------------------
    @classmethod
    def load(cls, path):
        raw = open(path, "rb").read()
        enc = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            enc, text = "cp1252", raw.decode("cp1252")
        nl = "\r\n" if b"\r\n" in raw else "\n"
        lines = text.replace("\r\n", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        return cls(lines, path, nl, enc)

    def text(self):
        return self.newline.join(self.lines) + self.newline

    def entries(self, key=None):
        out = []
        for i, line in enumerate(self.lines):
            e = parse_entry(i, line)
            if e and (key is None or e.key == key):
                out.append(e)
        return out

    def find(self, key, value):
        """every entry with this value, on or off (the same root can be listed twice)"""
        v = norm(value)
        return [e for e in self.entries(key) if norm(e.value) == v]

    def settings(self):
        """plain key = value settings (not cpk.root / lua.module), last one wins like Sider"""
        out = {}
        for line in self.lines:
            if _OFF.match(line) or parse_entry(0, line):
                continue
            m = _KEY.match(line)
            if m:
                v = m.group("val").split(";")[0].strip()
                out[m.group("key")] = v.strip('"')
        return out

    # ---- changing ----------------------------------------------------------------------
    def _put(self, e):
        self.lines[e.index] = e.render()

    def set_enabled(self, e, on):
        e = self.entries()[self._pos(e)] if not isinstance(e, Entry) else e
        if on == e.enabled:
            return
        if on:
            e.pre = re.match(r"\s*", e.pre).group(0)
        else:
            e.pre = "; " + e.pre
        e.enabled = on
        self._put(e)

    def _pos(self, e):
        return [x.index for x in self.entries()].index(e.index)

    def move(self, e, delta):
        """move an entry up (delta < 0) or down among the lines with the same key.
        The line swaps places with its neighbour of the same key, so the comments and the
        other lines around them stay where they were."""
        same = self.entries(e.key)
        k = [x.index for x in same].index(e.index)
        j = max(0, min(len(same) - 1, k + delta))
        if j == k:
            return e
        step = 1 if j > k else -1
        cur = e.index
        for t in range(k + step, j + step, step):
            other = same[t].index
            self.lines[cur], self.lines[other] = self.lines[other], self.lines[cur]
            cur = other
        return parse_entry(cur, self.lines[cur])

    def reorder(self, key, values):
        """put the entries of `key` into the order of `values` (normalised paths / names),
        using the same line slots, so nothing around them moves.  Entries not named keep
        their relative order after the named ones."""
        same = self.entries(key)
        slots = [e.index for e in same]
        rank = {norm(v): n for n, v in enumerate(values)}
        ordered = sorted(same, key=lambda e: (rank.get(norm(e.value), len(rank)), e.index))
        texts = [self.lines[e.index] for e in ordered]
        for s, t in zip(slots, texts):
            self.lines[s] = t

    def add(self, key, value, enabled=True, where=None, note=None):
        """add an entry.  where: None = after the last line with this key (or at the end of
        [sider] if there is none), "first" = before the first one, an Entry = right after it."""
        same = self.entries(key)
        line = '%s%s = "%s"%s' % ("" if enabled else "; ", key, value,
                                  ("   ; " + note) if note else "")
        if where == "first" and same:
            at = same[0].index
        elif isinstance(where, Entry):
            at = where.index + 1
        elif same:
            at = same[-1].index + 1
        else:
            at = self._section_end("sider")
        self.lines.insert(at, line)
        return parse_entry(at, line)

    def remove(self, e):
        del self.lines[e.index]

    def set_setting(self, key, value):
        """change `key = value` in place (keeping its indent), or add it to [sider]"""
        for i, line in enumerate(self.lines):
            if _OFF.match(line):
                continue
            m = _KEY.match(line)
            if m and m.group("key") == key:
                self.lines[i] = "%s%s = %s" % (m.group("ws"), key, value)
                return
        self.lines.insert(self._section_end("sider"), "%s = %s" % (key, value))

    def _section_end(self, name):
        start, end = None, len(self.lines)
        for i, line in enumerate(self.lines):
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                if start is not None:
                    end = i
                    break
                if s[1:-1].strip().lower() == name:
                    start = i
        if start is None:
            self.lines.insert(0, "[%s]" % name)
            return 1
        while end > start + 1 and not self.lines[end - 1].strip():
            end -= 1
        return end

    # ---- writing -----------------------------------------------------------------------
    def save(self, path=None, backup=True, reason=""):
        path = path or self.path
        if backup and os.path.exists(path):
            from . import backups
            backups.snapshot(path, reason)
        data = self.text().encode(self.encoding.replace("-sig", ""), "replace")
        if self.encoding == "utf-8-sig":
            data = b"\xef\xbb\xbf" + data
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)


def norm(v):
    """compare roots / modules the way a person would: case, slashes and a leading .\\ ignored"""
    v = v.strip().strip('"').replace("/", "\\").rstrip("\\").lower()
    while v.startswith(".\\"):
        v = v[2:]
    return v


def root_path(sider_dir, value):
    """where a cpk.root value points on disk (relative values are relative to sider.exe)"""
    v = value.replace("/", "\\")
    return os.path.normpath(v if os.path.isabs(v) else os.path.join(sider_dir, v))
