"""the map files of Sider's content servers: comma lists with # comments.

    174,   009, Lotto Park,   Belgium\\Stade Constant Vanden Stock      # RSC Anderlecht
    100, "Premier League\\Manchester United"
    1;48;18;23;11;36;22;25;12;3;2;

A MapFile keeps every line it does not understand (comments, blank lines, headers) exactly as
it was, and writes the lines it does understand back in the file's own style: fields joined by
", " (or ";" for the weather .csv files), quotes kept where the file had them, the trailing
comment kept.  A line switched off with a leading "#" (badge-server's way) is read as an
entry that is off.
"""
import codecs, os, re

DATA = re.compile(r"^\s*(#\s*)?(-?\d+)\s*[,;]")


class Row:
    def __init__(self, fields, comment="", enabled=True, quoted=()):
        self.fields = list(fields)
        self.comment = comment
        self.enabled = enabled
        self.quoted = set(quoted)
        self.orig = None                 # the line as read; written back as it was until changed

    def copy(self):
        return Row(self.fields, self.comment, self.enabled, self.quoted)

    def touch(self):
        self.orig = None


class MapFile:
    def __init__(self, path, width=None, sep=",", quote=None, disabled_rows=True):
        """width: the number of fields every row has (padded with empty ones, as ball-server's
        "6 commas are mandatory" needs); quote: indices of fields written in quotes"""
        self.path, self.width, self.sep = path, width, sep
        self.quote = set(quote or ())
        self.disabled_rows = disabled_rows
        self.items = []                    # str (kept line) or Row
        self.bom, self.newline, self.encoding = False, "\n", "utf-8"
        if path and os.path.exists(path):
            self.load()

    def load(self):
        raw = open(self.path, "rb").read()
        self.bom = raw.startswith(codecs.BOM_UTF8)
        if self.bom:
            raw = raw[3:]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text, self.encoding = raw.decode("cp1252", "replace"), "cp1252"
        self.newline = "\r\n" if "\r\n" in text else "\n"
        self.items = []
        for line in text.splitlines():
            r = self.parse(line)
            self.items.append(r if r is not None else line)

    def parse(self, line):
        m = DATA.match(line)
        if not m:
            return None
        off = bool(m.group(1))
        if off and not self.disabled_rows:
            return None
        body = line.lstrip()
        if off:
            body = body.lstrip("#").lstrip()
        comment = ""
        # a comment starts at a # outside quotes; for the weather csv there are none
        q, cut = False, None
        for i, ch in enumerate(body):
            if ch == '"':
                q = not q
            elif ch == "#" and not q:
                cut = i
                break
        if cut is not None:
            comment = body[cut + 1:].strip()
            body = body[:cut]
        parts = body.rstrip().split(self.sep)
        if self.sep == ";" and parts and parts[-1].strip() == "":
            parts = parts[:-1]                         # the weather files end every row with ;
        fields, quoted = [], set()
        for i, p in enumerate(parts):
            p = p.strip()
            if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
                p = p[1:-1]
                quoted.add(i)
            fields.append(p)
        r = Row(fields, comment, not off, quoted)
        r.orig = line
        return r

    # ---- access ----
    def rows(self):
        return [x for x in self.items if isinstance(x, Row)]

    def add(self, row, after=None):
        if after is not None and after in self.items:
            self.items.insert(self.items.index(after) + 1, row)
        else:
            self.items.append(row)
        return row

    def remove(self, row):
        self.items.remove(row)

    def render_row(self, r):
        if r.orig is not None:
            return r.orig
        f = list(r.fields)
        if self.width:
            f = (f + [""] * self.width)[:max(self.width, len(f))]
        out = []
        for i, v in enumerate(f):
            if i in r.quoted or i in self.quote:
                v = '"%s"' % v
            out.append(v)
        if self.sep == ";":
            line = ";".join(out) + ";"
        else:
            line = ", ".join(out)
        if r.comment:
            line += "   # " + r.comment
        return line if r.enabled else "#" + line

    def text(self):
        return self.newline.join(x if isinstance(x, str) else self.render_row(x) for x in self.items) + self.newline

    def save(self, reason="", sider_dir=None):
        from .backups import snapshot
        if os.path.exists(self.path):
            snapshot(self.path, reason or "map edited", sider_dir)
        data = self.text().encode(self.encoding, "replace")
        if self.bom:
            data = codecs.BOM_UTF8 + data
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(self.path + ".tmp", self.path)


class IniFile:
    """key = value settings (config.ini of a server), kept line by line"""
    LINE = re.compile(r"^(\s*)([A-Za-z0-9_.\-]+)(\s*=\s*)(.*?)(\s*(?:[;#].*)?)$")

    def __init__(self, path):
        self.path = path
        self.lines, self.newline, self.bom = [], "\n", False
        if os.path.exists(path):
            raw = open(path, "rb").read()
            self.bom = raw.startswith(codecs.BOM_UTF8)
            text = raw[3:].decode("utf-8", "replace") if self.bom else raw.decode("utf-8", "replace")
            self.newline = "\r\n" if "\r\n" in text else "\n"
            self.lines = text.splitlines()

    def items(self):
        out = []
        for i, l in enumerate(self.lines):
            s = l.strip()
            if not s or s[0] in ";#[" or s.startswith("--"):
                continue
            m = self.LINE.match(l)
            if m:
                out.append((m.group(2), m.group(4), i))
        return out

    def set(self, key, value):
        for k, v, i in self.items():
            if k == key:
                m = self.LINE.match(self.lines[i])
                self.lines[i] = m.group(1) + k + m.group(3) + value + m.group(5)
                return
        self.lines.append("%s = %s" % (key, value))

    def save(self, sider_dir=None):
        from .backups import snapshot
        if os.path.exists(self.path):
            snapshot(self.path, "settings changed", sider_dir)
        data = (self.newline.join(self.lines) + self.newline).encode("utf-8")
        with open(self.path + ".tmp", "wb") as f:
            f.write((codecs.BOM_UTF8 if self.bom else b"") + data)
        os.replace(self.path + ".tmp", self.path)
