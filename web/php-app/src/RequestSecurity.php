<?php

declare(strict_types=1);

namespace FitTrack;

final class RequestSecurity
{
    public static function accessCookieName(): string
    {
        return Config::isProduction() ? '__Host-fittrack_access' : 'fittrack_access';
    }

    public static function csrfCookieName(): string
    {
        return Config::isProduction() ? '__Host-fittrack_csrf' : 'fittrack_csrf';
    }

    public static function token(): ?string
    {
        $cookie = $_COOKIE[self::accessCookieName()] ?? null;
        if (is_string($cookie) && $cookie !== '') {
            return $cookie;
        }
        $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        if (preg_match('/^Bearer\s+(.+)$/i', $header, $matches)) {
            return trim($matches[1]);
        }
        return null;
    }

    public static function issueCookies(string $accessToken, int $expiresIn): void
    {
        $base = [
            'expires' => time() + $expiresIn,
            'path' => '/',
            'secure' => Config::isProduction(),
            'samesite' => 'Strict',
        ];
        setcookie(self::accessCookieName(), $accessToken, $base + ['httponly' => true]);
        setcookie(self::csrfCookieName(), self::signedCsrfToken($accessToken), $base + ['httponly' => false]);
    }

    public static function clearCookies(): void
    {
        $base = [
            'expires' => 1,
            'path' => '/',
            'secure' => Config::isProduction(),
            'samesite' => 'Strict',
        ];
        setcookie(self::accessCookieName(), '', $base + ['httponly' => true]);
        setcookie(self::csrfCookieName(), '', $base + ['httponly' => false]);
    }

    public static function enforceBrowserWriteProtection(string $method, string $path): void
    {
        if (in_array($method, ['GET', 'HEAD', 'OPTIONS'], true)) {
            return;
        }
        if (in_array($path, ['/auth/login', '/auth/register'], true)) {
            self::assertSameOrigin();
            return;
        }
        $accessToken = $_COOKIE[self::accessCookieName()] ?? null;
        if (!is_string($accessToken) || $accessToken === '') {
            return; // Bearer-token API/CLI clients are not vulnerable to ambient-cookie CSRF.
        }
        self::assertSameOrigin();
        $cookie = (string) ($_COOKIE[self::csrfCookieName()] ?? '');
        $header = (string) ($_SERVER['HTTP_X_CSRF_TOKEN'] ?? '');
        if ($cookie === '' || $header === '' || !hash_equals($cookie, $header)
            || !self::validSignedCsrfToken($cookie, $accessToken)) {
            throw new ApiException(403, 'CSRF_REJECTED', '安全驗證失敗，請重新整理頁面後再試。');
        }
    }

    public static function clientIp(): string
    {
        $remote = (string) ($_SERVER['REMOTE_ADDR'] ?? '127.0.0.1');
        $trusted = array_filter(array_map('trim', explode(',', Config::get('TRUSTED_PROXY_IPS', '') ?? '')));
        if (in_array($remote, $trusted, true)) {
            $forwarded = trim(explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? ''))[0] ?? '');
            if (filter_var($forwarded, FILTER_VALIDATE_IP)) {
                return $forwarded;
            }
        }
        return filter_var($remote, FILTER_VALIDATE_IP) ? $remote : '0.0.0.0';
    }

    private static function assertSameOrigin(): void
    {
        $origin = trim((string) ($_SERVER['HTTP_ORIGIN'] ?? ''));
        $referer = trim((string) ($_SERVER['HTTP_REFERER'] ?? ''));
        $host = trim((string) ($_SERVER['HTTP_HOST'] ?? ''));
        if ($origin === '' && $referer === '') {
            throw new ApiException(403, 'ORIGIN_REQUIRED', '缺少必要的來源驗證。');
        }
        $candidate = $origin !== '' ? $origin : $referer;
        $parts = parse_url($candidate);
        $expected = parse_url('http://' . $host);
        if (!$parts || !$expected) {
            throw new ApiException(403, 'ORIGIN_REJECTED', '不允許跨網站送出這個要求。');
        }
        $expectedScheme = Config::isProduction()
            ? 'https'
            : (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off' ? 'https' : 'http');
        $candidateScheme = strtolower((string) ($parts['scheme'] ?? ''));
        $candidatePort = (int) ($parts['port'] ?? ($candidateScheme === 'https' ? 443 : 80));
        $expectedPort = (int) ($expected['port'] ?? ($expectedScheme === 'https' ? 443 : 80));
        if (strtolower((string) ($parts['host'] ?? '')) !== strtolower((string) ($expected['host'] ?? ''))
            || $candidateScheme !== $expectedScheme
            || $candidatePort !== $expectedPort) {
            throw new ApiException(403, 'ORIGIN_REJECTED', '不允許跨網站送出這個要求。');
        }
        if (Config::isProduction() && $candidateScheme !== 'https') {
            throw new ApiException(403, 'HTTPS_REQUIRED', '正式環境只接受 HTTPS 來源。');
        }
    }

    private static function signedCsrfToken(string $accessToken): string
    {
        $nonce = bin2hex(random_bytes(32));
        $signature = hash_hmac('sha256', $accessToken . '.' . $nonce, Config::appKey());
        return $nonce . '.' . $signature;
    }

    private static function validSignedCsrfToken(string $token, string $accessToken): bool
    {
        $parts = explode('.', $token, 2);
        if (count($parts) !== 2 || !preg_match('/^[a-f0-9]{64}$/', $parts[0])
            || !preg_match('/^[a-f0-9]{64}$/', $parts[1])) {
            return false;
        }
        $expected = hash_hmac('sha256', $accessToken . '.' . $parts[0], Config::appKey());
        return hash_equals($expected, $parts[1]);
    }
}
