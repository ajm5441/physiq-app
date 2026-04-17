# engine/routes/questions.py
from flask import Blueprint, request, jsonify
from engine.db import db

questions_bp = Blueprint('engine_questions', __name__)


@questions_bp.route('/engine/questions/select-review', methods=['POST'])
def select_review():
    """
    Standalone endpoint exposing the weighted review selector.
    Called directly if the relay ever needs to refresh review picks
    outside of a full session build.
    """
    body        = request.get_json()
    user_id     = body['user_id']
    subtopic_id = body['subtopic_id']

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
    """, uid=user_id, cur=subtopic_id)

    questions = []
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
            questions.append(q)

    return jsonify(questions=questions), 200


@questions_bp.route('/engine/questions/next', methods=['POST'])
def next_question():
    """
    Given a subtopic and tier, return the next random question.
    Used when the relay needs to fetch an individual question on demand
    rather than from a pre-built pool (e.g. after pool exhaustion recovery).
    """
    body        = request.get_json()
    subtopic_id = body['subtopic_id']
    tier        = body['tier']
    exclude_ids = body.get('exclude_ids', [])

    exclude_clause = ''
    params = dict(sid=subtopic_id, tier=tier)
    if exclude_ids:
        exclude_clause = 'AND q.question_id NOT IN :excl'
        params['excl'] = tuple(exclude_ids)

    row = db.fetch_one(f"""
        SELECT q.question_id, q.subtopic_id, q.tier,
               q.prompt, q.correct_answer, q.hint_text, q.question_type
          FROM question q
         WHERE q.subtopic_id = :sid
           AND q.tier        = :tier
           {exclude_clause}
         ORDER BY RAND()
         LIMIT 1
    """, **params)

    if not row:
        return jsonify(error='No questions available for this tier'), 404

    q = dict(row._mapping)
    if q['question_type'] == 'multiple_choice':
        opts = db.fetch_all("""
            SELECT option_key, option_text FROM question_option
             WHERE question_id = :qid ORDER BY option_key
        """, qid=q['question_id'])
        q['options'] = [{'key': o.option_key, 'text': o.option_text} for o in opts]
    else:
        q['options'] = None

    return jsonify(q), 200
