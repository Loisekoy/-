<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;
use FitTrack\SqliteMigrator;

$pdo = Database::connection();
if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) !== 'pgsql') {
    $backup = SqliteMigrator::lastBackupPath();
    if ($backup !== null) {
        fwrite(STDOUT, "SQLite v1.0 upgraded to v1.1; backup: {$backup}\n");
    } else {
        fwrite(STDOUT, "SQLite is already using the current v1.1 structure.\n");
    }
    exit(0);
}

$hasUsers = (int) $pdo->query(
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='users'"
)->fetchColumn();
if ($hasUsers === 0) {
    fwrite(STDOUT, "Fresh database detected; bin/setup.php will apply the current schema.\n");
    exit(0);
}

$hasVersions = (int) $pdo->query(
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='exercise_versions'"
)->fetchColumn();
if ($hasVersions > 0) {
    fwrite(STDOUT, "Current v1.1 structure already present; migration skipped.\n");
    exit(0);
}

$path = dirname(__DIR__) . '/database/migrations/20261006_teacher_review_v1_1.sql';
$sql = file_get_contents($path);
if ($sql === false) {
    throw new RuntimeException('Migration file is missing: ' . $path);
}

fwrite(STDOUT, "Applying v1.1 migration after preflight checks...\n");
$pdo->exec($sql);
fwrite(STDOUT, "Migration 20261006_teacher_review_v1_1 applied.\n");
