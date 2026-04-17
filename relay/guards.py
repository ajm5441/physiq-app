# relay/guards.py
from relay.db import db


def assert_subtopic_accessible(user_id: int, subtopic_id: int) -> bool:
    """
    Returns True if the subtopic is unlocked, passed, or skipped for this user.
    Passed and skipped subtopics can be re-attempted for score improvement.
    Returns False if locked or not yet seeded in user_subtopic_progress.
    """
    row = db.fetch_one("""
        SELECT status FROM user_subtopic_progress
         WHERE user_id = :uid AND subtopic_id = :sid
    """, uid=user_id, sid=subtopic_id)

    return bool(row and row.status in ('unlocked', 'passed', 'skipped'))
