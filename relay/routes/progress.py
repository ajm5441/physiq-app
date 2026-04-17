# relay/routes/progress.py
from flask import Blueprint, jsonify, g
from relay.auth import jwt_required
from relay.db import db

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/progress/subtopics', methods=['GET'])
@jwt_required
def subtopic_progress():
    uid  = g.user_id
    rows = db.fetch_all("""
        SELECT
            usp.subtopic_id, s.name, s.topic_id,
            usp.status, usp.best_score, usp.attempts,
            usp.skipped, usp.passed_at
        FROM user_subtopic_progress usp
        JOIN subtopic s ON s.subtopic_id = usp.subtopic_id
        WHERE usp.user_id = :uid
        ORDER BY s.topic_id, s.display_order
    """, uid=uid)
    return jsonify([dict(r._mapping) for r in rows]), 200


@progress_bp.route('/progress/review-history', methods=['GET'])
@jwt_required
def review_history():
    uid  = g.user_id
    rows = db.fetch_all("""
        SELECT
            rp.subtopic_id, s.name,
            rp.correct_count, rp.incorrect_count,
            rp.last_reviewed_at, rp.sessions_since_last_review,
            usp.best_score,
            usp.status,
            usp.skipped
        FROM review_performance rp
        JOIN subtopic                s   ON s.subtopic_id   = rp.subtopic_id
        JOIN user_subtopic_progress  usp ON usp.subtopic_id = rp.subtopic_id
                                        AND usp.user_id     = :uid
        WHERE rp.user_id = :uid
        ORDER BY (
            (50 - LEAST(usp.best_score, 50))
            + LEAST(rp.sessions_since_last_review * 4
                    - rp.correct_count * 6
                    + rp.incorrect_count * 3, 30)
            + CASE WHEN usp.skipped = TRUE
                    AND rp.correct_count < 3
                   THEN 25 ELSE 0 END
        ) DESC
    """, uid=uid)
    return jsonify([dict(r._mapping) for r in rows]), 200
