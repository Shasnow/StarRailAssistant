# CurrencyWarsPlus reliability fixes

Related: [Discussion #258](https://github.com/Shasnow/StarRailAssistant/discussions/258).
Prepared independently from upstream `89ee0347fdda48f37ea96c38d409aeb12afbe8e4`.
The source changes were investigated in the fork at
`d4625a8a1cfcd54b49fd069cb476435ca2d96396`, not merged wholesale.
CurrencyWarsPlus itself, its transaction checks and its strategies already exist upstream.

## Problems and bounded changes

| Problem | Root cause | Change | Main regression |
| --- | --- | --- | --- |
| Slow purchase rechecks repeat complete scans | A serial pass rejects its early evidence at the end, or ages unrelated slots into its own work list | Decide age eligibility at the beginning of each attempt; keep real observation timestamps | `test_cw_purchase_reliability.py` |
| Untouched empty field evidence is repeatedly discarded | New-game/zero-population evidence intentionally has no per-slot OCR receipt | Recognize that structural baseline separately; never reuse it for a dirty target | Same file |
| Full recovery reopens empty bench panels | Fresh two-frame vacancies are discarded with the old snapshot | Preserve the newly acquired vacancy observations, without skipping layout validation | Same file |
| A complete frontend empty glyph becomes UNKNOWN | Animated-background antialiasing narrowly fails an exact contour band | Keep the original path; add guarded one-grid-pixel tolerance only for frontend glyphs | `test_cw_frontend_reliability.py` |
| Ordinary Blade cannot pass disputed-role review | Review hardcodes 0.9, unlike normal configured name OCR; recorded names scored 0.89194/0.89328 | Use the configured name confidence with a 0.7 floor; retain two agreeing names/stars and layouts before/after | `test_cw_identity_reliability.py` |
| Local F/D silently do nothing under a non-Latin layout | Logical Windows key lookup can return -1 without an input exception | Extension-local physical scan codes, foreground-window check, bounded hold and unconditional release | `test_cw_shop_input_reliability.py` |
| An empty strategy field is submitted | A completed paste call is mistaken for visible input | Authenticate the native paste button, paste once, and require visible configured-code text before submit | `test_cw_strategy_reliability.py` |
| A winning overclock summary never advances | The summary lacks the expected current-rank panel | Authenticate success header, health label, evaluation, exact action and button template on the same frame | `test_cw_terminal_reliability.py` |
| Native OCR reads only a partial next-action label | Native-size action OCR truncates the last character | Retry the same action ROI at 2x, still requiring the complete high-confidence label | Same file |
| Final HP stays unknown on a legible screenshot | RGB OCR merges the heart/label/value boxes | Recognize heart-bearing labels before classifying evidence; same-frame gray retry cannot replace parsed weak, invalid or conflicting HP | Same file |

These are observation/input reliability changes, not new strategies. Two acceptance policies
are deliberately changed and should be reviewed explicitly: ordinary-role review now follows
the configured name threshold (minimum 0.7), and frontend glyph recognition has a bounded
antialiasing path. The latter still requires correlation >=0.90, the original coverage in
each of six bands, the original RGB distance/margin, and two agreeing fresh frames.
Backend glyph structure recognition keeps the original exact path.

The scan-start clock is local to one attempt; it neither increases the configured 60-second
refresh interval nor rewrites timestamps. Dirty slots, purchased identities, evidence already
expired at entry, unknown rewards, layout changes and pending transactions remain blockers.

## Input and transaction safety

- Only local CurrencyWarsPlus F/D are adapted. Other keys, browser input and global keyboard
  mappings/layouts are unchanged. The adapter never activates the game window.
- One rejected key-up permits only a protective key-up retry, not another paid key-down.
  Stop during the hold still releases the key. OS acceptance is not game acceptance.
- Existing currency, inventory, experience, store-change and pending-receipt checks remain.
  `ShoppingResult.result` describes the phase; use its counts and reason to determine whether
  an individual purchase progressed. In particular, `experience_no_progress` is not a purchase.
- Strategy text requires a 12-character contiguous fragment of the configured code, not an
  exact transcription. This proves visibility only; the existing two-observation application
  result check remains necessary. Test strings are synthetic, not real share codes.
- Terminal navigation still requires two agreeing fresh pages. An enlarged action cannot
  override a different confidently recognized native action. Missing HP remains unknown.
- The HP parser recognizes `❤`, `♥` and `♡` immediately after the exact health label, retaining
  the original boxes, 0.9 confidence, range and conflict checks. Parsed invalid/weak/conflicting
  RGB HP cannot authorize gray replacement; genuinely missing label/value evidence may retry.
- Strategy input rejects Python/NumPy boolean scores in supported raw rows and modern OCR
  objects before they can authorize submission. Numeric scores retain the existing comparison
  policy; arbitrary unknown OCR adapter formats are not claimed to be validated.
- The program records challenge success/failure, not an inferred SSS rank. SSS below is visible
  historical screenshot evidence, not a new rank detector or a guaranteed run outcome.

## Offline verification

Use Python 3.12 and a disposable APPDATA/LOCALAPPDATA/TEMP/TMP profile. Never point tests at
the working installation. The public entry-point regressions use fake capture/OCR/input/time
boundaries with real decision and visual-analysis implementations; they do not launch HSR.

```text
python -m pytest -q -p no:cacheprovider tests/test_cw_purchase_reliability.py tests/test_cw_frontend_reliability.py tests/test_cw_identity_reliability.py
python -m pytest -q -p no:cacheprovider tests/test_cw_shop_input_reliability.py tests/test_cw_strategy_reliability.py tests/test_cw_terminal_reliability.py tests/test_cw_transaction_guards.py
python -m pytest -q -p no:cacheprovider
```

`test_cw_terminal_real_ocr.py` is opt-in with `SRA_CW_REAL_OCR=1` and already installed
PP-OCRv6/classifier models. It uses the real CPU OCR sessions and the public terminal entry
point, blocks network downloads, and uses saved summary pixels plus synthetic follow-up
pages and virtual clicks. It is not a live run. Without opt-in its two cases are skipped;
Win32 input cases are explicitly skipped outside Windows.

The frozen upstream baseline passes 1345 tests. The initial candidate passed **1434 tests
in 635.97 seconds**, with **zero failures, errors or skips**, including the two opt-in real
CPU OCR cases. Final review added 33 targeted public-reader/import cases for heart labels,
fallback preservation, geometry, frame agreement and supported boolean/numeric output shapes.
Against the initial candidate, 12 of these fail behaviorally and 21 preservation controls pass;
all 33 pass their focused checks after the minimal fixes. The final frozen suite passes
**1467 tests in 563.32 seconds**, with zero failures/errors/skips and real CPU OCR enabled.
All 1434 previous test identities are retained. Of the baseline cases, 1318 concern localization,
not CurrencyWarsPlus. Production/test/fixture bytes did not change after the final run.
The original 14 selected defect regressions fail
against those pristine production files, while 11 preservation controls pass there.
Full blocking lint still reports the existing `F821 tokens` in
`extensions/cw_plus/population_vision.py:240`; that file is unchanged. This does not claim
the entire existing CI is green. The targeted fixes do not change models, providers or global OCR.

## Historical full-run evidence: scope and limitations

Twenty available original extension journals were inspected. One shows the complete sequence
of 13 confirmed battles through the final settlement of a real 2026-10-27 RU-fork game.
Its runtime engine hash was
`a1c1cb176a263a04c737f2942314882509836577f4025a93572236a999b7122c`,
**not this branch**. The original private log SHA256 is
`d9428340473441e1d61f7af336031b6df69d38fb584ba792053beb940f10fd48`.
The table is a redacted extraction; machine/account names, IDs, paths and custom strategy data
are omitted, not fabricated. Raw journals are not committed.

| Original log line | Time | Confirmed battles | Evidence |
| ---: | --- | ---: | --- |
| 301 | 00:18:11.304 | 1 | settlement_or_next_stage |
| 611 | 00:23:34.140 | 2 | settlement_or_next_stage |
| 1219 | 00:31:36.342 | 3 | settlement_or_next_stage |
| 1427 | 00:34:57.054 | 4 | settlement_or_next_stage |
| 1975 | 00:42:41.687 | 5 | settlement_or_next_stage |
| 2181 | 00:46:18.238 | 6 | settlement_or_next_stage |
| 2591 | 00:52:22.520 | 7 | settlement_or_next_stage |
| 2799 | 00:55:40.407 | 8 | settlement_or_next_stage |
| 3159 | 01:01:35.531 | 9 | settlement_or_next_stage |
| 3559 | 01:07:15.706 | 10 | settlement_or_next_stage |
| 3845 | 01:11:31.125 | 11 | settlement_or_next_stage |
| 4165 | 01:15:50.971 | 12 | settlement_or_next_stage |
| 4413 | 01:20:28.368 | 13 | stable_terminal:final_settle |

The [sanitized winning panel](../tests/fixtures/terminal_overclock/summary.png) visibly shows
`挑战成功`, `SSS` and `100 HP`. Its pixels were verified against the crop of the available
original diagnostic image, SHA256
`476e27acc0dc2d6d3fb53961867ae86b6c41ca0e98f8fd2b682f5541eca1518c`.
The old final HP parser did **not** confirm that value; the screenshot did.

The game reached final victory approximately 1h 7m 26s after extension start. At 01:22:30.970
the journal records `result_terminal_navigation_timeout`; automatic return to the main menu
was not confirmed, and the user reported manually stopping the task. This is evidence of
gameplay reaching a winning final screen, **not** a clean autonomous end-to-end completion.
A later 12-battle fragment and other partial/manual runs are not counted as complete runs.

The three small frontend crops are genuine crops from two historical runs. The backend row
and both summary crops were checked against available original diagnostics. Import-dialog
assets come from the pinned fork and contain an empty field, not a user's code. Follow-up
terminal pages in replay are explicitly synthetic. No UID, account name or executable/model
binary is included; PNG fixtures and reviewed UI template crops are the only binary assets.

## Live acceptance still required

No HSR/account input or new live run was performed for this branch. After explicit user
permission, test one monitored run from this exact source revision in a separate runtime
profile, using the user's chosen unchanged upstream strategy and no copied account settings.
Record the runtime hashes, purchases/sales and refusals, equipment receipts, all battles,
final screen, HP evidence, navigation back to the start menu and checkpoint finalization.
Stop on unknown identities or unconfirmed transactions; do not replay paid input, reset a
saved game, overwrite the RU installation, or switch AutoPlot for a comparison.
Redact UID/account/code/path data before sharing evidence. Until that acceptance succeeds,
do not claim complete autonomous Currency Wars validation or a whole-run speedup.
