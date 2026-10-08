"""everyone who helped, for Help > Credits (the README's "The people who made this better" says
the same at length). Add a name here and in the README together.

    (name, where, what) -- where: the place to find them (GitHub, Discord, Evo-Web ...)
"""

AUTHOR = ("Matozanato", "GitHub", "Mod Studio, the League Builder and the modules")

# the ones the README gives a section of their own
FEATURED = [
    ("vmardonesdev", "GitHub, Vicentico12 on Discord",
     "the tester this project owes the most: full seasons and rollovers, a regression suite, a "
     "testing plan, twenty-one of the first thirty-seven issues, and on the Discord the European "
     "places of the game's leagues"),
    ("Alikhaled_727", "Evo-Web, Mohamed_248 on GitHub",
     "the leagues outside Europe: Saudi Arabia, Egypt, Morocco, Asia and Africa, the CAF cups, "
     "the AFC Champions League Two and the league cup pre-round"),
    ("vector360", "Evo-Web, Discord",
     "the European format checked against UEFA's: the first-season order, the draw rules, the "
     "real 2026/27 list and the Carabao Cup"),
    ("jibibi", "Evo-Web, Discord moderator",
     "tests on a heavily modded game (a full French patch, the kit server, Sider in any folder), "
     "faces by nationality, the Players page on small screens, NewLife sorting, and the first "
     "answer to everyone's questions on the Discord"),
    ("Amir (AmirPjanic)", "GitHub, Discord moderator",
     "Mod Studio tested release by release: the ID columns, names with č ć š ž đ, leagues of 26 "
     "and the national team editor"),
    ("victormican", "GitHub",
     "South America from top to bottom: Kick Off, Select Team order, Colombia's calendar, the "
     "limit of leagues"),
    ("jyanj083-dotcom", "GitHub",
     "Peru and the Libertadores tested to the end: qualifying places, Apertura/Clausura, NewLife "
     "and the competition places"),
]

EVERYONE = [
    ("Stagnant09 (TrivialDice)", "GitHub, Evo-Web",
     "the flags in Select Team: the idea, the hook and the first working version"),
    ("pioup38", "GitHub", "the first report from another game build"),
    ("bobzera", "Evo-Web", "the default-kit problem of new clubs past id 65536"),
    ("spursfan07", "Evo-Web", "the first leagues built by hand in the database, and the walls they hit"),
    ("Gabyyy2008", "GitHub", "Apertura and Clausura in Argentina and Venezuela"),
    ("alexfe87", "GitHub", "the UEFA formats on their own: the Europe-only build"),
    ("ThanosMJ", "Evo-Web", "Greek leagues three divisions deep and the league order"),
    ("NudnyNick999", "Evo-Web", "the request that started the Kick Off order"),
    ("bnaanana", "Evo-Web", "a crash log that showed another module's errors next to ours"),
    ("dannydecai", "Evo-Web", "the commentary names past id 9999"),
    ("astyleUZ", "Evo-Web", "the first-time questions that made the guides clearer"),
    ("Zega_1991", "Reddit", "regens that do not come back as a retired player"),
    ("Alby17", "Evo-Web", "shirt number 10 that came out as 11"),
    ("daemonkf-a11y", "GitHub",
     "a renamed Europa League, a Romanian split, the Europe-only schedule and the play-off loser"),
    ("alby171994", "GitHub", "an exhibition-only world with no schedule, narrowed to one module"),
    ("Jabo9", "Evo-Web, Discord", "a new League One that took the FA Cup; league play-offs"),
    ("n1ne", "Discord", "the questions that show where the docs are not clear yet"),
    ("mushroomwehk", "GitHub",
     "a 12-club league that started on matchday 3, clubs of the game in new leagues, the Asian "
     "league's description and Edit mode past 30,001 players"),
    ("pepponeee98", "GitHub", "leagues that disappeared and a crash"),
    ("okarin-hub (Okarin)", "GitHub, Discord", "an Indonesian league and the start-up crashes"),
    ("iptory", "GitHub", "the Argentinian format: two zones and a play-off of eight"),
    ("JamesNotLike", "Discord",
     "LaLiga and Ligue 1 gone from Select Team, followed to the four mods that wrote into the "
     "same empty spot of the game as ours"),
    ("KamyFC", "Discord", "an Asian pyramid built step by step, and every question on the way"),
    ("San Marino", "Discord", "NewLife players copied instead of moved, and the Polish cup bracket"),
    ("lukewcfc", "Discord", "option files next to the new European cups"),
    ("mauro1977doni", "Discord", "a Europe-only world with an empty schedule"),
    ("N3RO", "Discord", "the Czech Chance Liga"),
    ("Hector", "Discord", "crests and logos for the NewLife Database"),
    ("Xxspedd", "Discord",
     "kits made from plain pictures (his png -> ftex conversion, 0.2.0), and the idea of matching a "
     "folder of crests to clubs by name"),
]

# the people who supported the project on Ko-fi (ko-fi.com/mata28), first first; the README's
# "Supporters" lists the same names
SUPPORTERS = ["Thunder105", "GutGut", "Scott Weir (LaraCroft)", "Pierro1912"]


def html(_=lambda s: s):
    """the Credits window's text"""
    def row(n, w, t):
        return "<p style='margin:0 0 7px 0'><b>%s</b> <span style='color:#8a94a6'>(%s)</span><br>%s</p>" % (n, w, t)
    out = ["<p>%s</p>" % _("Mod Studio is tested in the open. Every fix in it goes back to someone who "
                           "played, wrote down what happened and sent it. Thank you, all of you."),
           "<h3>%s</h3>" % _("Made by"), row(*AUTHOR),
           "<h3>%s</h3>" % _("The people who made it better")]
    out += [row(*p) for p in FEATURED]
    out.append("<h3>%s</h3>" % _("Everyone else who helped"))
    out += [row(*p) for p in EVERYONE]
    out.append("<h3>%s</h3>" % _("Supporters"))
    out.append("<p>%s</p>" % _("They supported the project on Ko-fi. Thank you!"))
    out.append("<p style='margin:0 0 7px 0'>%s</p>" % "<br>".join("<b>%s</b>" % n for n in SUPPORTERS))
    out.append("<p>%s</p>" % _("Send a report on GitHub or Discord and your name goes on this list too."))
    return "\n".join(out)
