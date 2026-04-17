# engine/routes/progress.py
from flask import Blueprint, request, jsonify
from engine.db import db

progress_bp = Blueprint('engine_progress', __name__)


@progress_bp.route('/engine/progress/unlock', methods=['POST'])
def unlock():
    body = request.get_json()
    process_unlocks(body['user_id'], body['subtopic_id'], body['outcome'])
    return jsonify(ok=True), 200


@progress_bp.route('/engine/progress/update-score', methods=['POST'])
def update_score():
    body = request.get_json()
    uid  = body['user_id']
    tid  = body['topic_id']
    sid  = body['subtopic_id']
    sc   = body['score']

    new_total = db.fetch_scalar("""
        SELECT COALESCE(SUM(usp.best_score), 0)
          FROM user_subtopic_progress usp
          JOIN subtopic s ON s.subtopic_id = usp.subtopic_id
         WHERE usp.user_id = :uid AND s.topic_id = :tid AND s.is_bonus = FALSE
    """, uid=uid, tid=tid)

    db.execute("""
        INSERT INTO user_topic_score (user_id, topic_id, total_score, status)
        VALUES (:uid, :tid, :total, 'locked')
        ON DUPLICATE KEY UPDATE total_score = :total
    """, uid=uid, tid=tid, total=new_total)

    _check_bonus_unlock(uid, tid)
    return jsonify(total_score=new_total), 200


# ── Core unlock logic (called directly by sessions.py close route) ────────────

def process_unlocks(user_id: int, completed_subtopic_id: int, outcome: str):
    subtopic = db.fetch_one("""
        SELECT topic_id, is_bonus FROM subtopic WHERE subtopic_id = :sid
    """, sid=completed_subtopic_id)

    # ── Bonus path — entirely separate, never touches the main chain ──────────
    if subtopic.is_bonus:
        if outcome == 'pass':
            _finalize_bonus(user_id, subtopic.topic_id, completed_subtopic_id)
        return

    # ── Mark current subtopic passed ──────────────────────────────────────────
    db.execute("""
        UPDATE user_subtopic_progress
           SET status = 'passed', passed_at = NOW()
         WHERE user_id = :uid AND subtopic_id = :sid
    """, uid=user_id, sid=completed_subtopic_id)

    # Fetch all non-bonus siblings ordered by display_order
    siblings = db.fetch_all("""
        SELECT subtopic_id, display_order
          FROM subtopic
         WHERE topic_id = :tid AND is_bonus = FALSE
         ORDER BY display_order ASC
    """, tid=subtopic.topic_id)

    current_index = next(
        (i for i, s in enumerate(siblings)
         if s.subtopic_id == completed_subtopic_id),
        None,
    )
    if current_index is None:
        return

    if outcome == 'pass':
        _unlock_next(user_id, siblings, current_index,
                     count=1, mark_first_skipped=False)

    elif outcome == 'skip_granted':
        # Mark the immediately next subtopic 'skipped' and unlock the one after
        _unlock_next(user_id, siblings, current_index,
                     count=2, mark_first_skipped=True)

    _check_topic_completion(user_id, subtopic.topic_id, siblings)
    _check_bonus_unlock(user_id, subtopic.topic_id)


def _unlock_next(user_id: int, siblings: list, current_index: int,
                 count: int, mark_first_skipped: bool):
    for offset in range(1, count + 1):
        next_index = current_index + offset
        if next_index >= len(siblings):
            break

        next_sid   = siblings[next_index].subtopic_id
        is_skipped = mark_first_skipped and offset == 1
        new_status = 'skipped' if is_skipped else 'unlocked'

        db.execute("""
            INSERT INTO user_subtopic_progress
                (user_id, subtopic_id, status, skipped, passed_at)
            VALUES
                (:uid, :sid, :status, :skipped,
                 IF(:skipped, NOW(), NULL))
            ON DUPLICATE KEY UPDATE
                status    = IF(status = 'locked', :status, status),
                skipped   = IF(status = 'locked', :skipped, skipped),
                passed_at = IF(status = 'locked' AND :skipped, NOW(), passed_at)
        """, uid=user_id, sid=next_sid,
             status=new_status, skipped=is_skipped)


def _check_topic_completion(user_id: int, topic_id: int, non_bonus_siblings: list):
    sids = tuple(s.subtopic_id for s in non_bonus_siblings)
    if not sids:
        return

    done_count = db.fetch_scalar("""
        SELECT COUNT(*) FROM user_subtopic_progress
         WHERE user_id     = :uid
           AND subtopic_id IN :sids
           AND status      IN ('passed','skipped')
    """, uid=user_id, sids=sids)

    if done_count < len(sids):
        return

    # Mark topic completed
    db.execute("""
        UPDATE user_topic_score SET status = 'completed'
         WHERE user_id = :uid AND topic_id = :tid
    """, uid=user_id, tid=topic_id)

    # Find and unlock the next topic
    next_topic = db.fetch_one("""
        SELECT topic_id FROM topic
         WHERE display_order > (
               SELECT display_order FROM topic WHERE topic_id = :tid
         )
         ORDER BY display_order ASC LIMIT 1
    """, tid=topic_id)

    if not next_topic:
        return  # Course complete

    db.execute("""
        INSERT INTO user_topic_score (user_id, topic_id, total_score, status)
        VALUES (:uid, :tid, 0, 'unlocked')
        ON DUPLICATE KEY UPDATE
            status = IF(status = 'locked', 'unlocked', status)
    """, uid=user_id, tid=next_topic.topic_id)

    # Unlock first non-bonus subtopic of the new topic
    first_sub = db.fetch_one("""
        SELECT subtopic_id FROM subtopic
         WHERE topic_id = :tid AND is_bonus = FALSE
         ORDER BY display_order ASC LIMIT 1
    """, tid=next_topic.topic_id)

    if first_sub:
        db.execute("""
            INSERT INTO user_subtopic_progress (user_id, subtopic_id, status)
            VALUES (:uid, :sid, 'unlocked')
            ON DUPLICATE KEY UPDATE
                status = IF(status = 'locked', 'unlocked', status)
        """, uid=user_id, sid=first_sub.subtopic_id)


def _check_bonus_unlock(user_id: int, topic_id: int):
    row = db.fetch_one("""
        SELECT uts.total_score,
               uts.bonus_unlocked,
               t.bonus_score_threshold,
               s.subtopic_id AS bonus_subtopic_id
          FROM user_topic_score uts
          JOIN topic    t ON t.topic_id   = uts.topic_id
          JOIN subtopic s ON s.topic_id   = t.topic_id
                          AND s.is_bonus  = TRUE
         WHERE uts.user_id  = :uid
           AND uts.topic_id = :tid
         LIMIT 1
    """, uid=user_id, tid=topic_id)

    if not row or row.bonus_unlocked:
        return

    if row.total_score < row.bonus_score_threshold:
        return

    db.execute("""
        UPDATE user_topic_score
           SET bonus_unlocked = TRUE, bonus_unlocked_at = NOW()
         WHERE user_id = :uid AND topic_id = :tid
    """, uid=user_id, tid=topic_id)

    db.execute("""
        INSERT INTO user_subtopic_progress (user_id, subtopic_id, status)
        VALUES (:uid, :sid, 'unlocked')
        ON DUPLICATE KEY UPDATE
            status = IF(status = 'locked', 'unlocked', status)
    """, uid=user_id, sid=row.bonus_subtopic_id)


def _finalize_bonus(user_id: int, topic_id: int, bonus_subtopic_id: int):
    session_score = db.fetch_scalar("""
        SELECT score FROM session
         WHERE user_id     = :uid
           AND subtopic_id = :sid
           AND outcome     = 'pass'
         ORDER BY completed_at DESC LIMIT 1
    """, uid=user_id, sid=bonus_subtopic_id) or 0

    db.execute("""
        UPDATE user_subtopic_progress
           SET status = 'passed', passed_at = NOW()
         WHERE user_id = :uid AND subtopic_id = :sid
    """, uid=user_id, sid=bonus_subtopic_id)

    db.execute("""
        UPDATE user_topic_score
           SET total_score        = total_score + :score,
               bonus_completed    = TRUE,
               bonus_completed_at = NOW()
         WHERE user_id  = :uid AND topic_id = :tid
    """, uid=user_id, tid=topic_id, score=session_score)

    # Re-check threshold in case the bonus score itself pushes another unlock
    _check_bonus_unlock(user_id, topic_id)
