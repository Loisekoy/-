<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Database;
use FitTrack\ExpiredDataCleaner;

$pdo = Database::connection();

try {
    fwrite(STDOUT, json_encode(ExpiredDataCleaner::run($pdo), JSON_UNESCAPED_UNICODE) . PHP_EOL);
} catch (Throwable $error) {
    error_log('Session cleanup failed [' . get_class($error) . '] code=' . $error->getCode());
    fwrite(STDERR, json_encode([
        'status' => 'error',
        'error_type' => get_class($error),
        'error_code' => (string) $error->getCode(),
    ], JSON_UNESCAPED_UNICODE) . PHP_EOL);
    exit(1);
}
