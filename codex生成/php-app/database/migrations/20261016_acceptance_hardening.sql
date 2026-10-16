BEGIN;
SELECT pg_advisory_xact_lock(671902061);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(80) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION ensure_completed_session_has_set() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    target_session INTEGER;
    target_status VARCHAR(20);
BEGIN
    IF TG_TABLE_NAME = 'workout_sessions' THEN
        target_session := COALESCE(NEW.workout_session_id, OLD.workout_session_id);
        target_status := COALESCE(NEW.status, OLD.status);
    ELSIF TG_TABLE_NAME = 'workout_session_exercises' THEN
        target_session := COALESCE(NEW.workout_session_id, OLD.workout_session_id);
        SELECT status INTO target_status FROM workout_sessions
        WHERE workout_session_id = target_session FOR UPDATE;
    ELSE
        SELECT workout_session_id INTO target_session FROM workout_session_exercises
        WHERE workout_session_exercise_id = COALESCE(NEW.workout_session_exercise_id, OLD.workout_session_exercise_id);
        SELECT status INTO target_status FROM workout_sessions
        WHERE workout_session_id = target_session FOR UPDATE;
    END IF;
    IF target_status = 'completed' AND NOT EXISTS (
        SELECT 1 FROM workout_sets ws
        JOIN workout_session_exercises wse ON wse.workout_session_exercise_id = ws.workout_session_exercise_id
        WHERE wse.workout_session_id = target_session
    ) THEN
        RAISE EXCEPTION 'a completed workout session must contain at least one set' USING ERRCODE = '23514';
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

INSERT INTO schema_migrations(version)
VALUES ('20261016_acceptance_hardening')
ON CONFLICT (version) DO NOTHING;

COMMIT;
