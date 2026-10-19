"""python tools/test_crestmatch.py -- the crest name matcher, plain asserts."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from crestmatch import match, words, score, file_id, file_country, folder_country, key, TICK  # noqa: E402

N = 0


def check(got, want, what):
    global N
    N += 1
    assert got == want, "%s: got %r, wanted %r" % (what, got, want)


# 1. an exact name, extension and all
check(match(["Real Madrid.png"], [("Real Madrid", 7)]), [("Real Madrid.png", 7, 1.0)], "exact")

# 2. accents are folded on both sides
check(match(["Atletico Nacional.png"], [("Atlético Nacional", 3)]),
      [("Atletico Nacional.png", 3, 1.0)], "accents in the club name")
check(match(["Atlético Nacional.png"], [("Atletico Nacional", 3)]),
      [("Atlético Nacional.png", 3, 1.0)], "accents in the file name")

# 3. filler words on both sides
check(match(["cd_universidad_cesar_vallejo.png"], [("CD Universidad Cesar Vallejo", 11)]),
      [("cd_universidad_cesar_vallejo.png", 11, 1.0)], "filler words")
check(words("Club Atletico Deportivo La Coruna"), ["coruna"], "the filler list")

# 4. the crest pack's size suffixes come off
check(match(["alianza_lima_r_l.png"], [("Alianza Lima", 5)]),
      [("alianza_lima_r_l.png", 5, 1.0)], "_r_l")
check(match(["alianza_lima_r.png"], [("Alianza Lima", 5)]),
      [("alianza_lima_r.png", 5, 1.0)], "_r")
check(match(["alianza_lima_r_ll.png"], [("Alianza Lima", 5)]),
      [("alianza_lima_r_ll.png", 5, 1.0)], "_r_ll")

# 5. two clubs with similar names: the closer one wins, and it takes the file
got = match(["Sporting Cristal.png"], [("Sporting", 1), ("Sporting Cristal", 2)])
check(got, [("Sporting Cristal.png", 2, 1.0)], "the nearer of two similar clubs")

# 6. one club contains the other: 0.5, under the tick (B139), and the exact club wins 1.0
check(match(["Real Madrid.png"], [("Real Madrid Castilla", 9)]),
      [("Real Madrid.png", 9, 0.5)], "containment")
check(match(["Real Madrid.png"], [("Real Madrid Castilla", 9), ("Real Madrid", 8)]),
      [("Real Madrid.png", 8, 1.0)], "containment loses to the exact club")

# 7. nothing near enough is None, never a wrong guess
check(match(["Barcelona.png"], [("Bayern Munchen", 4)]), [("Barcelona.png", None, 0.0)], "no match")
check(match(["barcelona.png"], [("Bayern", 4)]), [("barcelona.png", None, 0.0)], "below 0.4")

# 8. a club is used once: the better of two files gets it, the other falls through
got = match(["Deportivo Cali.png", "Deportivo Cali 2.png"], [("Deportivo Cali", 6)])
assert got[0][1] == 6 and got[1][1] is None, "one club, one file: %r" % (got,)
N += 1

# 9. a file is used once: two clubs, two files, each file to its own club
got = match(["Alianza Lima.png", "Universitario.png"],
            [("Universitario de Deportes", 12), ("Alianza Lima", 13)])
check(sorted((f, i) for f, i, _s in got),
      [("Alianza Lima.png", 13), ("Universitario.png", 12)], "two files, two clubs")
check([f for f, _i, _s in got], ["Alianza Lima.png", "Universitario.png"], "output order")

# 10. numbers count as words
check(match(["1_fc_kaiserslautern.png"], [("1. FC Kaiserslautern", 2)]),
      [("1_fc_kaiserslautern.png", 2, 1.0)], "digits")

# 11. an empty side changes nothing
check(match([], [("Real Madrid", 7)]), [], "no files")
check(match(["Real Madrid.png"], []), [("Real Madrid.png", None, 0.0)], "no clubs")
check(match([], []), [], "nothing at all")

# 12. the score function on its own, including the 4-letter floor for containment
check(score(["real", "madrid"], ["real"]), 0.5, "containment score")
check(score(words("fc"), words("fc")), 0.0, "filler words leave nothing to score")
check(score(["abc"], ["abcdef"]), 0.0, "containment needs 4 letters")
check(score(words("Mali"), words("poland_bruk-bet-termalica-nieciecza.png", True)), 0.0,
      "containment starts and ends with a word: no Mali in Termalica")
check(score(words("Port FC"), words("Sporting Cristal.png", True)), 0.0, "no Port in Sporting")
check(score(words("Manchester United"), words("manchesterunited.png", True)), 1.0,
      "a name run together is the same name")

# 13. a file named by its team id
check(file_id("12345.png"), 12345, "id file")
check(file_id("e_2215_r.png"), 2215, "crest pack flag name")
check(file_id("e_2215_r_l.png"), 2215, "crest pack flag name, large")
check(file_id("Real Madrid.png"), None, "a name is no id")

# 14. B139 (David's Africa crests against NewLife's 12,936 clubs): a name only inside the
# other is a suggestion, never a tick
def one(f, clubs, where=None, countries=None):
    return match([f], clubs, where, countries)[0]


for f in ("chippa-united.webp", "doma-united.webp", "kayanza-united.webp"):
    got = one(f, [("United Sport FC", 1)])
    check((got[1], got[2] < TICK), (1, True), "%s is no tick for United Sport FC" % f)
got = one("rangers-kinshasa.webp", [("Rangers", 2)])
check((got[1], got[2] < TICK), (2, True), "rangers-kinshasa is no tick for Rangers")
got = one("ts-galaxy.webp", [("LA Galaxy", 3)])
check((got[1], got[2] < TICK), (3, True), "ts-galaxy is no tick for LA Galaxy")
got = one("vitesse.webp", [("Vitesse Arnhem", 4)])
check((got[1], got[2] < TICK), (4, True), "vitesse is no tick for Vitesse Arnhem")
check(one("Vitesse Arnhem.webp", [("Vitesse Arnhem", 4)]), ("Vitesse Arnhem.webp", 4, 1.0),
      "the exact name still ticks")
check(one("Bayern Munchen.png", [("FC Bayern Munchen II", 5)])[2], 0.5, "all the words of one in the other")

# 15. the same name written another way is still the same name
check(words("Abia Warriors F.C."), ["abia", "warriors"], "F.C. is fc")
check(words("Pyramids Football Club"), ["pyramids"], "Football Club")
check(words("Sporting Club de Moknine"), ["moknine"], "Sporting Club")
check(words("Sporting Lagos F.C."), ["sporting", "lagos"], "Sporting alone stays")
check(words("Dreams FC (GHA)"), ["dreams"], "NewLife's country tag")
check(words("poland_cracovia_1500x1500.football-logos.cc.png", True), ["poland", "cracovia"],
      "football-logos.cc's size and site tag")
check(one("al-ahly.webp", [("Al-Ahly Sporting Club", 6)]), ("al-ahly.webp", 6, 1.0), "Sporting Club gone")

# 16. countries: the file's own country first, another country never ticked
CTY = {key(n): n for n in ("Poland", "Romania", "South Africa", "Zambia", "Kenya", "Netherlands",
                           "Burkina Faso", "Côte D'ivoire")}
CTY[key("Ivory Coast")] = "Côte D'ivoire"
check(file_country("poland_cracovia_1500x1500.football-logos.cc.png", CTY),
      ("Poland", "cracovia_1500x1500.football-logos.cc.png"), "the country a file name starts with")
check(file_country("real_madrid.png", CTY), (None, "real_madrid.png"), "no country, no prefix")
check(file_country("poland_.png", CTY), (None, "poland_.png"), "a country and nothing else")
check(one("poland_cracovia_1500x1500.football-logos.cc.png", [("Cracovia", 7, "Poland")], None, CTY),
      ("poland_cracovia_1500x1500.football-logos.cc.png", 7, 1.0), "the prefix is the club's country")
got = one("poland_cracovia_1500x1500.football-logos.cc.png", [("Cracovia", 7, "Romania")], None, CTY)
check((got[1], got[2] < TICK), (7, True), "a club of another country is no tick")
got = one("FC Leopards.webp", [("AFC Leopards SC", 8, "Kenya")], "Zambia")
check((got[1], got[2] < TICK), (8, True), "Zambia's folder is no tick for Kenya's club")
check(one("san-pedro.webp", [("Deportivo San Pedro", 9, "Guatemala"), ("Football Club San Pédro", 10, "Côte D'ivoire")],
          "Côte D'ivoire"), ("san-pedro.webp", 10, 1.0), "the same country wins an equal score")
check(one("vitesse.webp", [("Vitesse", 11, "Netherlands"), ("Vitesse Bobo", 12, "Burkina Faso")], "Burkina Faso"),
      ("vitesse.webp", 12, 0.65), "the same country wins a better score")
check(one("vitesse.webp", [("Vitesse", 11, "Netherlands"), ("Vitesse Bobo", 12, None)], "Burkina Faso"),
      ("vitesse.webp", 12, 0.5), "a club of no known country before one of another")
check(one("Vitesse.png", [("Vitesse", 11, "Netherlands")]), ("Vitesse.png", 11, 1.0),
      "no country for the file: as before")
check(one("Vitesse.png", [("Vitesse", 11, None)], "Burkina Faso"), ("Vitesse.png", 11, 1.0),
      "no country for the club: as before")
check(one("Kaizer Chiefs.png", [("Kaizer Chiefs", 13, "south africa")], "South Africa"),
      ("Kaizer Chiefs.png", 13, 1.0), "countries compared by their letters")

# 17. one name inside the other ticks only for the one club of the file's own country it fits
check(one("mostaganem.webp", [("ES Mostaganem", 14, "Algeria")], "Algeria"),
      ("mostaganem.webp", 14, 0.65), "the only club of its country: ticked")
check(one("mostaganem.webp", [("ES Mostaganem", 14, "Algeria"), ("Mostaganem City", 15, "France")], "Algeria"),
      ("mostaganem.webp", 14, 0.65), "a club of another country does not count")
got = one("mostaganem.webp", [("ES Mostaganem", 14, "Algeria"), ("WA Mostaganem", 15, "Algeria")], "Algeria")
check((got[1], got[2]), (14, 0.5), "two clubs of its country: none ticked")
check(one("mostaganem.webp", [("ES Mostaganem", 14, "Algeria")]), ("mostaganem.webp", 14, 0.5),
      "no country for the file: no tick")
check(one("mostaganem.webp", [("ES Mostaganem", 14, None)], "Algeria"), ("mostaganem.webp", 14, 0.5),
      "no country for the club: no tick")
check(one("mostaganem.webp", [("ES Mostaganem", 14, "Tunisia")], "Algeria"), ("mostaganem.webp", 14, 0.5),
      "a club of another country: no tick")
check(one("chippa-united.webp", [("United Sport FC", 1, "United Arab Emirates")], "South Africa")[2], 0.5,
      "United Sport FC is no tick for South Africa's chippa-united")
got = match(["mostaganem.webp", "es-mostaganem.webp"], [("ES Mostaganem", 14, "Algeria")], "Algeria")
check(got, [("mostaganem.webp", None, 0.0), ("es-mostaganem.webp", 14, 1.0)], "the exact name wins the club")

# 18. the country of a folder: a country's name, the innermost first, then a league's
LEAGUES = {key("Betway Premiership"): "South Africa", key("Premier League"): None}
check(folder_country(r"D:\crests\Africa\Algeria\ligue-1-mobilis", {key("Algeria"): "Algeria"}), "Algeria",
      "the folder above the league's")
check(folder_country("C:/x/Ivory Coast/ligue-1-lonaci", CTY), "Côte D'ivoire", "an everyday name")
check(folder_country("C:/x/South Africa/Zambia", CTY), "Zambia", "the innermost country")
check(folder_country("C:/x/betway-premiership", CTY, LEAGUES), "South Africa", "a league's folder")
check(folder_country("C:/Kenya/a/b/c", CTY, LEAGUES), None, "only the last three names")
check(folder_country("C:/x/premier-league", CTY, LEAGUES), None, "a league name two countries share")
check(folder_country("", CTY), None, "no folder")

print("all %d checks passed" % N)
