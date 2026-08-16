# Risk Model Evaluation — Indicative Only (Low Label Precision)

## Defining the Ground Truth (SZZ-lite)

To evaluate whether the risk score accurately predicts defects, we need a ground truth of which files have historically introduced bugs. This relies on mining the repository's history using a simplified form of the SZZ algorithm (Śliwerski, Zimmermann, Zeller, 2005).

### Identifying Fix Commits

The rule for identifying bug-fixing commits is the following:

```python
FIX_PATTERNS = [
    r"\bfix(e[sd])?\b", r"\bbug\b", r"\bdefect\b", r"\bissue #?\d+\b",
    r"\bcloses? #\d+\b", r"\bresolves? #\d+\b", r"\bhotfix\b", r"\bregression\b",
]
REVERT_PATTERN = r'^Revert "'
```

Additional rules for filtering out noise:
- Commits touching exclusively documentation files (non-source files) are excluded.
- Merge commits are skipped.
- Commits touching more than 100 files are skipped, as they are likely bulk refactors or dependency updates.
- Revert commits (`Revert "..."`) provide the highest-precision signal of a defect introduction.

### Mandatory Manual Audit

We performed a manual audit of 30 randomly sampled labelled pairs (fix commit → introducing commit) to measure the precision of the SZZ approach on the target repository (`flask`), generated with a fixed seed of `42`.

**Audit Findings (30 pairs):**
- **Genuine defect introductions:** 11
- **Refactors, renames, or formatting misattributed by blame:** 8
- **Fix commits that were not really bug fixes:** 11

**Estimated Label Precision:** 11/30 (0.37)

**Sampled Pairs:**
1. `bda295d3` -> `1f20a112` (Genuine)
2. `e0afff0e` -> `025589ee` (Misattributed)
3. `cd14adbc` -> `7186a5aa` (Not a fix)
4. `a5ecdfa7` -> `71e10be2` (Misattributed)
5. `25357078` -> `d0cf5ef3` (Not a fix)
6. `b707bf44` -> `22987b68` (Genuine)
7. `0ec9192c` -> `9c02f07f` (Genuine)
8. `9e831e91` -> `a37f675c` (Misattributed)
9. `b8eba0a3` -> `18673ba3` (Misattributed)
10. `1f3923a9` -> `4cb6eea8` (Misattributed)
11. `e82db2ca` -> `4cb6eea8` (Misattributed)
12. `176fdfa0` -> `7ab934f6` (Genuine)
13. `25357078` -> `81576c23` (Not a fix)
14. `7ba35c4d` -> `e6178fe4` (Genuine)
15. `1928f28a` -> `97d2a198` (Not a fix)
16. `e82db2ca` -> `5e1b1030` (Genuine)
17. `2889da67` -> `7f87f3dd` (Not a fix)
18. `b8eba0a3` -> `a0801719` (Misattributed)
19. `25357078` -> `fa6eded6` (Not a fix)
20. `2a657943` -> `06a170ea` (Misattributed)
21. `e2f4b533` -> `3738f7ff` (Genuine)
22. `81798b40` -> `ca2bfbb0` (Not a fix)
23. `697f7b93` -> `d0dc89ea` (Not a fix)
24. `17d4cb38` -> `8fa5e32d` (Not a fix)
25. `59f7966e` -> `d0dc89ea` (Not a fix)
26. `1f1b65a6` -> `571b9f54` (Not a fix)
27. `ffca68fc` -> `8fa5e32d` (Genuine)
28. `dffe3034` -> `860a25c3` (Genuine)
29. `b5f4c521` -> `7d506f24` (Genuine)
30. `5fcc999b` -> `5e059be1` (Genuine)

**Runtime Performance:**
- SZZ extraction on `flask` (medium tier, max 200 fixes): 33 seconds
- SZZ extraction on `.` (chronopolis, max 200 fixes): 4.8 seconds

**Conclusion:** The literature reports a meaningful share of SZZ-flagged lines being refactoring noise. Our audit confirms this, finding a label precision of ~0.37, which is below the 0.6 threshold. **Therefore, every downstream number in this evaluation must be treated as indicative rather than conclusive.**
