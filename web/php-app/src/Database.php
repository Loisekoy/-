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
            parse_str($parts['query'] ?? '', $query);
            $sslMode = (string) ($query['sslmode'] ?? (Config::isProduction() ? 'require' : 'prefer'));
            $allowedSslModes = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'];
            if (!in_array($sslMode, $allowedSslModes, true)) {
                throw new RuntimeException('DATABASE_URL 的 sslmode 不受支援。');
            }
            if (Config::isProduction() && in_array($sslMode, ['disable', 'allow', 'prefer'], true)) {
                throw new RuntimeException('正式環境 PostgreSQL 連線必須使用 TLS (sslmode=require 或更高)。');
            }
            $dsn = sprintf(
                'pgsql:host=%s;port=%d;dbname=%s;sslmode=%s',
                $parts['host'],
                $port,
                $database,
                $sslMode
            );
            self::$pdo = new PDO(
                $dsn,
                urldecode($parts['user'] ?? ''),
                urldecode($parts['pass'] ?? ''),
                self::options()
            );
            self::$pdo->exec('SET search_path TO public');
            self::$pdo->exec('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED');
            self::$pdo->exec("SET TIME ZONE 'Asia/Taipei'");
        } elseif ($databaseUrl && str_starts_with($databaseUrl, 'pgsql:')) {
            self::$pdo = new PDO(
                $databaseUrl,
                Config::get('DB_USER', ''),
                Config::get('DB_PASSWORD', ''),
                self::options()
            );
            self::$pdo->exec('SET search_path TO public');
            self::$pdo->exec('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED');
            self::$pdo->exec("SET TIME ZONE 'Asia/Taipei'");
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
            self::ensureSqliteSchema(self::$pdo, $sqlitePath);
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

    public static function beginTransaction(PDO $pdo): void
    {
        $pdo->beginTransaction();
        if ((string) $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'pgsql') {
            $pdo->exec('SET TRANSACTION ISOLATION LEVEL READ COMMITTED');
        }
    }

    private static function options(): array
    {
        return [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ];
    }

    private static function ensureSqliteSchema(PDO $pdo, string $sqlitePath): void
    {
        if (self::$initialized) {
            return;
        }
        self::$initialized = true;

        $hasUsers = $pdo->query(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )->fetchColumn();
        if ((int) $hasUsers > 0) {
            SqliteMigrator::migrateIfNeeded($pdo, $sqlitePath);
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
