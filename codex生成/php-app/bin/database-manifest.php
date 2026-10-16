<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;

const TABLES = [
    'training_goals', 'body_parts', 'users', 'user_auth', 'user_sessions', 'admins',
    'login_failures', 'user_body_parts', 'body_records', 'exercises', 'exercise_versions',
    'workout_plans', 'planning_profiles', 'planning_profile_body_parts', 'plan_days',
    'plan_exercises', 'workout_sessions', 'workout_session_plans',
    'workout_session_exercises', 'workout_sets',
];

if (count($argv) !== 3 || !in_array($argv[1], ['--write', '--verify'], true)) {
    fwrite(STDERR, "Usage: php bin/database-manifest.php --write|--verify <manifest.json>\n");
    exit(2);
}

$pdo = Database::connection();
if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) !== 'pgsql') {
    throw new RuntimeException('Database manifest verification requires PostgreSQL.');
}

$counts = [];
foreach (TABLES as $table) {
    $counts[$table] = (int) $pdo->query('SELECT COUNT(*) FROM ' . $table)->fetchColumn();
}
$current = [
    'schema_versions' => $pdo->query('SELECT version FROM schema_migrations ORDER BY version')
        ->fetchAll(PDO::FETCH_COLUMN),
    'application_table_count' => (int) $pdo->query(
        "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND tablename <> 'schema_migrations'"
    )->fetchColumn(),
    'foreign_key_count' => (int) $pdo->query(
        "SELECT COUNT(*) FROM information_schema.table_constraints "
        . "WHERE constraint_schema='public' AND constraint_type='FOREIGN KEY'"
    )->fetchColumn(),
    'table_row_counts' => $counts,
];

$path = $argv[2];
if ($argv[1] === '--write') {
    $current['created_at_utc'] = gmdate('c');
    if (file_put_contents($path, json_encode($current, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES) . PHP_EOL, LOCK_EX) === false) {
        throw new RuntimeException("Unable to write database manifest: {$path}");
    }
    echo "Database manifest written.\n";
    exit(0);
}

$expected = json_decode((string) file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);
unset($expected['created_at_utc']);
if ($expected !== $current) {
    fwrite(STDERR, json_encode(['expected' => $expected, 'actual' => $current], JSON_PRETTY_PRINT) . PHP_EOL);
    throw new RuntimeException('Restored database does not match the backup manifest.');
}
if ($current['application_table_count'] !== 20 || $current['foreign_key_count'] !== 25) {
    throw new RuntimeException('Restored database schema cardinality is invalid.');
}

echo "PASS: restored database matches 20 tables, 25 foreign keys, schema version and all row counts.\n";
