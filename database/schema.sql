-- ─────────────────────────────────────────────────────────────────────────────
--  PhysIQ · MySQL 8 · Complete Schema
--  Run once against a fresh database:
--    mysql -u root -p physiq < schema.sql
-- ─────────────────────────────────────────────────────────────────────────────

SET FOREIGN_KEY_CHECKS = 0;

-- ── GROUP 1: Course catalog ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS topic (
    topic_id              INT           AUTO_INCREMENT PRIMARY KEY,
    name                  VARCHAR(100)  NOT NULL,
    display_order         INT           NOT NULL UNIQUE,
    bonus_score_threshold INT           NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subtopic (
    subtopic_id              INT           AUTO_INCREMENT PRIMARY KEY,
    topic_id                 INT           NOT NULL,
    name                     VARCHAR(100)  NOT NULL,
    display_order            INT           NOT NULL,
    is_bonus                 BOOLEAN       NOT NULL DEFAULT FALSE,
    prerequisite_subtopic_id INT           NULL,
    FOREIGN KEY (topic_id)
        REFERENCES topic(topic_id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_subtopic_id)
        REFERENCES subtopic(subtopic_id) ON DELETE SET NULL,
    UNIQUE KEY uq_subtopic_order (topic_id, display_order)
);

CREATE TABLE IF NOT EXISTS question (
    question_id    INT           AUTO_INCREMENT PRIMARY KEY,
    subtopic_id    INT           NOT NULL,
    tier           TINYINT       NOT NULL,
    prompt         TEXT          NOT NULL,
    correct_answer TEXT          NOT NULL,
    -- Numeric format:        '9.81' or '9.81|0.05'  (value|tolerance)
    -- Multiple choice format: 'B'
    -- Free response format:   'acceleration|force|mass'
    hint_text      TEXT          NOT NULL,
    question_type  VARCHAR(20)   NOT NULL DEFAULT 'multiple_choice',
    -- 'multiple_choice' | 'numeric' | 'free_response'
    CONSTRAINT chk_tier CHECK (tier BETWEEN 1 AND 4),
    FOREIGN KEY (subtopic_id)
        REFERENCES subtopic(subtopic_id) ON DELETE CASCADE
);

-- Multiple choice options stored separately (one row per option per question)
CREATE TABLE IF NOT EXISTS question_option (
    option_id    INT          AUTO_INCREMENT PRIMARY KEY,
    question_id  INT          NOT NULL,
    option_key   CHAR(1)      NOT NULL,   -- 'A', 'B', 'C', 'D'
    option_text  TEXT         NOT NULL,
    FOREIGN KEY (question_id)
        REFERENCES question(question_id) ON DELETE CASCADE,
    UNIQUE KEY uq_option (question_id, option_key)
);

-- ── GROUP 2: Users & authentication ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user (
    user_id       INT           AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)   NOT NULL UNIQUE,
    email         VARCHAR(120)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    DATETIME      NULL
);

CREATE TABLE IF NOT EXISTS refresh_token (
    token_id    INT           AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL UNIQUE,  -- one active token per user
    token_hash  VARCHAR(255)  NOT NULL,
    expires_at  DATETIME      NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)
        REFERENCES user(user_id) ON DELETE CASCADE
);

-- ── GROUP 3: Sessions & attempts ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS session (
    session_id     INT           AUTO_INCREMENT PRIMARY KEY,
    user_id        INT           NOT NULL,
    subtopic_id    INT           NOT NULL,
    started_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at   DATETIME      NULL,
    questions_used INT           NOT NULL DEFAULT 0,
    score          INT           NULL,
    outcome        VARCHAR(20)   NULL,
    -- 'pass' | 'fail' | 'skip_granted' | 'incomplete'
    FOREIGN KEY (user_id)     REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (subtopic_id) REFERENCES subtopic(subtopic_id)
);

CREATE TABLE IF NOT EXISTS question_attempt (
    attempt_id          INT       AUTO_INCREMENT PRIMARY KEY,
    session_id          INT       NOT NULL,
    question_id         INT       NOT NULL,
    tier                TINYINT   NOT NULL,
    is_correct          BOOLEAN   NOT NULL,
    hint_used           BOOLEAN   NOT NULL DEFAULT FALSE,
    counts_toward_limit BOOLEAN   NOT NULL DEFAULT TRUE,
    -- FALSE for first-attempt wrong answers (held pending hint retry)
    attempt_number      INT       NOT NULL DEFAULT 1,
    -- 1 = first try, 2 = hint retry
    attempted_at        DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id)  REFERENCES session(session_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES question(question_id)
);

CREATE TABLE IF NOT EXISTS review_question_log (
    log_id      INT       AUTO_INCREMENT PRIMARY KEY,
    session_id  INT       NOT NULL,
    question_id INT       NOT NULL,
    is_correct  BOOLEAN   NOT NULL,
    FOREIGN KEY (session_id)  REFERENCES session(session_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES question(question_id)
);

-- ── GROUP 4: Progress & scoring ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_subtopic_progress (
    progress_id  INT          AUTO_INCREMENT PRIMARY KEY,
    user_id      INT          NOT NULL,
    subtopic_id  INT          NOT NULL,
    best_score   INT          NOT NULL DEFAULT 0,
    attempts     INT          NOT NULL DEFAULT 0,
    status       VARCHAR(20)  NOT NULL DEFAULT 'locked',
    -- 'locked' | 'unlocked' | 'passed' | 'skipped'
    skipped      BOOLEAN      NOT NULL DEFAULT FALSE,
    passed_at    DATETIME     NULL,
    UNIQUE KEY uq_user_subtopic (user_id, subtopic_id),
    FOREIGN KEY (user_id)     REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (subtopic_id) REFERENCES subtopic(subtopic_id)
);

CREATE TABLE IF NOT EXISTS user_topic_score (
    record_id          INT          AUTO_INCREMENT PRIMARY KEY,
    user_id            INT          NOT NULL,
    topic_id           INT          NOT NULL,
    total_score        INT          NOT NULL DEFAULT 0,
    status             VARCHAR(20)  NOT NULL DEFAULT 'locked',
    -- 'locked' | 'unlocked' | 'completed'
    bonus_unlocked     BOOLEAN      NOT NULL DEFAULT FALSE,
    bonus_unlocked_at  DATETIME     NULL,
    bonus_completed    BOOLEAN      NOT NULL DEFAULT FALSE,
    bonus_completed_at DATETIME     NULL,
    UNIQUE KEY uq_user_topic (user_id, topic_id),
    FOREIGN KEY (user_id)  REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topic(topic_id)
);

CREATE TABLE IF NOT EXISTS review_performance (
    review_perf_id          INT       AUTO_INCREMENT PRIMARY KEY,
    user_id                 INT       NOT NULL,
    subtopic_id             INT       NOT NULL,
    correct_count           INT       NOT NULL DEFAULT 0,
    incorrect_count         INT       NOT NULL DEFAULT 0,
    last_reviewed_at        DATETIME  NULL,
    sessions_since_last_review INT    NOT NULL DEFAULT 0,
    UNIQUE KEY uq_review_perf (user_id, subtopic_id),
    FOREIGN KEY (user_id)     REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (subtopic_id) REFERENCES subtopic(subtopic_id)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX idx_subtopic_topic        ON subtopic(topic_id);
CREATE INDEX idx_question_subtopic_tier ON question(subtopic_id, tier);
CREATE INDEX idx_session_user          ON session(user_id);
CREATE INDEX idx_session_subtopic      ON session(subtopic_id);
CREATE INDEX idx_attempt_session       ON question_attempt(session_id);
CREATE INDEX idx_attempt_question      ON question_attempt(question_id);
CREATE INDEX idx_review_log_session    ON review_question_log(session_id);
CREATE INDEX idx_progress_user         ON user_subtopic_progress(user_id);
CREATE INDEX idx_progress_status       ON user_subtopic_progress(user_id, status);
CREATE INDEX idx_topic_score_user      ON user_topic_score(user_id);
CREATE INDEX idx_review_perf_user      ON review_performance(user_id);

SET FOREIGN_KEY_CHECKS = 1;

-- ── Seed: Physics I catalog ───────────────────────────────────────────────────

INSERT INTO topic (topic_id, name, display_order, bonus_score_threshold) VALUES
  (1, 'Kinematics',        1, 400),
  (2, 'Dynamics',          2, 450),
  (3, 'Work & Energy',     3, 400),
  (4, 'Momentum',          4, 380),
  (5, 'Rotational Motion', 5, 420),
  (6, 'Gravitation',       6, 360),
  (7, 'Waves',             7, 380);

-- Kinematics subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (1,  1, '1D Motion',                      1, FALSE, NULL),
  (2,  1, '2D Motion',                      2, FALSE, 1),
  (3,  1, 'Projectile Motion',              3, FALSE, 2),
  (4,  1, 'Relative Motion',                4, FALSE, 3),
  (5,  1, 'Graphical Analysis',             5, FALSE, 4),
  (6,  1, 'Special Relativity Intro',       6, TRUE,  NULL);

-- Dynamics subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (7,  2, 'Newton\'s Laws',                 1, FALSE, NULL),
  (8,  2, 'Free-Body Diagrams',             2, FALSE, 7),
  (9,  2, 'Frictional Forces',              3, FALSE, 8),
  (10, 2, 'Tension Forces',                 4, FALSE, 9),
  (11, 2, 'Circular Motion Dynamics',       5, FALSE, 10),
  (12, 2, 'Rocket Science Intro',           6, TRUE,  NULL);

-- Work & Energy subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (13, 3, 'Work & the Work-Energy Theorem', 1, FALSE, NULL),
  (14, 3, 'Kinetic Energy',                 2, FALSE, 13),
  (15, 3, 'Potential Energy',               3, FALSE, 14),
  (16, 3, 'Conservation of Energy',         4, FALSE, 15),
  (17, 3, 'Thermodynamics Intro',           5, TRUE,  NULL);

-- Momentum subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (18, 4, 'Linear Momentum & Impulse',      1, FALSE, NULL),
  (19, 4, 'Conservation of Momentum',       2, FALSE, 18),
  (20, 4, 'Elastic Collisions',             3, FALSE, 19),
  (21, 4, 'Inelastic Collisions',           4, FALSE, 20),
  (22, 4, 'Particle Physics Intro',         5, TRUE,  NULL);

-- Rotational Motion subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (23, 5, 'Angular Kinematics',             1, FALSE, NULL),
  (24, 5, 'Torque & Rotational Inertia',    2, FALSE, 23),
  (25, 5, 'Angular Momentum',               3, FALSE, 24),
  (26, 5, 'Rolling Motion',                 4, FALSE, 25),
  (27, 5, 'Gyroscopic Effects',             5, TRUE,  NULL);

-- Gravitation subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (28, 6, 'Newton\'s Law of Gravitation',   1, FALSE, NULL),
  (29, 6, 'Gravitational Fields',           2, FALSE, 28),
  (30, 6, 'Orbital Mechanics',              3, FALSE, 29),
  (31, 6, 'Black Holes Intro',              4, TRUE,  NULL);

-- Waves subtopics
INSERT INTO subtopic (subtopic_id, topic_id, name, display_order, is_bonus, prerequisite_subtopic_id) VALUES
  (32, 7, 'Wave Properties',                1, FALSE, NULL),
  (33, 7, 'Sound Waves',                    2, FALSE, 32),
  (34, 7, 'Standing Waves & Resonance',     3, FALSE, 33),
  (35, 7, 'Light & Optics Intro',           4, FALSE, 34),
  (36, 7, 'Quantum Mechanics Intro',        5, TRUE,  NULL);
