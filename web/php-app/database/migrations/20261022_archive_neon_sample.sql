BEGIN;
SELECT pg_advisory_xact_lock(671902061);

CREATE SCHEMA IF NOT EXISTS fittrack_legacy_archive;

DO $$
BEGIN
    IF to_regclass('public.playing_with_neon') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE contype = 'f'
              AND (
                  conrelid = 'public.playing_with_neon'::regclass
                  OR confrelid = 'public.playing_with_neon'::regclass
              )
        ) THEN
            RAISE EXCEPTION 'playing_with_neon has foreign-key dependencies and was not archived';
        END IF;

        ALTER TABLE public.playing_with_neon SET SCHEMA fittrack_legacy_archive;
    END IF;
END;
$$;

INSERT INTO schema_migrations(version)
VALUES ('20261022_archive_neon_sample')
ON CONFLICT (version) DO NOTHING;

COMMIT;
