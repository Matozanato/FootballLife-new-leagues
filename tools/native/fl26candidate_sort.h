#ifndef FL26_CANDIDATE_SORT_H
#define FL26_CANDIDATE_SORT_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { CANDIDATE_BLOCK = 32 };
typedef struct {
    uint64_t player;
    uint32_t score;
    uint16_t regulation;
    uint16_t padding;
} Candidate;
_Static_assert(sizeof(Candidate) == 16 && offsetof(Candidate, score) == 8 &&
               offsetof(Candidate, regulation) == 12, "native candidate layout");
typedef int (*CandidateTie)(void*);

static uint32_t candidate_minimum(const Candidate* rows, size_t start, size_t end)
{
    uint32_t minimum = UINT32_MAX;
    for (size_t i = start; i < end; ++i)
        if (rows[i].score < minimum) minimum = rows[i].score;
    return minimum;
}

static size_t candidate_block_end(size_t start, size_t count)
{
    return count - start < CANDIDATE_BLOCK ? count : start + CANDIDATE_BLOCK;
}

static void candidate_sort(Candidate* rows, size_t count, uint32_t* minima,
                               CandidateTie tie, void* context)
{
    for (size_t start = 0; start < count; start += CANDIDATE_BLOCK)
        minima[start / CANDIDATE_BLOCK] =
            candidate_minimum(rows, start, candidate_block_end(start, count));

    for (size_t i = 0; i < count; ++i) {
        size_t best = i;
        uint32_t score = rows[i].score;
        for (size_t j = i + 1; j < count;) {
            const size_t start = j / CANDIDATE_BLOCK * CANDIDATE_BLOCK;
            const size_t end = candidate_block_end(start, count);
            /* A rival with the same score must still consume a native tie draw. */
            if (j != start || minima[start / CANDIDATE_BLOCK] <= score) {
                for (; j < end; ++j) {
                    const uint32_t value = rows[j].score;
                    if (value == score) {
                        if (tie(context)) best = j;
                    } else if (value < score) {
                        best = j;
                        score = value;
                    }
                }
            }
            j = end;
        }
        if (best == i) continue;
        const uint32_t prior = rows[i].score;
        unsigned char saved[14];
        memcpy(saved, rows + i, sizeof saved);
        memcpy(rows + i, rows + best, sizeof saved);
        memcpy(rows + best, saved, sizeof saved);
        /* Only a future block can be skipped later. An unequal swap can
           increase its minimum when the selected record was a minimum. */
        const size_t start = best / CANDIDATE_BLOCK * CANDIDATE_BLOCK;
        if (start > i && score != prior && minima[start / CANDIDATE_BLOCK] == score)
            minima[start / CANDIDATE_BLOCK] =
                candidate_minimum(rows, start, candidate_block_end(start, count));
    }
}
#endif
