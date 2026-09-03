-- =========================================================
-- Migration: add the AI-predicted "people fed" column
-- Run this ONLY if you already created foodlink_db before
-- (i.e. your donations table doesn't have this column yet).
-- If you're setting up the database fresh, just run
-- foodlink_db.sql instead — it already includes this column.
-- =========================================================

USE foodlink_db;

ALTER TABLE donations
ADD COLUMN estimated_people_fed INT DEFAULT NULL AFTER contact_number;
