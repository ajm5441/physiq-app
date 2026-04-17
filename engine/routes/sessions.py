# engine/routes/sessions.py
from flask import Blueprint, request, jsonify
from engine.db import db
from engine.answer_checker import check_answer

sessions_bp = Blueprint('engine_sessions', __name__)


# ── Build session ─────────────────────────────────────────────────────────────

@sessions_bp.route('/engine/sessions/build', methods=['POST'])
def build_session():
    body        = request.get_json()
    user_id     = body['user_id']
    session_id  = body['session_id']
    subtopic_id = body['subtopic_id']

    # Maximum questions needed per tier given worst-case session paths:
    #   Tier I:  12  (student could burn all slots here)
    #   Tier II: 10  (at minimum 2 slots used on T1 before reaching T2)
    #   Tier III: 8
    #   Tier IV:  6
    subtopic_pool = {
        '1': _select_questions(subtopic_id, tier=1, limit=12),
        '2': _select_questions(subtopic_id, tier=2, limit=10),
        '3': _select_questions(subtopic_id, tier=3, limit=8),
        '4': _select_questions(subtopic_id, tier=4, limit=6),
    }

    # Next-subtopic probe pool for the skip path (Tier III + IV from next subtopic)
    next_subtopic_id = _get_next_subtopic_id(subtopic_id)
    next_subtopic_pool = None
    if next_subtopic_id:
        next_subtopic_pool = {
            '3': _select_questions(next_subtopic_id, tier=3, limit=3),
            '4': _select_questions(next_subtopic_id, tier=4, limit=3),
        }

    # Two weighted review questions
    review_questions    = _select_review_questions(user_id, subtopic_id)
    review_subtopic_ids = [q['subtopic_id'] for q in review_questions]

    return jsonify(
        subtopic_pool       = subtopic_pool,
        next_subtopic_id    = next_subtopic_id,
        next_subtopic_pool  = next_subtopic_pool,
        review_questions    = review_questions,
        review_subtopic_ids = review_subtopic_ids,
    ), 200


def _select_questions(subtopic_id: int, tier: int, limit: int) -> list[dict]:
    rows = db.fetch_all("""
        SELECT q.question_id, q.subtopic_id, q.tier,
               q.prompt, q.correct_answer, q.hint_text, q.question_type
          FROM question q
         WHERE q.subtopic_id = :sid AND q.tier = :tier
         ORDER BY RAND()
         LIMIT :lim
    """, sid=subtopic_id, tier=tier, lim=limit)

    questions = []
    for r in rows:
        q = dict(r._mapping)
        if q['question_type'] == 'multiple_choice':
            opts = db.fetch_all("""
                SELECT option_key, option_text
                  FROM question_option
                 WHERE question_id = :qid
                 ORDER BY option_key
            """, qid=q['question_id'])
            q['options'] = [{'key': o.option_key, 'text': o.option_text}
                            for o in opts]
        else:
            q['options'] = None
        questions.append(q)

    return questions


def _get_next_subtopic_id(subtopic_id: int) -> int | None:
    row = db.fetch_one("""
        SELECT s2.subtopic_id
          FROM subtopic s1
          JOIN subtopic s2
            ON s2.topic_id      = s1.topic_id
           AND s2.display_order = s1.display_order + 1
           AND s2.is_bonus      = FALSE
         WHERE s1.subtopic_id = :sid
    """, sid=subtopic_id)
    return row.subtopic_id if row else None


def _select_review_questions(user_id: int, current_subtopic_id: int) -> list[dict]:
    """
    Weighted priority query — picks the 2 subtopics most in need of review,
    then selects one random question from each.
    """
    candidates = db.fetch_all("""
        SELECT usp.subtopic_id,
               (50 - LEAST(usp.best_score, 50))
               + LEAST(
                   COALESCE(rp.sessions_since_last_review, 99) * 4
                   - COALESCE(rp.correct_count, 0) * 6
                   + COALESCE(rp.incorrect_count, 0) * 3,
                 30)
               + CASE
                   WHEN usp.skipped = TRUE
                    AND COALESCE(rp.correct_count, 0) < 3
                   THEN 25 ELSE 0
                 END AS priority_score
          FROM user_subtopic_progress usp
          LEFT JOIN review_performance rp
                 ON rp.user_id     = usp.user_id
                AND rp.subtopic_id = usp.subtopic_id
         WHERE usp.user_id     = :uid
           AND usp.status      IN ('passed','skipped')
           AND usp.subtopic_id != :cur
         ORDER BY priority_score DESC
         LIMIT 2
    """, uid=user_id, cur=current_subtopic_id)

    review_questions = []
    for c in candidates:
        row = db.fetch_one("""
            SELECT q.question_id, q.subtopic_id, q.tier,
                   q.prompt, q.correct_answer, q.hint_text, q.question_type
              FROM question q
             WHERE q.subtopic_id = :sid
             ORDER BY RAND()
             LIMIT 1
        """, sid=c.subtopic_id)
        if row:
            q = dict(row._mapping)
            if q['question_type'] == 'multiple_choice':
                opts = db.fetch_all("""
                    SELECT option_key, option_text
                      FROM question_option
                     WHERE question_id = :qid
                     ORDER BY option_key
                """, qid=q['question_id'])
                q['options'] = [{'key': o.option_key, 'text': o.option_text}
                                for o in opts]
            else:
                q['options'] = None
            review_questions.append(q)

    return review_questions


# ── Evaluate answer ───────────────────────────────────────────────────────────

@sessions_bp.route('/engine/sessions/<int:session_id>/evaluate', methods=['POST'])
def evaluate_answer(session_id):
    body     = request.get_json()
    question = db.fetch_one("""
        SELECT question_id, correct_answer, hint_text, question_type
          FROM question WHERE question_id = :qid
    """, qid=body['question_id'])

    correct       = check_answer(body['answer'], question.correct_answer,
                                 question.question_type)
    is_hint_retry = body['is_hint_retry']

    # A question is "resolving" when it is either answered correctly on any
    # attempt, or it is a hint retry (correct or not — the question is done).
    # The only non-resolving case is a first-attempt wrong answer.
    is_resolving = correct or is_hint_retry

    db.execute("""
        INSERT INTO question_attempt
            (session_id, question_id, tier, is_correct, hint_used,
             counts_toward_limit, attempt_number, attempted_at)
        VALUES
            (:sid, :qid, :tier, :correct, :hint_used,
             :counts, :attempt_num, NOW())
    """,
        sid        = session_id,
        qid        = body['question_id'],
        tier       = body['tier'],
        correct    = correct,
        hint_used  = is_hint_retry,
        counts     = is_resolving,
        attempt_num= 2 if is_hint_retry else 1,
    )

    # Only return hint_text on a first-attempt wrong — the hint was
    # already shown if this is a retry
    hint_text = (question.hint_text
                 if not correct and not is_hint_retry
                 else None)

    return jsonify(correct=correct, hint_text=hint_text), 200


# ── Close session ─────────────────────────────────────────────────────────────

@sessions_bp.route('/engine/sessions/<int:session_id>/close', methods=['POST'])
def close_session(session_id):
    body       = request.get_json()
    user_id    = body['user_id']
    subtopic_id= body['subtopic_id']
    outcome    = body['outcome']

    score = _compute_score(
        tier_correct   = body['tier_correct'],
        questions_used = body['questions_used'],
        outcome        = outcome,
    )

    db.execute("""
        UPDATE session
           SET completed_at   = NOW(),
               questions_used = :used,
               score          = :score,
               outcome        = :outcome
         WHERE session_id = :sid
    """, sid=session_id, used=body['questions_used'],
         score=score, outcome=outcome)

    subtopic = db.fetch_one("""
        SELECT topic_id, is_bonus FROM subtopic WHERE subtopic_id = :sid
    """, sid=subtopic_id)

    if not subtopic.is_bonus:
        _update_topic_score(user_id, subtopic.topic_id, subtopic_id, score)

    _update_review_performance(
        user_id, session_id, body.get('review_subtopic_ids', [])
    )

    # Increment attempt counter regardless of outcome
    db.execute("""
        INSERT INTO user_subtopic_progress (user_id, subtopic_id, attempts, status)
        VALUES (:uid, :sid, 1, 'unlocked')
        ON DUPLICATE KEY UPDATE attempts = attempts + 1
    """, uid=user_id, sid=subtopic_id)

    if outcome in ('pass', 'skip_granted'):
        from engine.routes.progress import process_unlocks
        process_unlocks(user_id, subtopic_id, outcome)

    return jsonify(score=score, outcome=outcome), 200


def _compute_score(tier_correct: dict, questions_used: int, outcome: str) -> int:
    """
    Base points:  T1=10, T2=20, T3=40, T4=80 (per correct answer, max 2 each)
    Efficiency bonus: 3 pts per unused question slot
    Outcome multiplier: skip_granted=1.25x, pass=1.0x, anything else=0
    """
    if outcome not in ('pass', 'skip_granted'):
        return 0

    tc   = {str(k): v for k, v in tier_correct.items()}
    base = (min(int(tc.get('1', 0)), 2) * 10 +
            min(int(tc.get('2', 0)), 2) * 20 +
            min(int(tc.get('3', 0)), 2) * 40 +
            min(int(tc.get('4', 0)), 2) * 80)

    efficiency_bonus = max(0, 12 - questions_used) * 3
    multiplier       = 1.25 if outcome == 'skip_granted' else 1.0
    return int((base + efficiency_bonus) * multiplier)


def _update_topic_score(user_id: int, topic_id: int,
                        subtopic_id: int, session_score: int):
    # Update best_score for this subtopic if improved
    db.execute("""
        INSERT INTO user_subtopic_progress (user_id, subtopic_id, best_score, status)
        VALUES (:uid, :sid, :score, 'unlocked')
        ON DUPLICATE KEY UPDATE
            best_score = GREATEST(best_score, :score)
    """, uid=user_id, sid=subtopic_id, score=session_score)

    # Recalculate topic total as sum of all subtopic best scores (non-bonus)
    new_total = db.fetch_scalar("""
        SELECT COALESCE(SUM(usp.best_score), 0)
          FROM user_subtopic_progress usp
          JOIN subtopic s ON s.subtopic_id = usp.subtopic_id
         WHERE usp.user_id = :uid
           AND s.topic_id  = :tid
           AND s.is_bonus  = FALSE
    """, uid=user_id, tid=topic_id)

    db.execute("""
        INSERT INTO user_topic_score (user_id, topic_id, total_score, status)
        VALUES (:uid, :tid, :total, 'locked')
        ON DUPLICATE KEY UPDATE total_score = :total
    """, uid=user_id, tid=topic_id, total=new_total)


def _update_review_performance(user_id: int, session_id: int,
                                selected_subtopic_ids: list):
    """
    For subtopics chosen as review: record correct/incorrect counts and
    reset the drought counter. For all other passed subtopics: increment
    the drought counter so they gradually regain review priority.
    """
    all_passed = db.fetch_all("""
        SELECT subtopic_id FROM user_subtopic_progress
         WHERE user_id = :uid AND status IN ('passed','skipped')
    """, uid=user_id)

    selected_set = set(int(s) for s in selected_subtopic_ids)

    for row in all_passed:
        sid = row.subtopic_id

        if sid in selected_set:
            correct = db.fetch_scalar("""
                SELECT COUNT(*) FROM review_question_log
                 WHERE session_id = :sess
                   AND question_id IN (
                       SELECT question_id FROM question WHERE subtopic_id = :sid
                   )
                   AND is_correct = TRUE
            """, sess=session_id, sid=sid) or 0

            incorrect = db.fetch_scalar("""
                SELECT COUNT(*) FROM review_question_log
                 WHERE session_id = :sess
                   AND question_id IN (
                       SELECT question_id FROM question WHERE subtopic_id = :sid
                   )
                   AND is_correct = FALSE
            """, sess=session_id, sid=sid) or 0

            db.execute("""
                INSERT INTO review_performance
                    (user_id, subtopic_id, correct_count, incorrect_count,
                     last_reviewed_at, sessions_since_last_review)
                VALUES (:uid, :sid, :c, :i, NOW(), 0)
                ON DUPLICATE KEY UPDATE
                    correct_count              = correct_count   + :c,
                    incorrect_count            = incorrect_count + :i,
                    last_reviewed_at           = NOW(),
                    sessions_since_last_review = 0
            """, uid=user_id, sid=sid, c=correct, i=incorrect)
        else:
            db.execute("""
                INSERT INTO review_performance
                    (user_id, subtopic_id, sessions_since_last_review)
                VALUES (:uid, :sid, 1)
                ON DUPLICATE KEY UPDATE
                    sessions_since_last_review = sessions_since_last_review + 1
            """, uid=user_id, sid=sid)
