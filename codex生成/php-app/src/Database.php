<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;
use RuntimeException;

final class Database
{
    private static ?PDO $pdo = null;
    private static bool $initialized = false;

    public static function connection(): PDO
    {
        if (self::$pdo instanceof PDO) {
            return self::$pdo;
        }

        $databaseUrl = Config::get('DATABASE_URL');
        if ($databaseUrl && preg_match('/^postgres(?:ql)?:\/\//', $databaseUrl)) {
            $parts = parse_url($databaseUrl);
            if (!$parts || !isset($parts['host'], $parts['path'])) {
                throw new RuntimeException('DATABASE_URL 格式不正確。');
            }
            $port = $parts['port'] ?? 5432;
            $database = ltrim($parts['path'], '/');
            $dsn = "pgsql:host={$parts['host']};port={$port};dbname={$database}";
            self::$pdo = new PDO(
                $dsn,
                urldecode($parts['user'] ?? ''),
                urldecode($parts['pass'] ?? ''),
                self::options()
            );
        } elseif ($databaseUrl && str_starts_with($databaseUrl, 'pgsql:')) {
            self::$pdo = new PDO(
                $databaseUrl,
                Config::get('DB_USER', ''),
                Config::get('DB_PASSWORD', ''),
                self::options()
            );
        } else {
            $sqlitePath = Config::get('SQLITE_PATH', Config::root() . '/storage/app.sqlite');
            if ($sqlitePath === null) {
                throw new RuntimeException('SQLITE_PATH 不可為空。');
            }
            $directory = dirname($sqlitePath);
            if (!is_dir($directory)) {
                mkdir($directory, 0775, true);
            }
            self::$pdo = new PDO('sqlite:' . $sqlitePath, null, null, self::options());
            self::$pdo->exec('PRAGMA foreign_keys = ON');
            self::ensureSqliteSchema(self::$pdo);
        }

        return self::$pdo;
    }

    public static function driver(): string
    {
        return (string) self::connection()->getAttribute(PDO::ATTR_DRIVER_NAME);
    }

    public static function insert(PDO $pdo, string $sql, array $params, string $idColumn): int
    {
        if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
            $statement = $pdo->prepare($sql . ' RETURNING ' . $idColumn);
            $statement->execute($params);
            return (int) $statement->fetchColumn();
        }

        $statement = $pdo->prepare($sql);
        $statement->execute($params);
        return (int) $pdo->lastInsertId();
    }

    private static function options(): array
    {
        return [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ];
    }

    private static function ensureSqliteSchema(PDO $pdo): void
    {
        if (self::$initialized) {
            return;
        }
        self::$initialized = true;

        $hasUsers = $pdo->query(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )->fetchColumn();
        if ((int) $hasUsers > 0) {
            return;
        }

        $schema = file_get_contents(Config::root() . '/database/sqlite.sql');
        if ($schema === false) {
            throw new RuntimeException('找不到 SQLite schema。');
        }
        $pdo->exec($schema);
        Seeder::seed($pdo);
    }
}
