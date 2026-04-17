# engine/routes/users.py
from flask import Blueprint, request, jsonify
from engine.db import db

users_bp = Blueprint('engine_users', __name__)


@users_bp.route('/engine/users/initialize', methods=['POST'])
def initialize_user():
    """
    Called immediately after a new user registers.
    Seeds the first topic as 'unlocked' and the first non-bonus subtopic
    of that topic as 'unlocked'. Everything else stays absent (treated
    as locked) until the unlock chain reaches it through gameplay.
    """
    user_id = request.get_json()['user_id']

    first_topic = db.fetch_one("""
        SELECT topic_id FROM topic ORDER BY display_order ASC LIMIT 1
    """)
    if not first_topic:
        return jsonify(error='No topics configured'), 500

    db.execute("""
        INSERT INTO user_topic_score (user_id, topic_id, total_score, status)
        VALUES (:uid, :tid, 0, 'unlocked')
        ON DUPLICATE KEY UPDATE status = IF(status = 'locked', 'unlocked', status)
    """, uid=user_id, tid=first_topic.topic_id)

    first_sub = db.fetch_one("""
        SELECT subtopic_id FROM subtopic
         WHERE topic_id = :tid AND is_bonus = FALSE
         ORDER BY display_order ASC LIMIT 1
    """, tid=first_topic.topic_id)
    if not first_sub:
        return jsonify(error='No subtopics configured for first topic'), 500

    db.execute("""
        INSERT INTO user_subtopic_progress (user_id, subtopic_id, status)
        VALUES (:uid, :sid, 'unlocked')
        ON DUPLICATE KEY UPDATE status = IF(status = 'locked', 'unlocked', status)
    """, uid=user_id, sid=first_sub.subtopic_id)

    return jsonify(
        initialized     = True,
        first_topic_id  = first_topic.topic_id,
        first_subtopic_id = first_sub.subtopic_id,
    ), 201
