r"""countries.py -- the countries our added leagues stand for, and which heading each one borrows.

Football Life ships eighteen real countries and three generic buckets: `PEU` (the rest of
Europe), `PLA` (the rest of Latin America) and `PAS` (the rest of Asia). Every country below
is deliberately one that the game does NOT ship, so nothing of ours ever wants a heading that
belongs to somebody else -- and a Croatian league filed under "rest of Europe" is exactly how
the shipped game files a country it has no picture for. That is why the list stops where it
does: no African or North American country is here, because there is no bucket for one.

The order is the order leagues are named in, so it is stable: changing it renames leagues in
a world that already exists. Add to the end.
"""

# (country, heading bucket)
COUNTRIES = [
    ("Croatia",                "PEU"),
    ("Slovenia",               "PEU"),
    ("Serbia",                 "PEU"),
    ("Bosnia and Herzegovina", "PEU"),
    ("Hungary",                "PEU"),
    ("Poland",                 "PEU"),
    ("Czechia",                "PEU"),
    ("Slovakia",               "PEU"),
    ("Austria",                "PEU"),
    ("Romania",                "PEU"),
    ("Bulgaria",               "PEU"),
    ("Greece",                 "PEU"),
    ("Ukraine",                "PEU"),
    ("Norway",                 "PEU"),
    ("Sweden",                 "PEU"),
    ("Ireland",                "PEU"),
    ("North Macedonia",        "PEU"),
    ("Montenegro",             "PEU"),
    ("Albania",                "PEU"),
    ("Finland",                "PEU"),
    ("Uruguay",                "PLA"),
    ("Paraguay",               "PLA"),
    ("Peru",                   "PLA"),
    ("Ecuador",                "PLA"),
    ("Bolivia",                "PLA"),
    ("Venezuela",              "PLA"),
    ("Mexico",                 "PLA"),
    ("South Korea",            "PAS"),
    ("Australia",              "PAS"),
    ("Qatar",                  "PAS"),
    ("United Arab Emirates",   "PAS"),
    ("Iran",                   "PAS"),
    ("Indonesia",              "PAS"),
]

# The shipped countries, by the region id they sit on. A league of ours that has been put
# inside one of these on purpose (deepen.py does that) is named after the country it is in,
# with its division number, rather than taking a country of its own.
SHIPPED = {
    2: "England", 3: "France", 4: "Spain", 5: "Italy", 6: "Portugal", 7: "Netherlands",
    8: "Belgium", 9: "Russia", 10: "Switzerland", 12: "Denmark", 15: "Scotland",
    16: "Brazil", 17: "Argentina", 18: "Chile", 19: "Colombia", 21: "China",
    27: "Turkey", 28: "Thailand",
}

ABBREV = {
    "Bosnia and Herzegovina": "BIH",
    "North Macedonia": "MKD",
    "United Arab Emirates": "UAE",
    "South Korea": "KOR",
    "Czechia": "CZE",
}


def short(name):
    """A three-letter tag for a country, for an emblem or a table."""
    if name in ABBREV:
        return ABBREV[name]
    letters = [c for c in name if c.isalpha()]
    return ("".join(letters[:3])).upper()
