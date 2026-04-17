# relay/routes/sessions.py
from flask import Blueprint, request, jsonify, g
from relay.auth import jwt_required
from relay.cache import session_cache
from relay.engine_client import engine_post
from relay.db import db
from relay.guards import assert_subtopic_accessible

sessions_bp = Blueprint('sessions', __name__)


# ── Start session ─────────────────────────────────────────────────────────────

@sessions_bp.route('/sessions/start', methods=['POST'])
@jwt_required
def start_session():
    user_id     = g.user_id
    body        = request.get_json() or {}
    subtopic_id = body.get('subtopic_id')

    if not subtopic_id:
        return jsonify(error='subtopic_id required'), 400

    if not assert_subtopic_accessible(user_id, subtopic_id):
        return jsonify(error='Subtopic is locked or does not exist'), 403

    existing = session_cache.get_active(user_id)
    if existing:
        return jsonify(
            error='An active session already exists',
            session_id=existing['session_id'],
        ), 409

    session_id = db.execute_returning("""
        INSERT INTO session (user_id, subtopic_id, started_at)
        VALUES (:uid, :sid, NOW())
    """, uid=user_id, sid=subtopic_id)

    plan = engine_post('/engine/sessions/build', {
        'user_id':     user_id,
        'session_id':  session_id,
        'subtopic_id': subtopic_id,
    })

    session_cache.set(user_id, {
        'session_id':           session_id,
        'subtopic_id':          subtopic_id,
        'next_subtopic_id':     plan['next_subtopic_id'],
        'pools': {
            '1': plan['subtopic_pool']['1'],
            '2': plan['subtopic_pool']['2'],
            '3': plan['subtopic_pool']['3'],
            '4': plan['subtopic_pool']['4'],
        },
        'next_pools':           plan['next_subtopic_pool'],
        'review_questions':     plan['review_questions'],
        'review_subtopic_ids':  plan['review_subtopic_ids'],
        'reviews_served':       0,
        'questions_used':       0,
        'tier_correct':         {'1': 0, '2': 0, '3': 0, '4': 0},
        'current_tier':         1,
        'hint_pending':         False,
        'pending_question':     None,
        'skip_phase':           False,
        'skip_tier3_done':      False,
        'skip_tier4_done':      False,
        'current_question':     None,
    })

    first_q = _get_next_question(session_cache.get_active(user_id))
    state   = session_cache.get_active(user_id)
    state['current_question'] = first_q
    session_cache.set(user_id, state)

    return jsonify(
        session_id         = session_id,
        question           = _format_question(first_q),
        questions_remaining= 12,
        current_tier       = 1,
    ), 201


# ── Submit answer ─────────────────────────────────────────────────────────────

@sessions_bp.route('/sessions/<int:session_id>/answer', methods=['POST'])
@jwt_required
def submit_answer(session_id):
    user_id = g.user_id
    body    = request.get_json() or {}
    answer  = body.get('answer')

    state = session_cache.get_active(user_id)
    if not state or state['session_id'] != session_id:
        return jsonify(error='No active session found'), 404

    if state['hint_pending']:
        question      = state['pending_question']
        is_hint_retry = True
    else:
        question      = state['current_question']
        is_hint_retry = False

    result = engine_post('/engine/sessions/evaluate', {
        'session_id':    session_id,
        'question_id':   question['question_id'],
        'tier':          question['tier'],
        'is_review':     question['is_review'],
        'answer':        answer,
        'is_hint_retry': is_hint_retry,
        'user_id':       user_id,
    })

    correct = result['correct']

    # ── First-attempt wrong: serve hint, hold question, do NOT resolve ────────
    if not is_hint_retry and not correct:
        state['hint_pending']     = True
        state['pending_question'] = question
        session_cache.set(user_id, state)
        return jsonify(
            correct             = False,
            hint                = result['hint_text'],
            hint_retry          = True,
            questions_remaining = 12 - state['questions_used'],
            current_tier        = state['current_tier'],
        ), 200

    # ── Resolving cases (A: first-try correct, B: hint-retry correct,
    #                      C: hint-retry wrong) ──────────────────────────────
    state['questions_used'] += 1

    if correct:
        if state['skip_phase']:
            _update_skip_phase(state)
        else:
            _update_tier_state(state, question['tier'])

    state['hint_pending']     = False
    state['pending_question'] = None

    # Enter skip phase once Tier IV hits 2 correct
    if (not state['skip_phase']
            and state['tier_correct'].get('4', 0) >= 2
            and state['next_subtopic_id'] is not None
            and state['next_pools'] is not None):
        state['skip_phase'] = True

    session_over, outcome = _check_terminal(state)

    if session_over:
        session_cache.clear(user_id)
        engine_post('/engine/sessions/close', {
            'session_id':          session_id,
            'user_id':             user_id,
            'subtopic_id':         state['subtopic_id'],
            'outcome':             outcome,
            'questions_used':      state['questions_used'],
            'tier_correct':        state['tier_correct'],
            'review_subtopic_ids': state['review_subtopic_ids'],
        }, async_=True)
        return jsonify(correct=correct, session_complete=True, outcome=outcome), 200

    # Advance to next question
    next_q = _get_next_question(state)
    state['current_question'] = next_q
    session_cache.set(user_id, state)

    return jsonify(
        correct             = correct,
        session_complete    = False,
        next_question       = _format_question(next_q),
        questions_remaining = 12 - state['questions_used'],
        current_tier        = state['current_tier'],
    ), 200


# ── Force close (abandoned / timeout) ────────────────────────────────────────

@sessions_bp.route('/sessions/<int:session_id>/close', methods=['POST'])
@jwt_required
def close_session(session_id):
    user_id = g.user_id
    state   = session_cache.get_active(user_id)

    if state and state['session_id'] == session_id:
        session_cache.clear(user_id)
        engine_post('/engine/sessions/close', {
            'session_id':          session_id,
            'user_id':             user_id,
            'subtopic_id':         state['subtopic_id'],
            'outcome':             'incomplete',
            'questions_used':      state['questions_used'],
            'tier_correct':        state['tier_correct'],
            'review_subtopic_ids': state.get('review_subtopic_ids', []),
        }, async_=True)

    return jsonify(message='Session closed'), 200


# ── Get session state ─────────────────────────────────────────────────────────

@sessions_bp.route('/sessions/<int:session_id>', methods=['GET'])
@jwt_required
def get_session(session_id):
    user_id = g.user_id
    state   = session_cache.get_active(user_id)

    if not state or state['session_id'] != session_id:
        return jsonify(error='Session not found'), 404

    return jsonify(
        session_id          = session_id,
        questions_remaining = 12 - state['questions_used'],
        current_tier        = state['current_tier'],
        tier_correct        = state['tier_correct'],
        skip_phase          = state['skip_phase'],
    ), 200


# ── Session state helpers ─────────────────────────────────────────────────────

def _get_next_question(state: dict) -> dict | None:
    used  = state['questions_used']
    tier  = str(state['current_tier'])

    if state['skip_phase']:
        return _get_skip_phase_question(state)

    # Inject review questions at positions 3 and 8 (after 3rd and 8th slot used)
    reviews_due = (
        state['reviews_served'] < 2 and (
            (state['reviews_served'] == 0 and used == 3) or
            (state['reviews_served'] == 1 and used == 8)
        )
    )
    if reviews_due:
        idx = state['reviews_served']
        state['reviews_served'] += 1
        q = state['review_questions'][idx]
        q['is_review'] = True
        return q

    pool = state['pools'].get(tier, [])
    if not pool:
        return None

    q = pool.pop(0)
    q['is_review'] = False
    return q


def _get_skip_phase_question(state: dict) -> dict | None:
    next_pools = state.get('next_pools')
    if not next_pools:
        return None

    if not state['skip_tier3_done']:
        pool = next_pools.get('3', [])
        if not pool:
            return None
        q = pool.pop(0)
        q['is_review'] = False
        return q

    if not state['skip_tier4_done']:
        pool = next_pools.get('4', [])
        if not pool:
            return None
        q = pool.pop(0)
        q['is_review'] = False
        return q

    return None


def _update_tier_state(state: dict, tier: int):
    t = str(tier)
    ct = str(state['current_tier'])
    if t == ct:
        state['tier_correct'][t] = state['tier_correct'].get(t, 0) + 1
        if state['tier_correct'][t] >= 2 and state['current_tier'] < 4:
            state['current_tier'] += 1


def _update_skip_phase(state: dict):
    if not state['skip_tier3_done']:
        state['skip_tier3_done'] = True
    elif not state['skip_tier4_done']:
        state['skip_tier4_done'] = True


def _check_terminal(state: dict):
    tc   = state['tier_correct']
    used = state['questions_used']

    if state['skip_phase']:
        if state['skip_tier4_done']:
            return True, 'skip_granted'
        if used >= 12:
            return True, 'pass'   # at minimum T3 x2 was already met
        next_pools = state.get('next_pools') or {}
        if not next_pools.get('3') and not state['skip_tier3_done']:
            return True, 'pass'
        if not next_pools.get('4') and state['skip_tier3_done']:
            return True, 'pass'
        return False, None

    t3 = tc.get('3', 0)
    t4 = tc.get('4', 0)

    # T3 passed — keep going for skip attempt unless limit hit or no T4 pool
    if t3 >= 2 and used < 12 and t4 < 2:
        pool4 = state['pools'].get('4', [])
        if pool4 or t4 > 0:
            return False, None
        return True, 'pass'

    if t3 >= 2 and t4 >= 2:
        # Will have entered skip_phase already — shouldn't reach here
        return True, 'pass'

    if used >= 12:
        return True, 'pass' if t3 >= 2 else 'fail'

    if _get_next_question(state) is None and not state['hint_pending']:
        return True, 'pass' if t3 >= 2 else 'fail'

    return False, None


def _format_question(q: dict) -> dict:
    if q is None:
        return None
    return {
        'question_id': q['question_id'],
        'tier':        q['tier'],
        'is_review':   q.get('is_review', False),
        'prompt':      q['prompt'],
        'type':        q['question_type'],
        'options':     q.get('options'),
    }
