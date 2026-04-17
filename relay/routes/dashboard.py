# relay/routes/dashboard.py
from flask import Blueprint, jsonify, g
from relay.auth import jwt_required
from relay.db import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard', methods=['GET'])
@jwt_required
def get_dashboard():
    uid = g.user_id

    # ── Aggregate stats ───────────────────────────────────────────────────────
    stats = db.fetch_one("""
        SELECT
            COALESCE(SUM(uts.total_score), 0)                         AS overall_score,
            COUNT(CASE WHEN usp.status = 'passed'  THEN 1 END)        AS subtopics_passed,
            COUNT(CASE WHEN usp.status = 'skipped' THEN 1 END)        AS subtopics_skipped,
            COUNT(CASE WHEN uts.bonus_unlocked = TRUE THEN 1 END)      AS bonus_unlocked,
            ROUND(AVG(CASE WHEN s.outcome IN ('pass','skip_granted')
                           THEN s.score END), 0)                       AS avg_session_score
        FROM user u
        LEFT JOIN user_topic_score      uts ON uts.user_id = u.user_id
        LEFT JOIN user_subtopic_progress usp ON usp.user_id = u.user_id
        LEFT JOIN session               s   ON s.user_id   = u.user_id
        WHERE u.user_id = :uid
    """, uid=uid)

    # ── Per-topic cards ───────────────────────────────────────────────────────
    topics = db.fetch_all("""
        SELECT
            t.topic_id, t.name, t.bonus_score_threshold,
            COALESCE(uts.total_score, 0)       AS total_score,
            COALESCE(uts.status, 'locked')     AS status,
            COALESCE(uts.bonus_unlocked, 0)    AS bonus_unlocked,
            COALESCE(uts.bonus_completed, 0)   AS bonus_completed,
            COUNT(CASE WHEN s.is_bonus = FALSE THEN 1 END) AS subtopics_total,
            COUNT(CASE WHEN usp.status IN ('passed','skipped')
                        AND s2.is_bonus = FALSE THEN 1 END) AS subtopics_passed
        FROM topic t
        LEFT JOIN user_topic_score       uts ON uts.topic_id = t.topic_id
                                             AND uts.user_id  = :uid
        LEFT JOIN subtopic               s   ON s.topic_id   = t.topic_id
        LEFT JOIN subtopic               s2  ON s2.topic_id  = t.topic_id
        LEFT JOIN user_subtopic_progress usp ON usp.subtopic_id = s2.subtopic_id
                                             AND usp.user_id     = :uid
        GROUP BY t.topic_id, t.name, t.bonus_score_threshold,
                 uts.total_score, uts.status, uts.bonus_unlocked, uts.bonus_completed
        ORDER BY t.display_order
    """, uid=uid)

    # ── Strong and weak areas (top/bottom 4 by best_score) ───────────────────
    strong = db.fetch_all("""
        SELECT usp.subtopic_id, s.name, usp.best_score
          FROM user_subtopic_progress usp
          JOIN subtopic s ON s.subtopic_id = usp.subtopic_id
         WHERE usp.user_id = :uid
           AND usp.status IN ('passed','skipped')
           AND s.is_bonus  = FALSE
         ORDER BY usp.best_score DESC
         LIMIT 4
    """, uid=uid)

    weak = db.fetch_all("""
        SELECT usp.subtopic_id, s.name, usp.best_score
          FROM user_subtopic_progress usp
          JOIN subtopic s ON s.subtopic_id = usp.subtopic_id
         WHERE usp.user_id = :uid
           AND usp.status IN ('passed','skipped')
           AND s.is_bonus  = FALSE
         ORDER BY usp.best_score ASC
         LIMIT 4
    """, uid=uid)

    # ── Next recommended subtopic (lowest display_order that is unlocked) ─────
    next_sub = db.fetch_one("""
        SELECT usp.subtopic_id, s.name
          FROM user_subtopic_progress usp
          JOIN subtopic s ON s.subtopic_id = usp.subtopic_id
         WHERE usp.user_id = :uid
           AND usp.status  = 'unlocked'
           AND s.is_bonus  = FALSE
         ORDER BY s.display_order ASC
         LIMIT 1
    """, uid=uid)

    return jsonify(
        overall_score     = int(stats.overall_score or 0),
        subtopics_passed  = int(stats.subtopics_passed or 0),
        subtopics_skipped = int(stats.subtopics_skipped or 0),
        bonus_unlocked    = int(stats.bonus_unlocked or 0),
        avg_session_score = int(stats.avg_session_score or 0),
        topics            = [dict(t._mapping) for t in topics],
        strong_areas      = [dict(r._mapping) for r in strong],
        weak_areas        = [dict(r._mapping) for r in weak],
        next_subtopic     = dict(next_sub._mapping) if next_sub else None,
    ), 200


@dashboard_bp.route('/dashboard/topics', methods=['GET'])
@jwt_required
def get_topic_scores():
    uid    = g.user_id
    topics = db.fetch_all("""
        SELECT t.topic_id, t.name,
               COALESCE(uts.total_score, 0)    AS total_score,
               COALESCE(uts.status, 'locked')  AS status
          FROM topic t
          LEFT JOIN user_topic_score uts
                 ON uts.topic_id = t.topic_id AND uts.user_id = :uid
         ORDER BY t.display_order
    """, uid=uid)
    return jsonify(topics=[dict(t._mapping) for t in topics]), 200
