<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;
use RuntimeException;

final class Auth
{
    public static function register(PDO $pdo, array $input): array
    {
        $name = trim(self::stringField($input, 'name'));
        $email = mb_strtolower(trim(self::stringField($input, 'email')));
        $password = self::stringField($input, 'password');

        if (mb_strlen($name) < 1 || mb_strlen($name) > 100) {
            throw new ApiException(422, 'INVALID_NAME', '姓名需為 1 至 100 個字。');
        }
        if (!filter_var($email, FILTER_VALIDATE_EMAIL) || mb_strlen($email) > 255) {
            throw new ApiException(422, 'INVALID_EMAIL', 'Email 格式不正確。');
        }
        $length = strlen($password);
        if ($length < 10 || $length > 72 || str_contains($password, "\0")
            || !preg_match('/[A-Za-z]/', $password) || !preg_match('/\d/', $password)) {
            throw new ApiException(422, 'INVALID_PASSWORD', '密碼需為 10 至 72 bytes，且至少包含英文字母與數字。');
        }

        $exists = $pdo->prepare('SELECT 1 FROM user_auth WHERE email = ?');
        $exists->execute([$email]);
        if ($exists->fetchColumn()) {
            throw new ApiException(409, 'EMAIL_EXISTS', '這個 Email 已經註冊。');
        }

        Database::beginTransaction($pdo);
        try {
            $userId = Database::insert(
                $pdo,
                'INSERT INTO users (name) VALUES (?)',
                [$name],
                'user_id'
            );
            $authId = Database::insert(
                $pdo,
                'INSERT INTO user_auth (user_id, email, password_hash) VALUES (?, ?, ?)',
                [$userId, $email, password_hash($password, PASSWORD_BCRYPT, ['cost' => 10])],
                'auth_id'
            );
            $result = self::createSession($pdo, $authId, $userId, 'USER', $name, $email);
            $pdo->commit();
            return $result;
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            if ($error instanceof \PDOException && self::isUniqueViolation($error)) {
                throw new ApiException(409, 'EMAIL_EXISTS', '這個 Email 已經註冊。');
            }
            throw $error;
        }
    }

    public static function login(PDO $pdo, array $input): array
    {
        $email = mb_strtolower(trim(self::stringField($input, 'email')));
        $password = self::stringField($input, 'password');
        if (str_contains($password, "\0")) {
            throw new ApiException(422, 'INVALID_PASSWORD', '密碼不得包含 NUL。', [], [
                'password' => '密碼不得包含 NUL。',
            ]);
        }
        $statement = $pdo->prepare(
            'SELECT ua.auth_id, ua.user_id, ua.email, ua.password_hash, ua.is_active, u.name, '
            . 'CASE WHEN a.user_id IS NULL THEN 0 ELSE 1 END AS is_admin '
            . 'FROM user_auth ua JOIN users u ON u.user_id = ua.user_id '
            . 'LEFT JOIN admins a ON a.user_id = ua.user_id WHERE ua.email = ?'
        );
        $statement->execute([$email]);
        $row = $statement->fetch();

        if (!$row || !(bool) $row['is_active'] || !password_verify($password, $row['password_hash'])) {
            throw new ApiException(401, 'INVALID_CREDENTIALS', 'Email 或密碼錯誤。');
        }

        return self::createSession(
            $pdo,
            (int) $row['auth_id'],
            (int) $row['user_id'],
            (int) $row['is_admin'] === 1 ? 'ADMIN' : 'USER',
            (string) $row['name'],
            (string) $row['email']
        );
    }

    public static function user(PDO $pdo, ?string $token): array
    {
        if (!$token) {
            throw new ApiException(401, 'AUTH_REQUIRED', '請先登入。');
        }
        $payload = self::decode($token);
        $statement = $pdo->prepare(
            'SELECT u.user_id, u.name, ua.auth_id, ua.email, ua.is_active, us.expires_at, us.revoked_at, '
            . 'CASE WHEN a.user_id IS NULL THEN 0 ELSE 1 END AS is_admin '
            . 'FROM user_sessions us '
            . 'JOIN user_auth ua ON ua.auth_id = us.auth_id '
            . 'JOIN users u ON u.user_id = ua.user_id '
            . 'LEFT JOIN admins a ON a.user_id = u.user_id '
            . 'WHERE us.user_session_id = ? AND u.user_id = ?'
        );
        $statement->execute([(string) ($payload['jti'] ?? ''), (int) ($payload['sub'] ?? 0)]);
        $row = $statement->fetch();
        if (!$row || !(bool) $row['is_active'] || $row['revoked_at'] !== null || strtotime($row['expires_at']) <= time()) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入狀態已失效，請重新登入。');
        }

        return [
            'user_id' => (int) $row['user_id'],
            'auth_id' => (int) $row['auth_id'],
            'name' => $row['name'],
            'email' => $row['email'],
            'role' => (int) $row['is_admin'] === 1 ? 'ADMIN' : 'USER',
            'jti' => (string) $payload['jti'],
        ];
    }

    public static function logout(PDO $pdo, array $user): void
    {
        $statement = $pdo->prepare(
            'UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP '
            . 'WHERE user_session_id = ? AND revoked_at IS NULL'
        );
        $statement->execute([$user['jti']]);
    }

    public static function changePassword(PDO $pdo, array $user, array $input): void
    {
        $current = self::stringField($input, 'current_password');
        $new = self::stringField($input, 'new_password');
        if (str_contains($current, "\0")) {
            throw new ApiException(422, 'INVALID_PASSWORD', '密碼不得包含 NUL。');
        }
        $statement = $pdo->prepare(
            'SELECT password_hash FROM user_auth WHERE auth_id = ? AND user_id = ?'
        );
        $statement->execute([(int) $user['auth_id'], (int) $user['user_id']]);
        $hash = $statement->fetchColumn();
        if (!$hash || !password_verify($current, (string) $hash)) {
            throw new ApiException(401, 'INVALID_CURRENT_PASSWORD', '目前密碼不正確。');
        }
        $length = strlen($new);
        if ($length < 10 || $length > 72 || str_contains($new, "\0")
            || !preg_match('/[A-Za-z]/', $new) || !preg_match('/\d/', $new)) {
            throw new ApiException(422, 'INVALID_PASSWORD', '新密碼需為 10 至 72 bytes，且至少包含英文字母與數字。');
        }

        Database::beginTransaction($pdo);
        try {
            $pdo->prepare('UPDATE user_auth SET password_hash = ? WHERE auth_id = ?')->execute([
                password_hash($new, PASSWORD_BCRYPT, ['cost' => 10]),
                (int) $user['auth_id'],
            ]);
            $pdo->prepare(
                'UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP '
                . 'WHERE auth_id = ? AND revoked_at IS NULL'
            )->execute([(int) $user['auth_id']]);
            $pdo->commit();
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    public static function deactivate(PDO $pdo, array $user, array $input): void
    {
        $current = self::stringField($input, 'current_password');
        if (str_contains($current, "\0")) {
            throw new ApiException(422, 'INVALID_PASSWORD', '密碼不得包含 NUL。');
        }
        $statement = $pdo->prepare(
            'SELECT password_hash FROM user_auth WHERE auth_id = ? AND user_id = ?'
        );
        $statement->execute([(int) $user['auth_id'], (int) $user['user_id']]);
        $hash = $statement->fetchColumn();
        if (!$hash || !password_verify($current, (string) $hash)) {
            throw new ApiException(401, 'INVALID_CURRENT_PASSWORD', '目前密碼不正確。');
        }

        Database::beginTransaction($pdo);
        try {
            $pdo->prepare('UPDATE user_auth SET is_active = FALSE WHERE auth_id = ?')->execute([
                (int) $user['auth_id'],
            ]);
            $pdo->prepare(
                'UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP '
                . 'WHERE auth_id = ? AND revoked_at IS NULL'
            )->execute([(int) $user['auth_id']]);
            $pdo->commit();
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    private static function isUniqueViolation(\PDOException $error): bool
    {
        $message = strtolower($error->getMessage());
        return $error->getCode() === '23505'
            || str_contains($message, 'unique constraint')
            || str_contains($message, 'is not unique');
    }

    private static function stringField(array $input, string $field): string
    {
        if (!array_key_exists($field, $input) || !is_string($input[$field])) {
            throw new ApiException(422, 'INVALID_FIELD_TYPE', "{$field} 必須是字串。", [], [
                $field => '必須是字串。',
            ]);
        }
        return $input[$field];
    }

    private static function createSession(
        PDO $pdo,
        int $authId,
        int $userId,
        string $role,
        string $name,
        string $email
    ): array
    {
        $jti = self::uuidV4();
        $issuedAt = time();
        $expiresAt = $issuedAt + 7200;
        $statement = $pdo->prepare(
            'INSERT INTO user_sessions (user_session_id, auth_id, created_at, expires_at) VALUES (?, ?, ?, ?)'
        );
        $statement->execute([
            $jti,
            $authId,
            gmdate('Y-m-d\TH:i:s\Z', $issuedAt),
            gmdate('Y-m-d\TH:i:s\Z', $expiresAt),
        ]);
        $payload = [
            'sub' => (string) $userId,
            'jti' => $jti,
            'iat' => $issuedAt,
            'exp' => $expiresAt,
        ];
        return [
            'user_id' => $userId,
            'name' => $name,
            'email' => $email,
            'role' => $role,
            'access_token' => self::encode($payload),
            'token_type' => 'Bearer',
            'expires_in' => 7200,
        ];
    }

    private static function encode(array $payload): string
    {
        $header = ['alg' => 'HS256', 'typ' => 'JWT'];
        $segments = [
            self::base64UrlEncode(json_encode($header, JSON_UNESCAPED_SLASHES) ?: '{}'),
            self::base64UrlEncode(json_encode($payload, JSON_UNESCAPED_SLASHES) ?: '{}'),
        ];
        $signature = hash_hmac('sha256', implode('.', $segments), Config::appKey(), true);
        $segments[] = self::base64UrlEncode($signature);
        return implode('.', $segments);
    }

    private static function decode(string $token): array
    {
        $segments = explode('.', $token);
        if (count($segments) !== 3) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證格式不正確。');
        }
        [$header, $payload, $signature] = $segments;
        try {
            $decodedHeader = json_decode(self::base64UrlDecode($header), true, 8, JSON_THROW_ON_ERROR);
        } catch (\Throwable) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證標頭不正確。');
        }
        if (!is_array($decodedHeader) || ($decodedHeader['alg'] ?? null) !== 'HS256'
            || ($decodedHeader['typ'] ?? null) !== 'JWT') {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證演算法不受支援。');
        }
        $expected = self::base64UrlEncode(
            hash_hmac('sha256', $header . '.' . $payload, Config::appKey(), true)
        );
        if (!hash_equals($expected, $signature)) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證簽章無效。');
        }
        try {
            $decoded = json_decode(self::base64UrlDecode($payload), true, 8, JSON_THROW_ON_ERROR);
        } catch (\Throwable) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證內容不正確。');
        }
        if (!is_array($decoded)
            || !is_string($decoded['sub'] ?? null) || !ctype_digit($decoded['sub']) || (int) $decoded['sub'] < 1
            || !is_string($decoded['jti'] ?? null)
            || !preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i', $decoded['jti'])
            || !is_int($decoded['iat'] ?? null) || !is_int($decoded['exp'] ?? null)
            || $decoded['iat'] < 1 || $decoded['iat'] > time() + 60
            || $decoded['exp'] !== $decoded['iat'] + 7200) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證必要欄位不正確。');
        }
        if ($decoded['exp'] <= time()) {
            throw new ApiException(401, 'TOKEN_EXPIRED', '登入已逾時，請重新登入。');
        }
        return $decoded;
    }

    private static function base64UrlEncode(string $value): string
    {
        return rtrim(strtr(base64_encode($value), '+/', '-_'), '=');
    }

    private static function base64UrlDecode(string $value): string
    {
        $padding = strlen($value) % 4;
        if ($padding > 0) {
            $value .= str_repeat('=', 4 - $padding);
        }
        $decoded = base64_decode(strtr($value, '-_', '+/'), true);
        if ($decoded === false) {
            throw new ApiException(401, 'TOKEN_INVALID', '登入憑證編碼不正確。');
        }
        return $decoded;
    }

    private static function uuidV4(): string
    {
        $data = random_bytes(16);
        $data[6] = chr((ord($data[6]) & 0x0f) | 0x40);
        $data[8] = chr((ord($data[8]) & 0x3f) | 0x80);
        return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
    }
}
