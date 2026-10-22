BEGIN;
SELECT pg_advisory_xact_lock(671902061);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(80) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE planning_profiles ALTER COLUMN algorithm_version SET DEFAULT 'rules-v1';

DROP TRIGGER IF EXISTS trg_body_records_keep_last ON body_records;
DROP FUNCTION IF EXISTS lock_and_protect_last_body_record();

CREATE OR REPLACE FUNCTION lock_body_record_owners() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    first_user INTEGER;
    second_user INTEGER;
BEGIN
    first_user := OLD.user_id;
    second_user := CASE WHEN TG_OP = 'UPDATE' THEN NEW.user_id ELSE OLD.user_id END;
    IF second_user < first_user THEN
        first_user := second_user;
        second_user := OLD.user_id;
    END IF;
    PERFORM 1 FROM users WHERE user_id = first_user FOR UPDATE;
    IF second_user <> first_user THEN
        PERFORM 1 FROM users WHERE user_id = second_user FOR UPDATE;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_body_records_keep_last
    BEFORE DELETE OR UPDATE OF user_id ON body_records
    FOR EACH ROW EXECUTE FUNCTION lock_body_record_owners();

CREATE OR REPLACE FUNCTION ensure_completed_profile_has_weight() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    affected_user INTEGER;
    other_user INTEGER;
BEGIN
    IF TG_TABLE_NAME = 'users' THEN
        affected_user := COALESCE(NEW.user_id, OLD.user_id);
    ELSE
        affected_user := OLD.user_id;
        IF TG_OP = 'UPDATE' THEN other_user := NEW.user_id; END IF;
    END IF;

    IF EXISTS (
        SELECT 1 FROM users u
        WHERE u.user_id = affected_user AND u.profile_completed_at IS NOT NULL
    ) AND NOT EXISTS (
        SELECT 1 FROM body_records br WHERE br.user_id = affected_user
    ) THEN
        RAISE EXCEPTION 'completed_profile_requires_weight_record' USING ERRCODE = '23514';
    END IF;

    IF other_user IS NOT NULL AND other_user <> affected_user
       AND EXISTS (
           SELECT 1 FROM users u
           WHERE u.user_id = other_user AND u.profile_completed_at IS NOT NULL
       ) AND NOT EXISTS (
           SELECT 1 FROM body_records br WHERE br.user_id = other_user
       ) THEN
        RAISE EXCEPTION 'completed_profile_requires_weight_record' USING ERRCODE = '23514';
    END IF;

    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_completed_profile_weight ON users;
CREATE CONSTRAINT TRIGGER trg_users_completed_profile_weight
    AFTER INSERT OR UPDATE ON users
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION ensure_completed_profile_has_weight();

DROP TRIGGER IF EXISTS trg_body_records_completed_profile_weight ON body_records;
CREATE CONSTRAINT TRIGGER trg_body_records_completed_profile_weight
    AFTER DELETE OR UPDATE OF user_id ON body_records
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION ensure_completed_profile_has_weight();

INSERT INTO schema_migrations(version)
VALUES ('20261022_srs_conformance')
ON CONFLICT (version) DO NOTHING;

COMMIT;
