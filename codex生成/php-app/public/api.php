<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Api;
use FitTrack\ApiException;
use FitTrack\Database;

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/api', PHP_URL_PATH) ?: '/api';
$path = preg_replace('#^/api(?:\.php)?#', '', $path) ?: '/';

try {
    [$status, $body] = (new Api(Database::connection()))->dispatch(
        strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET'),
        $path
    );
    http_response_code($status);
    if ($status !== 204 && $body !== null) {
        echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
} catch (ApiException $error) {
    http_response_code($error->status);
    echo json_encode([
        'code' => $error->errorCode,
        'message' => $error->getMessage(),
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (Throwable $error) {
    error_log((string) $error);
    http_response_code(500);
    echo json_encode([
        'code' => 'INTERNAL_ERROR',
        'message' => '系統暫時無法處理這個要求，請稍後再試。',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}
