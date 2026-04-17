# relay/routes/topics.py
from flask import Blueprint, jsonify, g
from relay.auth import jwt_required
from relay.db import db

topics_bp = Blueprint('topics', __name__)


@topics_bp.route('/topics', methods=['GET'])
@jwt_required
def list_topics():
    uid = g.user_id
    rows = db.fetch_all("""
        SELECT
            t.topic_id, t.name, t.display_order,
            t.bonus_score_threshold,
            COALESCE(uts.total_score, 0)        AS total_score,
            COALESCE(uts.status, 'locked')      AS status,
            COALESCE(uts.bonus_unlocked, FALSE)  AS bonus_unlocked,
            COALESCE(uts.bonus_completed, FALSE) AS bonus_completed,
            COUNT(CASE WHEN s.is_bonus = FALSE THEN 1 END) AS subtopics_total,
            COUNT(CASE WHEN usp.status IN ('passed','skipped')
                        AND sub2.is_bonus = FALSE THEN 1 END) AS subtopics_passed
        FROM topic t
        LEFT JOIN user_topic_score       uts  ON uts.topic_id  = t.topic_id
                                              AND uts.user_id   = :uid
        LEFT JOIN subtopic               sub2 ON sub2.topic_id  = t.topic_id
        LEFT JOIN user_subtopic_progress usp  ON usp.subtopic_id = sub2.subtopic_id
                                              AND usp.user_id    = :uid
        LEFT JOIN subtopic               s    ON s.topic_id      = t.topic_id
        GROUP BY t.topic_id, t.name, t.display_order,
                 t.bonus_score_threshold, uts.total_score, uts.status,
                 uts.bonus_unlocked, uts.bonus_completed
        ORDER BY t.display_order
    """, uid=uid)
    return jsonify([dict(r._mapping) for r in rows]), 200


@topics_bp.route('/topics/<int:topic_id>/subtopics', methods=['GET'])
@jwt_required
def list_subtopics(topic_id):
    uid = g.user_id
    rows = db.fetch_all("""
        SELECT
            s.subtopic_id, s.name, s.display_order, s.is_bonus,
            COALESCE(usp.status,     'locked') AS status,
            COALESCE(usp.best_score, 0)        AS best_score,
            COALESCE(usp.attempts,   0)        AS attempts,
            COALESCE(usp.skipped,    FALSE)    AS skipped,
            usp.passed_at
        FROM subtopic s
        LEFT JOIN user_subtopic_progress usp
               ON usp.subtopic_id = s.subtopic_id AND usp.user_id = :uid
        WHERE s.topic_id = :tid
        ORDER BY s.is_bonus ASC, s.display_order ASC
    """, uid=uid, tid=topic_id)
    return jsonify([dict(r._mapping) for r in rows]), 200
