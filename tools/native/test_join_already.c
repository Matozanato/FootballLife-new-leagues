/* B488 (16.11.2026): which of our competitions register_all takes as "already in a season" --
   fl26join's join_why, the part that touches no game memory.

     zig cc -O2 -fno-sanitize=undefined test_join_already.c -o test_join_already.exe && test_join_already.exe

   (tools/test_join_already.py builds and runs it.) Exit code 1 on any failure.

   The cases are the ones the comments of join_pre and join_why name:
     - a new career, no load: the July list of its creation has set the memory, so on 1 August no
       January-December league goes in and the split parents the builder let in stay out (door);
     - the same career saved before 1 August and loaded (the tester's): the memory is unknown, so a
       January-December league is held out by the date (July to December), a split parent by the
       season the save holds; one never entered still goes in;
     - a January-December league on its own registration day after New Year (February) goes in,
       memory or not, and so does one whose rounds are last season's (B253);
     - a league flagged by its parent and never entered (GitHub #19) goes in;
     - not flagged: in, as before (the 2 of a new career);
     - an unread date never holds anything out (the old answer). */
#define FL26_JOIN_TEST
#include "fl26join.c"
#include <stdio.h>

static int fails = 0, saved_asked = 0;
static void expect(int ok, const char* what)
{
  printf("  %s  %s\n", ok ? "ok  " : "FAIL", what);
  if (!ok) fails++;
}

/* the save's answer: ids 500..599 entered into a running season, the rest not */
static int saved_stub(uint16_t id) { saved_asked++; return id >= 500 && id < 600; }

static join_facts_t facts(int flagged, int cal, int rounds, int table, int door, int mid, int month)
{
  join_facts_t f = { flagged, cal, rounds, table, door, mid, month };
  return f;
}

int main(void)
{
  join_facts_t f;
  printf("new career, no load (memory set by the July list of its creation), 1 August:\n");
  f = facts(1, 1, 0, 0, 0, 1, 8);
  expect(join_why(&f, 300, saved_stub) == JOIN_MIDSEASON, "January-December league, no rounds: held out (mid-season)");
  f = facts(1, 0, 0, 0, 1, 1, 8);
  expect(join_why(&f, 510, saved_stub) == JOIN_DOOR, "split parent the builder let in: held out (door)");
  f = facts(1, 0, 1, 0, 0, 1, 8);
  expect(join_why(&f, 200, saved_stub) == JOIN_ROUNDS, "August-May league with rounds: held out (rounds)");
  f = facts(0, 0, 0, 0, 0, 1, 8);
  expect(join_why(&f, 200, saved_stub) == JOIN_IN, "not flagged: appended, as before");

  printf("saved before 1 August, loaded (memory unknown):\n");
  saved_asked = 0;
  f = facts(1, 1, 0, 0, 0, -1, 8);
  expect(join_why(&f, 300, saved_stub) == JOIN_MIDSEASON_DATE, "January-December league in August: held out by the date");
  expect(saved_asked == 0, "  ... without asking the save");
  f = facts(1, 1, 0, 0, 0, -1, 12);
  expect(join_why(&f, 300, saved_stub) == JOIN_MIDSEASON_DATE, "the same in December");
  f = facts(1, 1, 0, 0, 0, -1, 7);
  expect(join_why(&f, 300, saved_stub) == JOIN_MIDSEASON_DATE, "the same in July");
  f = facts(1, 0, 0, 0, 0, -1, 8);
  expect(join_why(&f, 510, saved_stub) == JOIN_SAVED_SEASON, "split parent entered at creation: held out (season in the save)");
  f = facts(1, 0, 0, 0, 0, -1, 8);
  expect(join_why(&f, 200, saved_stub) == JOIN_IN, "August-May league flagged and never entered (GitHub #19): appended");
  f = facts(1, 0, 1, 0, 0, -1, 8);
  expect(join_why(&f, 200, saved_stub) == JOIN_ROUNDS, "August-May league with rounds: held out (rounds), as since 01.10.");
  f = facts(1, 1, 0, 0, 0, -1, -1);
  expect(join_why(&f, 300, saved_stub) == JOIN_IN, "date unread: appended, the old answer");

  printf("after New Year, a January-December league's own registration day (February):\n");
  f = facts(1, 1, 0, 0, 0, 0, 2);
  expect(join_why(&f, 300, saved_stub) == JOIN_IN, "memory 'New Year passed': appended");
  f = facts(1, 1, 0, 0, 0, -1, 2);
  expect(join_why(&f, 300, saved_stub) == JOIN_IN, "memory unknown (loaded in January): appended");
  f = facts(1, 1, 0, 1, 0, -1, 2);
  expect(join_why(&f, 300, saved_stub) == JOIN_IN, "last season's final table does not hold it out");
  f = facts(1, 1, 0, 0, 0, 0, 2);
  expect(join_why(&f, 520, saved_stub) == JOIN_SAVED_SEASON, "one whose season the save still holds running: held out");

  printf("second season, July list seen (memory known):\n");
  f = facts(1, 0, 0, 1, 0, 1, 8);
  expect(join_why(&f, 200, saved_stub) == JOIN_TABLE, "August-May league with a table: held out (table)");
  f = facts(1, 1, 0, 1, 0, 1, 8);
  expect(join_why(&f, 300, saved_stub) == JOIN_MIDSEASON, "January-December league half way through: held out (mid-season)");
  f = facts(1, 0, 0, 0, 0, 1, 8);
  expect(join_why(&f, 200, saved_stub) == JOIN_IN, "August-May league the July build left out, nothing in the save: appended");

  printf("the reasons have their names:\n");
  int named = 1;
  for (int i = 0; i < JOIN_NREASONS; i++) named &= JOIN_WHY[i] && JOIN_WHY[i][0];
  expect(named, "every reason named for the summary line");

  if (fails) { printf("%d check(s) failed\n", fails); return 1; }
  printf("all checks passed\n");
  return 0;
}
