<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Api;
use FitTrack\ApiException;
use FitTrack\ApiResponse;
use FitTrack\Database;
use FitTrack\RequestSecurity;

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/api', PHP_URL_PATH) ?: '/api';
$path = preg_replace('#^/api(?:\.php)?#', '', $path) ?: '/';
$method = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');

try {
    RequestSecurity::enforceBrowserWriteProtection($method, $path);
    [$status, $body] = (new Api(Database::connection(), RequestSecurity::clientIp()))->dispatch($method, $path);
    $body = ApiResponse::normalize($body);
    if (in_array($path, ['/auth/register', '/auth/login'], true) && is_array($body)) {
        RequestSecurity::issueCookies((string) $body['access_token'], (int) $body['expires_in']);
        unset($body['access_token'], $body['token_type']);
    }
    if (in_array($path, ['/auth/logout', '/auth/password', '/auth/deactivate'], true)
        && in_array($method, ['POST', 'PATCH'], true)) {
        RequestSecurity::clearCookies();
    }
    http_response_code($status);
    if ($status !== 204) {
        echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
} catch (ApiException $error) {
    foreach ($error->headers as $name => $value) {
        header($name . ': ' . $value);
    }
    if ($error->status === 401) {
        RequestSecurity::clearCookies();
    }
    http_response_code($error->status);
    $body = [
        'code' => $error->errorCode,
        'message' => $error->getMessage(),
    ];
    if ($error->status === 422) {
        $body['field_errors'] = (object) $error->fieldErrors;
    }
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (PDOException $error) {
    $sqlState = (string) $error->getCode();
    if (in_array($sqlState, ['40P01', '40001'], true)) {
        http_response_code(409);
        echo json_encode([
            'code' => 'TRANSACTION_RETRY_REQUIRED',
            'message' => '同時操作發生衝突，請重新載入後再試。',
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    } elseif (in_array($sqlState, ['55P03', '57014'], true)) {
        header('Retry-After: 1');
        http_response_code(503);
        echo json_encode([
            'code' => 'RETRY_LATER',
            'message' => '資料庫正在處理同時操作，請稍候重試。',
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    } else {
        error_log('Database request failed [' . $error->getCode() . ']');
        http_response_code(500);
        echo json_encode([
            'code' => 'INTERNAL_ERROR',
            'message' => '系統暫時無法處理這個要求，請稍後再試。',
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
} catch (Throwable $error) {
    error_log('Unhandled request failure [' . get_class($error) . '] code=' . $error->getCode());
    http_response_code(500);
    echo json_encode([
        'code' => 'INTERNAL_ERROR',
        'message' => '系統暫時無法處理這個要求，請稍後再試。',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}
