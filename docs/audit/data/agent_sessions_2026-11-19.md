# Agent sessions (raw usage data, collected 2026-11-19)

Source: Claude Code Remote session API (`get_session`, `external_metadata`), queried 2026-11-19 ~22:50 UTC. This is data, not interpretation.

Field notes: times are UTC (created_at / updated_at, truncated to the minute); Duration = Last update - Created (h:mm), wall-clock, not active time. Status = status_bucket without the `SESSION_STATUS_BUCKET_` prefix. Model = configured_model; external_metadata.last_served_model was identical wherever present (shown as `(served n/a)` where absent). Env A = env_018bGtjMjTuiXrFRESCejUn6, Env B = env_01MTWJVTWBHG13yZcRS4DzCz. Cost / token fields from external_metadata.usage; Context used = external_metadata.context_usage.used_tokens. `n/a` = field missing in the API response. Sessions still WORKING (incl. the original Supervisor, which ran this collection) are a point-in-time snapshot. Rows: round-2 Supervisor (session_01NPjxeNGwvGuevzV1aTjiEo), original Supervisor (session_01NPjxeNTmHt2DtBN8F8uLqB), and all 58 sessions whose parent_session_id is the round-2 Supervisor.

| # | Task | Title | Model | Env | Created | Last update | Duration | Status | Cost USD | Output tokens | Input tokens | Cache read tokens | Cache write tokens | Context used tokens |
|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | - | Custom 3D animation engine design | claude-opus-5-5 | A | 2026-11-12 23:33 | 2026-11-19 22:48 | 167:15 | WORKING | 676.81 | 3,710,391 | 419,300 | 2,156,160,113 | 20,544,284 | 613,677 |
| 2 | - | Plush Studio – Supervisor (round 2) | claude-opus-5-5 | A | 2026-11-18 14:52 | 2026-11-19 22:48 | 31:56 | REVIEW_READY | 240.68 | 677,707 | 151,028 | 1,010,799,766 | 3,098,519 | 316,539 |
| 3 | T-085 | Plush Studio – T-085 renderer optional | claude-opus-5-5 | A | 2026-11-18 14:53 | 2026-11-18 15:32 | 0:38 | COMPLETED | 3.48 | 42,219 | 612 | 7,959,063 | 129,757 | 194,839 |
| 4 | T-087 | Plush Studio – T-087 review recipe | claude-opus-5-5 | A | 2026-11-18 14:53 | 2026-11-18 15:46 | 0:53 | COMPLETED | 7.25 | 84,365 | 200 | 19,399,449 | 210,059 | 274,723 |
| 5 | T-088 | Plush Studio – T-088 version switch | claude-opus-5-5 | A | 2026-11-18 14:53 | 2026-11-18 15:02 | 0:09 | COMPLETED | 4.02 | 54,750 | 607 | 8,434,159 | 154,809 | 218,827 |
| 6 | T-086 | Plush Studio – T-086 CI efficiency | claude-opus-5-5 | A | 2026-11-18 15:56 | 2026-11-18 16:06 | 0:10 | COMPLETED | 3.52 | 49,718 | 1,110 | 7,695,082 | 122,016 | 186,035 |
| 7 | T-089 | Plush Studio – T-089 face/eyes r3 | claude-opus-5-5 | A | 2026-11-18 16:33 | 2026-11-18 22:12 | 5:39 | COMPLETED | 18.77 | 161,038 | 3,462 | 63,144,556 | 362,693 | 426,864 |
| 8 | T-092 | Plush Studio – T-092 materials | claude-opus-5-5 | A | 2026-11-18 16:33 | 2026-11-18 17:59 | 1:26 | COMPLETED | 10.64 | 91,116 | 5,333 | 33,524,055 | 260,719 | 324,738 |
| 9 | T-093 | Plush Studio – T-093 garments | claude-opus-5-5 | A | 2026-11-18 16:33 | 2026-11-18 22:12 | 5:39 | COMPLETED | 25.52 | 246,874 | 4,204 | 82,080,716 | 517,606 | 136,553 |
| 10 | T-095 | Plush Studio – T-095 two-person exchange | claude-opus-5-5 | A | 2026-11-18 16:33 | 2026-11-18 19:34 | 3:01 | COMPLETED | 10.47 | 105,763 | 2,295 | 30,255,997 | 286,573 | 320,039 |
| 11 | T-096 | Plush Studio – T-096 clearance and grip | claude-opus-5-5 | A | 2026-11-18 16:33 | 2026-11-18 19:18 | 2:45 | COMPLETED | 17.83 | 201,940 | 1,350 | 53,222,029 | 392,192 | 456,211 |
| 12 | T-098L | Plush Studio – T-098L set/light experiment | claude-opus-5-5 | A | 2026-11-18 18:21 | 2026-11-18 19:16 | 0:54 | COMPLETED | 4.57 | 53,525 | 3,186 | 12,050,107 | 134,226 | 198,245 |
| 13 | T-104 | Plush Studio – T-104 timing calibration | claude-opus-5-5 | A | 2026-11-18 21:38 | 2026-11-18 23:36 | 1:57 | COMPLETED | 9.99 | 98,614 | 1,792 | 30,723,334 | 232,213 | 296,232 |
| 14 | T-091 | Plush Studio – T-091 hair round 4 | claude-opus-5-5 | A | 2026-11-18 22:33 | 2026-11-19 01:03 | 2:30 | COMPLETED | 10.33 | 106,220 | 259 | 30,037,866 | 274,238 | 338,257 |
| 15 | T-089b | Plush Studio – T-089b face polish | claude-opus-5-5 | A | 2026-11-18 22:33 | 2026-11-19 01:24 | 2:51 | COMPLETED | 4.33 | 38,731 | 103 | 14,781,552 | 75,025 | 310,985 |
| 16 | T-093b | Plush Studio – T-093b garment completion | claude-opus-5-5 | A | 2026-11-18 22:33 | 2026-11-19 00:20 | 1:47 | COMPLETED | 7.80 | 80,606 | 223 | 22,264,724 | 216,734 | 280,753 |
| 17 | T-097A | Plush Studio – T-097A emotion blending | claude-opus-5-5 | A | 2026-11-18 22:39 | 2026-11-18 23:36 | 0:57 | COMPLETED | 6.42 | 85,611 | 1,684 | 16,204,868 | 181,963 | 246,927 |
| 18 | T-097B | Plush Studio – T-097B reactions | claude-opus-5-5 | A | 2026-11-18 23:33 | 2026-11-18 23:48 | 0:14 | COMPLETED | 3.04 | 40,420 | 87 | 6,378,856 | 119,197 | 183,216 |
| 19 | T-097C | Plush Studio – T-097C acting checks | claude-opus-5-5 | A | 2026-11-18 23:33 | 2026-11-18 23:39 | 0:05 | COMPLETED | 2.03 | 25,158 | 64 | 4,030,270 | 90,215 | 154,234 |
| 20 | T-097D | Plush Studio – T-097D reaction playback | claude-opus-5-5 | A | 2026-11-18 23:48 | 2026-11-19 00:17 | 0:29 | COMPLETED | 5.22 | 52,159 | 167 | 14,489,027 | 160,094 | 224,113 |
| 21 | T-097-boy | Plush Studio – T-097-boy acting | claude-opus-5-5 | A | 2026-11-18 23:48 | 2026-11-19 01:57 | 2:08 | COMPLETED | 16.74 | 135,938 | 423 | 56,762,551 | 332,670 | 396,689 |
| 22 | T-097-girl | Plush Studio – T-097-girl acting | claude-opus-5-5 | A | 2026-11-18 23:48 | 2026-11-19 01:46 | 1:57 | COMPLETED | 22.54 | 173,888 | 506 | 77,159,354 | 403,697 | 467,716 |
| 23 | T-094 | Plush Studio – T-094 versions 2.1.0 / 0.12.0 | claude-opus-5-5 | A | 2026-11-19 01:25 | 2026-11-19 03:48 | 2:22 | COMPLETED | 13.14 | 102,534 | 345 | 43,485,390 | 297,854 | 361,873 |
| 24 | T-111 | Plush Studio – T-111 interaction architect | claude-opus-5-5 | A | 2026-11-19 02:57 | 2026-11-19 03:04 | 0:06 | COMPLETED | 2.12 | 32,409 | 50 | 3,287,553 | 102,111 | 166,357 |
| 25 | T-101 | Plush Studio – T-101 old failing tests | claude-opus-5-5 | A | 2026-11-19 02:57 | 2026-11-19 05:24 | 2:26 | COMPLETED | 11.98 | 110,233 | 342 | 38,414,372 | 260,553 | 329,065 |
| 26 | T-110 | Plush Studio – T-110 felt surface | claude-opus-5-5 | A | 2026-11-19 02:57 | 2026-11-19 04:16 | 1:18 | COMPLETED | 9.47 | 98,470 | 245 | 27,129,499 | 258,353 | 326,864 |
| 27 | T-104d | Plush Studio – T-104d timing default | claude-opus-5-5 | A | 2026-11-19 02:57 | 2026-11-19 04:40 | 1:42 | COMPLETED | 3.21 | 31,555 | 131 | 8,737,864 | 104,153 | 172,664 |
| 28 | T-112a | Plush Studio – T-112a verbs | claude-opus-5-5 | A | 2026-11-19 03:04 | 2026-11-19 03:42 | 0:37 | COMPLETED | 10.64 | 119,560 | 251 | 30,431,190 | 270,028 | 338,540 |
| 29 | T-112b | Plush Studio – T-112b pass verb | claude-opus-5-5 | A | 2026-11-19 03:42 | 2026-11-19 04:54 | 1:12 | COMPLETED | 13.34 | 139,389 | 269 | 39,767,437 | 324,852 | 393,364 |
| 30 | T-051 | Plush Studio – T-051 finger grasps | claude-opus-5-5 | A | 2026-11-19 03:42 | 2026-11-19 04:59 | 1:17 | COMPLETED | 11.99 | 137,660 | 281 | 34,839,975 | 283,230 | 351,742 |
| 31 | T-109 | Plush Studio – T-109 face round 4 | claude-opus-5-5 | A | 2026-11-19 03:48 | 2026-11-19 05:59 | 2:10 | COMPLETED | 12.93 | 128,739 | 312 | 39,837,352 | 298,394 | 366,905 |
| 32 | T-112c | Plush Studio – T-112c verb hands | claude-opus-5-5 | A | 2026-11-19 05:00 | 2026-11-19 07:08 | 2:08 | COMPLETED | 11.17 | 89,736 | 302 | 37,028,067 | 245,143 | 313,655 |
| 33 | T-113 | Plush Studio – T-113 expressions | claude-opus-5-5 | A | 2026-11-19 05:59 | 2026-11-19 10:40 | 4:41 | COMPLETED | n/a | n/a | n/a | n/a | n/a | 0 |
| 34 | T-114 | Plush Studio – T-114 two-character acting | claude-opus-5-5 | A | 2026-11-19 10:42 | 2026-11-19 14:06 | 3:24 | COMPLETED | 11.33 | 93,654 | 795 | 29,833,468 | 435,430 | 291,708 |
| 35 | T-118 | Plush Studio – T-118 hair round 5 | claude-fable-5-2 | A | 2026-11-19 11:37 | 2026-11-19 12:25 | 0:48 | COMPLETED | 9.90 | 87,732 | 143 | 14,483,102 | 217,987 | 282,358 |
| 36 | T-119 | Plush Studio – T-119 garments round 3 | claude-fable-5-2 | A | 2026-11-19 11:37 | 2026-11-19 14:34 | 2:56 | COMPLETED | n/a | n/a | n/a | n/a | n/a | 339,799 |
| 37 | T-120 | Plush Studio – T-120 gaze legibility | claude-fable-5-2 | A | 2026-11-19 11:37 | 2026-11-19 12:06 | 0:29 | COMPLETED | 5.85 | 54,352 | 82 | 6,764,324 | 145,363 | 216,639 |
| 38 | T-121 | Plush Studio – T-121 finger separation | claude-opus-5-5 | A | 2026-11-19 11:37 | 2026-11-19 12:35 | 0:57 | COMPLETED | 6.64 | 60,073 | 2,244 | 20,253,901 | 171,638 | 237,165 |
| 39 | T-122 | Plush Studio – T-122 candidate versions 2.2.0/0.13.0 | claude-opus-5-5 | A | 2026-11-19 11:37 | 2026-11-19 12:54 | 1:17 | COMPLETED | 3.13 | 27,496 | 1,145 | 8,904,081 | 99,236 | 169,028 |
| 40 | T-124 | Plush Studio – T-124 render optimisation 720p | claude-opus-5-5 | A | 2026-11-19 12:49 | 2026-11-19 22:38 | 9:49 | WORKING | 9.72 | 72,829 | 15,512 | 29,860,280 | 277,713 | 231,666 |
| 41 | T-125 | Plush Studio – T-125 automatic motion checks | claude-opus-5-5 | A | 2026-11-19 13:02 | 2026-11-19 17:59 | 4:56 | COMPLETED | 13.96 | 176,655 | 5,010 | 36,634,973 | 384,971 | 176,263 |
| 42 | T-127 | Plush Studio – T-127 CI speed | claude-opus-5-5 | A | 2026-11-19 13:24 | 2026-11-19 15:44 | 2:19 | COMPLETED | 10.93 | 93,019 | 2,296 | 32,231,588 | 325,963 | 397,302 |
| 43 | T-128 | Plush Studio – T-128 tooling trial | claude-opus-5-5 | A | 2026-11-19 13:50 | 2026-11-19 14:29 | 0:38 | COMPLETED | 2.64 | 35,187 | 610 | 6,451,584 | 80,190 | 149,983 |
| 44 | T-117 | Plush Studio – T-117 8 s cup-exchange showcase | claude-opus-5-5 | A | 2026-11-19 14:07 | 2026-11-19 17:30 | 3:22 | COMPLETED | 6.10 | 62,232 | 1,706 | 17,406,185 | 170,999 | 239,097 |
| 45 | T-131 | Plush Studio – T-131 make boy 2.2.0 / girl 0.13.0 current | claude-opus-5-5 | B | 2026-11-19 15:02 | 2026-11-19 15:18 | 0:16 | COMPLETED | 1.91 | 19,406 | 591 | 4,945,318 | 66,273 | 136,066 |
| 46 | T-126a | Plush Studio – T-126a third character body + face | claude-opus-5-5 | B | 2026-11-19 15:18 | 2026-11-19 19:02 | 3:43 | COMPLETED | 7.46 | 63,016 | 1,717 | 18,451,024 | 311,998 | 252,298 |
| 47 | T-126b | Plush Studio – T-126b third character hair | claude-fable-5-2 | B | 2026-11-19 15:18 | 2026-11-19 18:07 | 2:48 | COMPLETED | 11.95 | 69,189 | 1,164 | 14,977,797 | 385,844 | 276,631 |
| 48 | T-126d | Plush Studio – T-126d third character materials | claude-opus-5-5 | B | 2026-11-19 15:18 | 2026-11-19 15:27 | 0:09 | COMPLETED | 2.51 | 24,199 | 1,120 | 6,730,183 | 83,601 | 152,112 |
| 49 | T-126c | Plush Studio – T-126c third character dress + skirt cloth | claude-fable-5-2 | B | 2026-11-19 15:19 | 2026-11-19 19:22 | 4:03 | COMPLETED | 5.54 | 52,275 | 68 | 5,443,777 | 147,523 | 217,518 |
| 50 | T-130 | Plush Studio – T-130 workflow evaluation round 4 | claude-sonnet-5-5 | B | 2026-11-19 17:30 | 2026-11-19 17:38 | 0:07 | COMPLETED | 0.56 | 11,325 | 41 | 2,046,772 | 59,544 | 123,915 |
| 51 | T-132 | Plush Studio – T-132 candidates boy 2.3.0 / girl 0.14.0 | claude-opus-5-5 | B | 2026-11-19 17:40 | 2026-11-19 18:30 | 0:49 | COMPLETED | 4.51 | 47,863 | 1,680 | 12,129,398 | 139,848 | 208,360 |
| 52 | T-134 | Plush Studio – T-134 E1 reach mechanics | claude-fable-5-2 | B | 2026-11-19 20:08 | 2026-11-19 22:47 | 2:39 | COMPLETED | 23.53 | 202,092 | 308 | 46,337,688 | 385,686 | 455,144 |
| 53 | T-135 | Plush Studio – T-135 E1m reach measurements | claude-opus-5-5 | B | 2026-11-19 20:08 | 2026-11-19 22:23 | 2:15 | COMPLETED | 3.29 | 47,034 | 614 | 7,432,930 | 107,500 | 177,232 |
| 54 | T-136 | Plush Studio – T-136 E2 blinks + E3 gaze chain | claude-opus-5-5 | B | 2026-11-19 20:08 | 2026-11-19 22:22 | 2:13 | WORKING | 9.42 | 104,618 | 1,285 | 27,473,261 | 227,770 | 291,248 |
| 55 | T-137 | Plush Studio – T-137 faces round 5 (F1a/F1b/F2) | claude-fable-5-2 | B | 2026-11-19 20:08 | 2026-11-19 22:43 | 2:34 | WORKING | 10.85 | 72,119 | 5,305 | 27,683,034 | 148,979 | 309,128 |
| 56 | T-139 | Plush Studio – T-139 E5 animcheck attribution | claude-opus-5-5 | B | 2026-11-19 20:36 | 2026-11-19 20:49 | 0:13 | COMPLETED | 1.94 | 21,422 | 82 | 4,745,197 | 70,114 | 138,089 |
| 57 | T-140 | Plush Studio – T-140 C1 framing | claude-opus-5-5 | B | 2026-11-19 20:50 | 2026-11-19 22:20 | 1:30 | COMPLETED | 7.46 | 85,698 | 261 | 22,090,237 | 165,755 | 233,729 |
| 58 | T-143 | Plush Studio – T-143 A4 cleanup | claude-sonnet-5-5 | B | 2026-11-19 22:09 | 2026-11-19 22:30 | 0:20 | COMPLETED | 0.56 | 12,521 | 44 | 2,228,341 | 53,346 | 117,180 |
| 59 | T-142 | Plush Studio – T-142 A1 legacy removal (step 1 report) | claude-opus-5-5 | B | 2026-11-19 22:23 | 2026-11-19 22:49 | 0:25 | WORKING | 1.51 | 17,443 | 55 | 3,175,960 | 65,111 | 133,086 |
| 60 | T-138 | Plush Studio – T-138 E4 grasp accuracy | claude-opus-5-5 (served n/a) | B | 2026-11-19 22:48 | 2026-11-19 22:48 | 0:00 | WORKING | n/a | n/a | n/a | n/a | n/a | n/a |
| | **Total (60 sessions)** | | | | | | | | **1,385.19** | **8,920,485** | 644,401 | **4,469,230,596** | **35,472,552** | |

## Totals by model (configured_model)

| Model | Sessions | Cost USD | Output tokens | Input tokens | Cache read tokens | Cache write tokens |
|---|---:|---:|---:|---:|---:|---:|
| claude-opus-5-5 | 51 | 1,316.45 | 8,358,880 | 637,246 | 4,349,265,761 | 33,928,280 |
| claude-fable-5-2 | 7 | 67.62 | 537,759 | 7,070 | 115,689,722 | 1,431,382 |
| claude-sonnet-5-5 | 2 | 1.12 | 23,846 | 85 | 4,275,113 | 112,890 |
| **All** | **60** | **1,385.19** | **8,920,485** | **644,401** | **4,469,230,596** | **35,472,552** |

Sessions with no `usage` block (excluded from sums, counted in session totals): T-138 (just created, PENDING), T-119, T-113.
