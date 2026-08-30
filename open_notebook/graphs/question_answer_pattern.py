"""
Step 6 — answer-position / answer-set anti-pattern audit.

Batch-level, post-validation. Does not call an LLM.
Does not steer generation. Does not trigger refill or cognitive rejection.

After accepted questions are validated, Bank Batch may safely reorder options
to break obvious patterns and to randomly rebalance a skewed letter distribution.
Never invents a fixed ABCDE/ABAB sequence.

Final Paper: helper is reusable; do not hook into audit_paper matrix checks.
"""

from __future__ import annotations

import copy
import random
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

OPTION_LABELS = ("A", "B", "C", "D", "E")
N_OPTIONS = 5

# Conservative letter mentions we can remap with a permutation.
_REMAPPABLE_LETTER = re.compile(
    r"(?i)(?:\b(?:option|choice|answer|answers)\s*[A-E]\b|\([A-E]\)|"
    r"\b[A-E]\s+is\s+(?:the\s+)?correct\b|"
    r"\b[A-E]\s+are\s+correct\b|"
    r"\b[A-E](?:\s*,\s*[A-E])+\s*(?:and\s+[A-E])?\b|"
    r"\b[A-E]\s+and\s+[A-E]\b)"
)
_OPTION_LETTER_TOKEN = re.compile(r"(?i)\b(?:option|choice|answer)\s*([A-E])\b|\(([A-E])\)")
_LETTER_IS_CORRECT = re.compile(
    r"(?i)\b([A-E])\s+(?:is|are)\s+(?:the\s+)?correct\b"
)


def _atype(q: Dict[str, Any]) -> str:
    return str(q.get("answer_type") or "").strip()


def _indices(q: Dict[str, Any]) -> List[int]:
    raw = q.get("correct_indices") or []
    out: List[int] = []
    for x in raw:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if 0 <= i < N_OPTIONS:
            out.append(i)
    return sorted(set(out))


def _letter(idx: int) -> str:
    if 0 <= idx < len(OPTION_LABELS):
        return OPTION_LABELS[idx]
    return "?"


def _combo(indices: Sequence[int]) -> str:
    return "+".join(_letter(i) for i in sorted(indices))


def _letters_from_indices(indices: Sequence[int]) -> str:
    return "".join(_letter(i) for i in sorted(indices))


def single_correct_position_sequence(
    questions: Sequence[Dict[str, Any]],
) -> List[str]:
    seq: List[str] = []
    for q in _ordered(questions):
        if _atype(q) != "single_correct":
            continue
        idx = _indices(q)
        seq.append(_letter(idx[0]) if len(idx) == 1 else "?")
    return seq


def multiple_correct_set_sequence(
    questions: Sequence[Dict[str, Any]],
) -> List[str]:
    seq: List[str] = []
    for q in _ordered(questions):
        if _atype(q) != "multiple_correct":
            continue
        seq.append(_combo(_indices(q)))
    return seq


def _ordered(questions: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        list(questions or []),
        key=lambda q: int(q.get("question_number") or 0),
    )


def detect_single_correct_position_pattern(
    questions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Detect only obviously systematic Single Correct key patterns.

    Rules (all require enough length; small coincidences are ignored):
    - alphabetical run ABCDE or EDCBA of length 5+
    - wrapping +1 cycle of length >= 5 matching question order
    - period-2 alternation (ABAB, ACAC, ...) in a window of length >= 4
    - period-3 cycle (ABCABC) in a window of length >= 6
    - consecutive identical letter length >= 4
    - answer index == (question_number-1) % 5 for every Single item when n >= 5
    - one letter used for all but at most 0 answers when n >= 6
    """
    items: List[Tuple[int, int]] = []
    for q in _ordered(questions):
        if _atype(q) != "single_correct":
            continue
        idx = _indices(q)
        if len(idx) != 1:
            continue
        items.append((int(q.get("question_number") or 0), idx[0]))
    seq = [p for _, p in items]
    n = len(seq)
    if n < 4:
        return {"detected": False, "pattern_type": None, "sequence": [_letter(i) for i in seq]}

    letters = [_letter(i) for i in seq]

    if n >= 5 and all((qn - 1) % 5 == pos for qn, pos in items):
        return {"detected": True, "pattern_type": "question_number_determined", "sequence": letters}

    if n >= 6:
        freq = max(Counter(seq).values())
        if freq >= n - 1 or len(set(seq)) == 1:
            return {"detected": True, "pattern_type": "excessive_same_position", "sequence": letters}

    if len(set(seq)) == 1 and n >= 4:
        return {"detected": True, "pattern_type": "excessive_same_position", "sequence": letters}

    run = _max_consecutive_run(seq)
    if run >= 4:
        return {"detected": True, "pattern_type": "excessive_same_position", "sequence": letters}

    if _has_alpha_run(seq, 5):
        return {"detected": True, "pattern_type": "alphabetical_run", "sequence": letters}

    if _has_period2_window(seq, 4):
        return {"detected": True, "pattern_type": "alternating_period_2", "sequence": letters}

    if _has_period_window(seq, period=3, min_len=6):
        return {"detected": True, "pattern_type": "simple_cycle", "sequence": letters}

    return {"detected": False, "pattern_type": None, "sequence": letters}


def detect_multiple_correct_set_pattern(
    questions: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Detect excessive repetition of the same Multiple Correct letter combination.

    Does not treat 2-correct vs 3-correct alternation as a pattern.
    """
    combos = multiple_correct_set_sequence(questions)
    n = len(combos)
    if n < 3:
        return {"detected": False, "pattern_type": None, "sequence": combos}
    counts: Dict[str, int] = {}
    for c in combos:
        counts[c] = counts.get(c, 0) + 1
    top = max(counts.values()) if counts else 0
    if top >= 3 and (top >= 3 if n == 3 else top * 2 >= n or top >= 3):
        # n=3 all same → detect; n=4 two+two → do not (top=2); n=4 three same → detect
        if top >= 3:
            return {
                "detected": True,
                "pattern_type": "repeated_answer_set",
                "sequence": combos,
            }
    return {"detected": False, "pattern_type": None, "sequence": combos}


def _max_consecutive_run(seq: Sequence[int]) -> int:
    best = 1
    cur = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best if seq else 0


def _has_alpha_run(seq: Sequence[int], length: int) -> bool:
    if len(seq) < length:
        return False
    for i in range(len(seq) - length + 1):
        chunk = seq[i : i + length]
        up = all((chunk[j + 1] - chunk[j]) % N_OPTIONS == 1 for j in range(length - 1))
        down = all((chunk[j] - chunk[j + 1]) % N_OPTIONS == 1 for j in range(length - 1))
        if up or down:
            return True
    return False


def _has_period2_window(seq: Sequence[int], min_len: int) -> bool:
    if len(seq) < min_len:
        return False
    for i in range(len(seq) - min_len + 1):
        chunk = seq[i : i + min_len]
        a, b = chunk[0], chunk[1]
        if a == b:
            continue
        if all(chunk[j] == (a if j % 2 == 0 else b) for j in range(len(chunk))):
            return True
    return False


def _has_period_window(seq: Sequence[int], *, period: int, min_len: int) -> bool:
    if len(seq) < min_len:
        return False
    for i in range(len(seq) - min_len + 1):
        chunk = seq[i : i + min_len]
        base = list(chunk[:period])
        if len(set(base)) < 2:
            continue
        if all(chunk[j] == base[j % period] for j in range(len(chunk))):
            return True
    return False


def explanation_has_option_letters(explanation: str) -> bool:
    text = explanation or ""
    if _REMAPPABLE_LETTER.search(text):
        return True
    if _OPTION_LETTER_TOKEN.search(text):
        return True
    if _LETTER_IS_CORRECT.search(text):
        return True
    if re.search(r"\b[B-E]\b", text):
        return True
    return False


def explanation_letter_refs_are_remappable(explanation: str) -> bool:
    """True when every detected option-letter mention uses a known remappable form."""
    text = explanation or ""
    if not explanation_has_option_letters(text):
        return True
    # Strip remappable spans; leftover "Option X"-style tokens mean unsafe.
    stripped = _REMAPPABLE_LETTER.sub(" ", text)
    if _OPTION_LETTER_TOKEN.search(stripped) or _LETTER_IS_CORRECT.search(stripped):
        return False
    if re.search(r"\b[B-E]\b", stripped):
        return False
    return True


def remap_explanation_letters(explanation: str, old_to_new: Sequence[int]) -> str:
    if not (explanation or "").strip():
        return explanation or ""

    def new_letter(old: str) -> str:
        i = ord(old.upper()) - ord("A")
        if 0 <= i < len(old_to_new):
            mapped = OPTION_LABELS[old_to_new[i]]
            return mapped if old.isupper() else mapped.lower()
        return old

    holders: Dict[str, str] = {}
    counter = {"n": 0}

    def hold(m: re.Match) -> str:
        letter = next(g for g in m.groups() if g)
        key = f"<<L{counter['n']}>>"
        counter["n"] += 1
        holders[key] = new_letter(letter)
        return m.group(0).replace(letter, key, 1)

    text = _OPTION_LETTER_TOKEN.sub(hold, explanation)
    text = _LETTER_IS_CORRECT.sub(hold, text)
    for key, val in holders.items():
        text = text.replace(key, val)
    return text


def can_safely_reorder_options(question: Dict[str, Any]) -> Tuple[bool, str]:
    options = list(question.get("options") or [])
    if len(options) != N_OPTIONS:
        return False, "not_five_options"
    if any(not str(o).strip() for o in options):
        return False, "duplicate_or_blank_options"
    if len({str(o) for o in options}) != N_OPTIONS:
        return False, "duplicate_or_blank_options"
    atype = _atype(question)
    idx = _indices(question)
    if atype == "single_correct" and len(idx) != 1:
        return False, "single_index_invalid"
    if atype == "multiple_correct" and not (2 <= len(idx) <= 4):
        return False, "multiple_index_invalid"
    expl = str(question.get("explanation") or "")
    if explanation_has_option_letters(expl) and not explanation_letter_refs_are_remappable(expl):
        return False, "unsafe_explanation_letters"
    return True, ""


def apply_index_permutation(
    question: Dict[str, Any],
    old_to_new: Sequence[int],
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Reorder options so old index i moves to old_to_new[i].
    Returns (new_question_or_None, skip_reason).
    """
    ok, reason = can_safely_reorder_options(question)
    if not ok:
        return None, reason
    if len(old_to_new) != N_OPTIONS:
        return None, "bad_permutation"
    if sorted(old_to_new) != list(range(N_OPTIONS)):
        return None, "bad_permutation"

    old_options = [str(o) for o in (question.get("options") or [])]
    old_idx = _indices(question)
    old_correct_texts = [old_options[i] for i in old_idx]

    new_options = [""] * N_OPTIONS
    for old_i, new_i in enumerate(old_to_new):
        new_options[new_i] = old_options[old_i]
    new_idx = sorted(int(old_to_new[i]) for i in old_idx)

    expl = str(question.get("explanation") or "")
    new_expl = expl
    if explanation_has_option_letters(expl):
        new_expl = remap_explanation_letters(expl, old_to_new)
        if explanation_has_option_letters(new_expl) and not explanation_letter_refs_are_remappable(new_expl):
            return None, "unsafe_explanation_letters"

    updated = copy.copy(question)
    updated["options"] = new_options
    updated["correct_indices"] = new_idx
    updated["answer"] = _letters_from_indices(new_idx)
    updated["explanation"] = new_expl
    updated["option_defensibility"] = _remap_option_defensibility(
        question.get("option_defensibility"), old_to_new
    )
    bs = question.get("blind_solver_answer")
    if isinstance(bs, str) and bs and "N/A" not in bs:
        updated["blind_solver_answer"] = remap_explanation_letters(bs, old_to_new)

    err = validate_post_shuffle(question, updated)
    if err:
        return None, err
    if [new_options[i] for i in new_idx] != old_correct_texts:
        return None, "correct_text_mismatch"
    return updated, ""


def _remap_option_defensibility(value: Any, old_to_new: Sequence[int]) -> Any:
    if not isinstance(value, list):
        return value
    out = []
    for item in value:
        if not isinstance(item, dict):
            out.append(item)
            continue
        row = dict(item)
        lab = str(row.get("option") or "").strip().upper()
        if lab in OPTION_LABELS:
            old_i = OPTION_LABELS.index(lab)
            row["option"] = OPTION_LABELS[old_to_new[old_i]]
        out.append(row)
    return out


def validate_post_shuffle(
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> str:
    old_opts = [str(o) for o in (before.get("options") or [])]
    new_opts = [str(o) for o in (after.get("options") or [])]
    if len(new_opts) != N_OPTIONS:
        return "not_five_options"
    if sorted(old_opts) != sorted(new_opts):
        return "option_multiset_changed"
    if len(set(new_opts)) != N_OPTIONS:
        return "duplicate_options_after_shuffle"
    atype = _atype(after)
    idx = _indices(after)
    if atype == "single_correct" and len(idx) != 1:
        return "single_not_one_correct"
    if atype == "multiple_correct" and not (2 <= len(idx) <= 4):
        return "multiple_count_invalid"
    old_correct = sorted(str((before.get("options") or [])[i]) for i in _indices(before))
    new_correct = sorted(str(new_opts[i]) for i in idx)
    if old_correct != new_correct:
        return "correct_set_changed"
    if str(after.get("question") or "") != str(before.get("question") or ""):
        return "stem_changed"
    return ""


def _swap_perm(src: int, dst: int) -> List[int]:
    perm = list(range(N_OPTIONS))
    perm[src], perm[dst] = dst, src
    return perm


def _rotate_perm(k: int) -> List[int]:
    return [(i + k) % N_OPTIONS for i in range(N_OPTIONS)]


def position_distribution(seq: Sequence[str]) -> Dict[str, int]:
    counts = {lab: 0 for lab in OPTION_LABELS}
    for s in seq:
        if s in counts:
            counts[s] += 1
    return counts


def needs_randomized_position_balance(seq: Sequence[str]) -> bool:
    """True when Single Correct keys are too concentrated on one letter or a run."""
    letters = [s for s in seq if s in OPTION_LABELS]
    n = len(letters)
    if n < 4:
        return False
    max_c = max(Counter(letters).values())
    ceil_share = (n + N_OPTIONS - 1) // N_OPTIONS
    if max_c > ceil_share + 1:
        return True
    run = 1
    for i in range(1, len(letters)):
        if letters[i] == letters[i - 1]:
            run += 1
            if run >= 3:
                return True
        else:
            run = 1
    return False


def _balanced_letter_quota(n: int, rng: random.Random) -> List[int]:
    base, rem = divmod(max(0, n), N_OPTIONS)
    quota = [base] * N_OPTIONS
    extra = list(range(N_OPTIONS))
    rng.shuffle(extra)
    for i in extra[:rem]:
        quota[i] += 1
    return quota


def _break_target_runs(targets: List[int], rng: random.Random) -> List[int]:
    out = list(targets)
    for _ in range(len(out)):
        changed = False
        run = 1
        for i in range(1, len(out)):
            if out[i] == out[i - 1]:
                run += 1
                if run >= 3:
                    mid = i - 1
                    cands = [
                        j
                        for j, val in enumerate(out)
                        if val != out[mid] and abs(j - mid) > 1
                    ]
                    if not cands:
                        cands = [j for j, val in enumerate(out) if val != out[mid]]
                    if cands:
                        swap = rng.choice(cands)
                        out[mid], out[swap] = out[swap], out[mid]
                        changed = True
                        break
            else:
                run = 1
        if not changed:
            break
    return out


def _assign_balanced_targets(
    current: Sequence[int],
    rng: random.Random,
) -> List[int]:
    n = len(current)
    remaining = list(_balanced_letter_quota(n, rng))
    targets = [-1] * n
    overflow: List[int] = []
    order = list(range(n))
    rng.shuffle(order)
    for i in order:
        cur = int(current[i])
        if 0 <= cur < N_OPTIONS and remaining[cur] > 0:
            targets[i] = cur
            remaining[cur] -= 1
        else:
            overflow.append(i)
    leftover: List[int] = []
    for letter, cnt in enumerate(remaining):
        leftover.extend([letter] * cnt)
    rng.shuffle(leftover)
    for i, dest in zip(overflow, leftover):
        targets[i] = dest
    for i, dest in enumerate(targets):
        if dest < 0:
            targets[i] = int(current[i]) if 0 <= int(current[i]) < N_OPTIONS else 0
    return _break_target_runs(targets, rng)


def _balance_single_correct_positions(
    questions: List[Dict[str, Any]],
    rng: random.Random,
) -> Tuple[List[Dict[str, Any]], List[int], List[Dict[str, Any]]]:
    reordered: List[int] = []
    skipped: List[Dict[str, Any]] = []
    out = questions
    singles_idx = [
        i
        for i, q in enumerate(out)
        if _atype(q) == "single_correct" and len(_indices(q)) == 1
    ]
    current = [_indices(out[i])[0] for i in singles_idx]
    seq = [_letter(x) for x in current]
    if not needs_randomized_position_balance(seq):
        return out, reordered, skipped
    targets = _assign_balanced_targets(current, rng)
    for k, i in enumerate(singles_idx):
        q = out[i]
        cur, dest = current[k], targets[k]
        if cur == dest:
            continue
        qn = int(q.get("question_number") or 0)
        ok, reason = can_safely_reorder_options(q)
        if not ok:
            skipped.append({"question_number": qn, "reason": reason})
            continue
        updated, err = apply_index_permutation(q, _swap_perm(cur, dest))
        if not updated:
            if err:
                skipped.append({"question_number": qn, "reason": err})
            continue
        out[i] = updated
        reordered.append(qn)
    return out, reordered, skipped


def apply_answer_position_audit(
    questions: Sequence[Dict[str, Any]],
    *,
    rng: Optional[random.Random] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Inspect accepted questions; safely reorder options to break obvious patterns
    and to randomly rebalance a skewed Single Correct letter distribution.

    Never regenerates stems. Never changes accepted count. Never rejects.
    """
    rng = rng or random.Random()
    out = [copy.copy(q) for q in _ordered(questions)]
    before_seq = single_correct_position_sequence(out)
    before_dist = position_distribution(before_seq)
    single_before = detect_single_correct_position_pattern(out)
    multi_before = detect_multiple_correct_set_pattern(out)
    reordered: List[int] = []
    skipped: List[Dict[str, Any]] = []

    pattern_detected = bool(single_before.get("detected") or multi_before.get("detected"))
    pattern_type = None
    if single_before.get("detected"):
        pattern_type = single_before.get("pattern_type")
    if multi_before.get("detected"):
        extra = multi_before.get("pattern_type")
        pattern_type = extra if not pattern_type else f"{pattern_type}+{extra}"

    if pattern_detected:
        if single_before.get("detected"):
            out, r, s = _break_single_patterns(out)
            reordered.extend(r)
            skipped.extend(s)
        if detect_multiple_correct_set_pattern(out).get("detected"):
            out, r, s = _break_multiple_patterns(out)
            reordered.extend(r)
            skipped.extend(s)

    out, r_bal, s_bal = _balance_single_correct_positions(out, rng)
    reordered.extend(r_bal)
    skipped.extend(s_bal)

    if detect_single_correct_position_pattern(out).get("detected"):
        out, r, s = _break_single_patterns(out)
        reordered.extend(r)
        skipped.extend(s)
    if detect_multiple_correct_set_pattern(out).get("detected"):
        out, r, s = _break_multiple_patterns(out)
        reordered.extend(r)
        skipped.extend(s)

    single_after = detect_single_correct_position_pattern(out)
    multi_after = detect_multiple_correct_set_pattern(out)
    still = bool(single_after.get("detected") or multi_after.get("detected"))
    after_seq = single_correct_position_sequence(out)
    after_dist = position_distribution(after_seq)
    diag = {
        "single_sequence_before": single_before.get("sequence") or [],
        "multiple_sequence_before": multi_before.get("sequence") or [],
        "pattern_detected": bool(pattern_detected),
        "pattern_type": pattern_type if pattern_detected else None,
        "questions_safely_reordered": sorted(set(reordered)),
        "questions_skipped_unsafe": skipped,
        "single_sequence_after": single_after.get("sequence") or [],
        "multiple_sequence_after": multi_after.get("sequence") or [],
        "pattern_remaining": still,
        "accepted_count": len(out),
        "answer_position_before": before_seq,
        "answer_position_after": after_seq,
        "distribution_before": before_dist,
        "distribution_after": after_dist,
        "position_balance_applied": bool(r_bal),
    }
    return out, diag


def _break_single_patterns(
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[int], List[Dict[str, Any]]]:
    reordered: List[int] = []
    skipped: List[Dict[str, Any]] = []
    out = questions
    seen_skip: set = set()

    def note_skip(qn: int, reason: str) -> None:
        key = (qn, reason)
        if key in seen_skip:
            return
        seen_skip.add(key)
        skipped.append({"question_number": qn, "reason": reason})

    for _ in range(len(out) + 2):
        if not detect_single_correct_position_pattern(out).get("detected"):
            break
        progressed = False
        for q in reversed(out):
            if _atype(q) != "single_correct":
                continue
            qn = int(q.get("question_number") or 0)
            ok, reason = can_safely_reorder_options(q)
            if not ok:
                note_skip(qn, reason)
                continue
            cur = _indices(q)[0]
            best = None
            for dest in range(N_OPTIONS):
                if dest == cur:
                    continue
                updated, err = apply_index_permutation(q, _swap_perm(cur, dest))
                if not updated:
                    if err:
                        note_skip(qn, err)
                    continue
                trial = [updated if x is q else x for x in out]
                if not detect_single_correct_position_pattern(trial).get("detected"):
                    best = updated
                    break
                if best is None:
                    best = updated
            if best is None:
                continue
            out[out.index(q)] = best
            reordered.append(qn)
            progressed = True
            break
        if not progressed:
            break
    return out, reordered, skipped


def _break_multiple_patterns(
    questions: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[int], List[Dict[str, Any]]]:
    reordered: List[int] = []
    skipped: List[Dict[str, Any]] = []
    out = questions
    for _ in range(len(out) + 1):
        det = detect_multiple_correct_set_pattern(out)
        if not det.get("detected"):
            break
        progressed = False
        for q in reversed(out):
            if _atype(q) != "multiple_correct":
                continue
            qn = int(q.get("question_number") or 0)
            ok, reason = can_safely_reorder_options(q)
            if not ok:
                skipped.append({"question_number": qn, "reason": reason})
                continue
            for k in (1, 2, 3, 4):
                updated, err = apply_index_permutation(q, _rotate_perm(k))
                if not updated:
                    if err:
                        skipped.append({"question_number": qn, "reason": err})
                    continue
                trial = [updated if x is q else x for x in out]
                if not detect_multiple_correct_set_pattern(trial).get("detected"):
                    out[out.index(q)] = updated
                    reordered.append(qn)
                    progressed = True
                    break
            if progressed:
                break
        if not progressed:
            break
    return out, reordered, skipped
