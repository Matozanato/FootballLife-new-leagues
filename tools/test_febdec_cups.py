"""Regression tests for February-December domestic cups."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B


def recipe(**extra):
    league = {
        "name": "Uruguay Calendar Test",
        "country": "Uruguay",
        "clubs": 12,
        "legs": 2,
        "season": "calendar",
    }
    league.update(extra)
    return {
        "world": "_TestFebDecCups",
        "leagues": [league],
    }


def main(base):
    # 1. National cup is accepted.
    pl = B.plan(recipe(cup=True), base)
    p = pl["leagues"][0]
    assert p.get("calendar"), "top division should be calendar-year"
    assert p.get("own_cup"), "national cup was not planned"
    print("accepted: February-December + national cup")

    # 2. National cup + super cup are accepted.
    pl = B.plan(recipe(cup=True, supercup=True), base)
    p = pl["leagues"][0]
    assert p.get("own_cup", {}).get("super"), "super cup was not planned"
    print("accepted: February-December + national cup + super cup")

    # 2b. Build's summary dates it as dates_lines() does: the end of January (JAPAN_SUPER_CUP,
    #     day 30), not "follows BELGIUM_SUPER_CUP" (the August-May one's)
    text = [l for l in B.describe(pl).splitlines() if "super cup, the champion" in l]
    assert len(text) == 1 and B.CALENDAR_SUPER_DATE_LIKE in text[0] and "end of January" in text[0]         and B.SUPER_CUP_LIKE not in text[0], text
    aug = recipe(cup=True, supercup=True)
    aug["leagues"][0].pop("season")
    text = [l for l in B.describe(B.plan(aug, base)).splitlines() if "super cup, the champion" in l]
    assert len(text) == 1 and "follows %s" % B.SUPER_CUP_LIKE in text[0], text
    print("summary: February-December super cup at the end of January, August-May as before")

    # 3. League cup remains unsupported for February-December countries.
    try:
        B.plan(recipe(league_cup=True), base)
    except B.BuildError as e:
        assert "league cup" in str(e).lower(), str(e)
    else:
        raise AssertionError("February-December + league cup should be rejected")
    print("rejected: February-December + league cup")

    # dates_lines() works after Build has assigned cup regulation ids.
    cup = {
        "reg": 197,
        "like": "ENGLAND_D1_CUP",
        "super": "Test Super Cup",
        "super_reg": 198,
    }

    # August-May must keep the old behaviour: no calendar-year date override.
    normal = {"leagues": [{"own_cup": dict(cup)}]}
    normal_lines = B.dates_lines(normal, base)

    normal_cup_like = B.like_reg(base, "ENGLAND_D1_CUP")
    normal_super_like = B.like_reg(base, B.SUPER_CUP_LIKE)

    expected_normal = [
        "dates 197 like=%d" % normal_cup_like,
        "dates 198 like=%d" % normal_super_like,
    ]

    assert normal_lines == expected_normal, (
        "August-May dates changed:\n%r\nexpected:\n%r"
        % (normal_lines, expected_normal)
    )
    print("unchanged: August-May cup dates")

    # February-December gets the calendar prototypes with explicit dates.
    calendar = {
        "leagues": [{
            "calendar": True,
            "own_cup": dict(cup),
        }]
    }
    calendar_lines = B.dates_lines(calendar, base)

    cal_cup_like = B.like_reg(base, B.CALENDAR_CUP_DATE_LIKE)
    cal_super_like = B.like_reg(base, B.CALENDAR_SUPER_DATE_LIKE)

    assert cal_cup_like is not None, "calendar national-cup prototype not found"
    assert cal_super_like is not None, "calendar super-cup prototype not found"

    expected_calendar = [
        "dates 197 like=%d days=%s"
        % (
            cal_cup_like,
            ",".join(map(str, B.CALENDAR_CUP_DATE_DAYS)),
        ),
        "dates 198 like=%d days=%s"
        % (
            cal_super_like,
            ",".join(map(str, B.CALENDAR_SUPER_DATE_DAYS)),
        ),
    ]

    assert calendar_lines == expected_calendar, (
        "February-December dates wrong:\n%r\nexpected:\n%r"
        % (calendar_lines, expected_calendar)
    )

    print("calendar dates:", calendar_lines)
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
