-- Reel Studio 2.0 Mode B (prompt → professional edit) projects. Kept in its own migration: a new enum value cannot
-- be used in the transaction that adds it. Old 'topic' projects stay readable.
alter type public.project_mode add value if not exists 'edit';
