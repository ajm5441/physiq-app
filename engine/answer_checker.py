# engine/answer_checker.py
import re
import math
from typing import Any

NUMERIC_RELATIVE_TOLERANCE = 0.02
NUMERIC_ABSOLUTE_TOLERANCE = 0.01


def check_answer(submitted: Any, correct_answer: str, question_type: str) -> bool:
    if question_type == 'multiple_choice':
        return _check_multiple_choice(submitted, correct_answer)
    elif question_type == 'numeric':
        return _check_numeric(submitted, correct_answer)
    elif question_type == 'free_response':
        return _check_free_response(submitted, correct_answer)
    raise ValueError(f'Unknown question_type: {question_type}')


def _check_multiple_choice(submitted: Any, correct_answer: str) -> bool:
    return str(submitted).strip().upper() == correct_answer.strip().upper()


def _check_numeric(submitted: Any, correct_answer: str) -> bool:
    try:
        submitted_val = _parse_numeric(submitted)
    except (ValueError, TypeError):
        return False

    if '|' in str(correct_answer):
        correct_str, tol_str = correct_answer.split('|', 1)
        return math.isclose(
            submitted_val, float(correct_str.strip()),
            rel_tol=0, abs_tol=float(tol_str.strip()),
        )

    return math.isclose(
        submitted_val, float(correct_answer.strip()),
        rel_tol=NUMERIC_RELATIVE_TOLERANCE,
        abs_tol=NUMERIC_ABSOLUTE_TOLERANCE,
    )


def _parse_numeric(value: Any) -> float:
    # Strip trailing unit strings (e.g. "9.81 m/s²" → "9.81")
    cleaned = re.sub(r'[a-zA-Z°²³/\s]+$', '', str(value).strip())
    cleaned = cleaned.replace(',', '')
    return float(cleaned)


def _check_free_response(submitted: Any, correct_answer: str) -> bool:
    """
    correct_answer is pipe-separated required keywords, e.g. 'force|mass|acceleration'.
    All keywords must appear in the student's response (case-insensitive).
    """
    keywords = [kw.strip().lower() for kw in correct_answer.split('|') if kw.strip()]
    if not keywords:
        return False
    normalised = re.sub(r'[^\w\s]', '', str(submitted).lower())
    words = set(normalised.split())
    return all(kw in words for kw in keywords)
