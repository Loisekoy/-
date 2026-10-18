<?php

declare(strict_types=1);

namespace FitTrack;

final class Config
{
    private static bool $loaded = false;

    public static function load(): void
    {
        if (self::$loaded) {
            return;
        }

        self::$loaded = true;
        $path = dirname(__DIR__) . '/.env';
        if (!is_file($path)) {
            return;
        }

        foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [] as $line) {
            $line = trim($line);
            if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
                continue;
            }
            [$key, $value] = array_map('trim', explode('=', $line, 2));
            $value = trim($value, "\"'");
            if (getenv($key) === false) {
                putenv($key . '=' . $value);
                $_ENV[$key] = $value;
            }
        }
    }

    public static function get(string $key, ?string $default = null): ?string
    {
        self::load();
        $value = getenv($key);
        return $value === false ? $default : $value;
    }

    public static function root(): string
    {
        return dirname(__DIR__);
    }

    public static function appKey(): string
    {
        $key = self::get('SECRET_KEY', self::get('APP_KEY', 'local-development-key-change-before-deploy')) ?? '';
        if (self::isProduction()
            && ($key === 'local-development-key-change-before-deploy' || strlen($key) < 32)) {
            throw new \RuntimeException('Production SECRET_KEY must be explicitly configured with at least 32 bytes.');
        }
        return $key;
    }

    public static function isProduction(): bool
    {
        return strtolower(self::get('APP_ENV', 'development') ?? 'development') === 'production';
    }

    public static function rateLimitSecret(): string
    {
        $secret = self::get('RATE_LIMIT_SECRET', self::appKey()) ?? self::appKey();
        if (self::isProduction() && strlen($secret) < 32) {
            throw new \RuntimeException('Production RATE_LIMIT_SECRET must be at least 32 bytes.');
        }
        return $secret;
    }
}
