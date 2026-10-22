<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;

final class Seeder
{
    private const GOALS = [
        ['Muscle Gain', '增加肌肉量，以中等次數與穩定訓練量為主。'],
        ['Fat Loss', '提高活動量與訓練密度，搭配規律飲食管理。'],
        ['Strength', '以較低次數、較長休息與漸進負重提升力量。'],
        ['General Fitness', '均衡安排全身肌群，建立可持續的運動習慣。'],
    ];

    private const BODY_PARTS = [
        ['Chest', '胸部推舉與夾胸類動作。'],
        ['Back', '背部拉力與划船類動作。'],
        ['Shoulders', '肩部推舉、外展與穩定訓練。'],
        ['Biceps', '肱二頭肌彎舉類動作。'],
        ['Triceps', '肱三頭肌伸展與下壓類動作。'],
        ['Legs', '股四頭、腿後肌與小腿訓練。'],
        ['Glutes', '臀部伸髖與穩定訓練。'],
        ['Core', '腹部、軀幹抗旋轉與核心穩定訓練。'],
    ];

    public static function seed(PDO $pdo): void
    {
        $demoPassword = Config::get('DEMO_BOOTSTRAP_PASSWORD', 'Demo123456') ?? '';
        $adminPassword = Config::get('DEMO_ADMIN_PASSWORD') ?? '';
        if (!self::validPassword($demoPassword) || !self::validPassword($adminPassword)) {
            throw new \RuntimeException(
                '示範會員與管理員密碼必須是 10 至 72 bytes、包含英文字母與數字、且不得含 NUL。'
            );
        }

        Database::beginTransaction($pdo);
        try {
            $goalStatement = $pdo->prepare(
                'INSERT INTO training_goals (goal_name, description) VALUES (?, ?)'
            );
            foreach (self::GOALS as $goal) {
                $goalStatement->execute($goal);
            }

            $partStatement = $pdo->prepare(
                'INSERT INTO body_parts (body_part_name, description) VALUES (?, ?)'
            );
            foreach (self::BODY_PARTS as $part) {
                $partStatement->execute($part);
            }
            self::seedExercises($pdo);
            self::seedDemoAccounts($pdo, $demoPassword, $adminPassword);
            $pdo->commit();
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }

    /**
     * Synchronise the bundled exercise instructions without mutating history.
     *
     * Exercise versions are intentionally immutable. When the bundled seed
     * receives a wording correction (for example, Simplified to Traditional
     * Chinese), create a new version so the library and new plans use the
     * corrected text while existing workout snapshots remain reproducible.
     */
    public static function syncBundledExerciseDescriptions(PDO $pdo): int
    {
        $bundledPath = Config::root() . '/database/exercises-seed.json';
        if (!is_file($bundledPath)) {
            return 0;
        }

        $records = json_decode((string) file_get_contents($bundledPath), true);
        if (!is_array($records) || $records === []) {
            return 0;
        }

        $currentRows = $pdo->query(
            'SELECT e.exercise_id, ev.version_no, ev.exercise_name, ev.difficulty_level, '
            . 'ev.equipment, ev.description, ev.image_url '
            . 'FROM exercises e JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'WHERE ev.version_no = ('
            . 'SELECT MAX(v2.version_no) FROM exercise_versions v2 '
            . 'WHERE v2.exercise_id = e.exercise_id)'
        )->fetchAll();
        $currentByName = [];
        foreach ($currentRows as $row) {
            $currentByName[(string) $row['exercise_name']] = $row;
        }

        $updates = [];
        foreach ($records as $record) {
            if (!is_array($record)) {
                continue;
            }
            $name = trim((string) ($record['exercise_name'] ?? ''));
            $description = (string) ($record['description'] ?? '');
            if ($name === '' || $description === '' || !isset($currentByName[$name])) {
                continue;
            }
            $current = $currentByName[$name];
            if ((string) $current['description'] === $description) {
                continue;
            }
            $updates[] = [
                (int) $current['exercise_id'],
                (int) $current['version_no'] + 1,
                (string) $current['exercise_name'],
                (string) $current['difficulty_level'],
                $current['equipment'],
                $description,
                $current['image_url'],
            ];
        }

        if ($updates === []) {
            return 0;
        }

        Database::beginTransaction($pdo);
        try {
            $insert = $pdo->prepare(
                'INSERT INTO exercise_versions '
                . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
                . 'VALUES (?, ?, ?, ?, ?, ?, ?)'
            );
            foreach ($updates as $values) {
                $insert->execute($values);
            }
            $pdo->commit();
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }

        return count($updates);
    }

    private static function seedExercises(PDO $pdo): void
    {
        $workspace = dirname(Config::root(), 2);
        $datasetRoot = $workspace . '/參考資料/exercises-dataset-main';
        $jsonPath = $datasetRoot . '/data/exercises.json';
        $records = is_file($jsonPath)
            ? json_decode((string) file_get_contents($jsonPath), true)
            : [];

        $partRows = $pdo->query('SELECT body_part_id, body_part_name FROM body_parts')->fetchAll();
        $partIds = [];
        foreach ($partRows as $row) {
            $partIds[$row['body_part_name']] = (int) $row['body_part_id'];
        }

        $bundledPath = Config::root() . '/database/exercises-seed.json';
        if (is_file($bundledPath)) {
            $bundled = json_decode((string) file_get_contents($bundledPath), true);
            if (is_array($bundled) && $bundled !== []) {
                self::seedBundledExercises($pdo, $partIds, $bundled);
                return;
            }
        }

        $counts = array_fill_keys(array_keys($partIds), 0);
        $mediaDir = Config::root() . '/public/media/exercises';
        if (!is_dir($mediaDir)) {
            mkdir($mediaDir, 0775, true);
        }

        foreach (is_array($records) ? $records : [] as $record) {
            $part = self::classifyExercise($record);
            if (!isset($partIds[$part]) || $counts[$part] >= 6) {
                continue;
            }
            $gifRelative = (string) ($record['gif_url'] ?? '');
            $gifSource = $datasetRoot . '/' . $gifRelative;
            if (!is_file($gifSource)) {
                continue;
            }

            $counts[$part]++;
            $difficulty = $counts[$part] <= 3
                ? 'Beginner'
                : ($counts[$part] <= 5 ? 'Intermediate' : 'Advanced');
            $filename = basename($gifSource);
            $destination = $mediaDir . '/' . $filename;
            if (!is_file($destination)) {
                copy($gifSource, $destination);
            }
            $steps = $record['instruction_steps']['zh'] ?? [];
            $description = is_array($steps) && $steps !== []
                ? implode("\n", array_map(
                    static fn (string $step, int $index): string => ($index + 1) . '. ' . $step,
                    $steps,
                    array_keys($steps)
                ))
                : (string) ($record['instructions']['zh'] ?? $record['instructions']['en'] ?? '請依正確姿勢完成動作。');
            $description .= "\n\n媒體來源：" . (string) ($record['attribution'] ?? 'Gym visual');
            self::insertExercise($pdo, [
                trim((string) ($record['name'] ?? 'Exercise')) . ' #' . (string) ($record['id'] ?? ''),
                $partIds[$part],
                $difficulty,
                ucwords((string) ($record['equipment'] ?? 'Bodyweight')),
                mb_substr($description, 0, 4000),
                '/media/exercises/' . $filename,
            ]);
        }

        if ((int) $pdo->query('SELECT COUNT(*) FROM exercises')->fetchColumn() === 0) {
            self::seedFallbackExercises($pdo, $partIds);
        }
    }

    private static function seedBundledExercises(PDO $pdo, array $partIds, array $records): void
    {
        foreach ($records as $record) {
            $part = (string) ($record['body_part_name'] ?? '');
            if (!isset($partIds[$part])) {
                continue;
            }
            self::insertExercise($pdo, [
                (string) $record['exercise_name'],
                $partIds[$part],
                (string) $record['difficulty_level'],
                $record['equipment'] ?? null,
                (string) $record['description'],
                $record['image_url'] ?? null,
            ]);
        }
    }

    private static function classifyExercise(array $record): string
    {
        $category = mb_strtolower((string) ($record['category'] ?? ''));
        $target = mb_strtolower((string) ($record['target'] ?? ''));
        $name = mb_strtolower((string) ($record['name'] ?? ''));

        if (str_contains($target, 'triceps') || str_contains($name, 'triceps')) {
            return 'Triceps';
        }
        if (str_contains($target, 'biceps') || str_contains($name, 'curl')) {
            return 'Biceps';
        }
        if (str_contains($target, 'glute') || str_contains($name, 'hip thrust')) {
            return 'Glutes';
        }

        return match ($category) {
            'chest' => 'Chest',
            'back' => 'Back',
            'shoulders' => 'Shoulders',
            'waist' => 'Core',
            'upper legs', 'lower legs' => 'Legs',
            'upper arms' => 'Biceps',
            default => 'Core',
        };
    }

    private static function seedFallbackExercises(PDO $pdo, array $partIds): void
    {
        foreach (array_keys($partIds) as $part) {
            for ($index = 1; $index <= 3; $index++) {
                self::insertExercise($pdo, [
                    $part . ' 基礎動作 ' . $index,
                    $partIds[$part],
                    'Beginner',
                    'Bodyweight',
                    '保持穩定呼吸與可控制的動作速度。',
                    null,
                ]);
            }
        }
    }

    /** @param array{0:string,1:int,2:string,3:?string,4:string,5:?string} $values */
    private static function insertExercise(PDO $pdo, array $values): int
    {
        $exerciseId = Database::insert(
            $pdo,
            'INSERT INTO exercises (body_part_id, is_active) VALUES (?, TRUE)',
            [(int) $values[1]],
            'exercise_id'
        );
        $pdo->prepare(
            'INSERT INTO exercise_versions '
            . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
            . 'VALUES (?, 1, ?, ?, ?, ?, ?)'
        )->execute([
            $exerciseId,
            $values[0],
            $values[2],
            $values[3],
            $values[4],
            $values[5],
        ]);
        return $exerciseId;
    }

    private static function seedDemoAccounts(PDO $pdo, string $demoPassword, string $adminPassword): void
    {
        $goalId = (int) $pdo->query(
            "SELECT training_goal_id FROM training_goals WHERE goal_name='Muscle Gain'"
        )->fetchColumn();

        $createUser = static function (
            string $name,
            string $email,
            string $password,
            bool $admin
        ) use ($pdo, $goalId): int {
            $userId = Database::insert(
                $pdo,
                'INSERT INTO users '
                . '(name, gender, age, height_cm, training_experience, training_goal_id, '
                . 'training_days_per_week, training_duration_minutes) '
                . 'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                [$name, 'Other', 25, 170, 'Beginner', $goalId, 4, 60],
                'user_id'
            );
            $auth = $pdo->prepare(
                'INSERT INTO user_auth (user_id, email, password_hash) VALUES (?, ?, ?)'
            );
            $auth->execute([$userId, $email, password_hash($password, PASSWORD_BCRYPT, ['cost' => 10])]);
            if ($admin) {
                $pdo->prepare('INSERT INTO admins (user_id) VALUES (?)')->execute([$userId]);
            }
            return $userId;
        };

        $findUser = $pdo->prepare('SELECT user_id FROM user_auth WHERE email = ?');
        $findUser->execute(['demo@fittrack.local']);
        $demoUserId = (int) $findUser->fetchColumn();
        $createdDemo = $demoUserId === 0;
        if ($createdDemo) {
            $demoUserId = $createUser('示範會員', 'demo@fittrack.local', $demoPassword, false);
        }

        $findUser->execute(['admin@fittrack.local']);
        $adminUserId = (int) $findUser->fetchColumn();
        if ($adminUserId === 0) {
            $adminUserId = $createUser('系統管理員', 'admin@fittrack.local', $adminPassword, true);
        } else {
            $isAdmin = $pdo->prepare('SELECT 1 FROM admins WHERE user_id = ?');
            $isAdmin->execute([$adminUserId]);
            if (!$isAdmin->fetchColumn()) {
                $pdo->prepare('INSERT INTO admins (user_id) VALUES (?)')->execute([$adminUserId]);
            }
        }

        if (!$createdDemo) {
            return;
        }

        $parts = $pdo->query(
            "SELECT body_part_id FROM body_parts WHERE body_part_name IN ('Chest', 'Back', 'Legs', 'Core') ORDER BY body_part_id"
        )->fetchAll(PDO::FETCH_COLUMN);
        $preference = $pdo->prepare(
            'INSERT INTO user_body_parts (user_id, body_part_id, priority) VALUES (?, ?, ?)'
        );
        foreach ($parts as $index => $partId) {
            $preference->execute([$demoUserId, (int) $partId, $index + 1]);
        }
        $pdo->prepare(
            'INSERT INTO body_records (user_id, record_date, weight_kg, notes) VALUES (?, ?, ?, ?)'
        )->execute([$demoUserId, date('Y-m-d'), 68.4, '初始體重']);
        $pdo->prepare(
            'UPDATE users SET profile_completed_at = CURRENT_TIMESTAMP WHERE user_id = ?'
        )->execute([$demoUserId]);
    }

    public static function validPassword(string $password): bool
    {
        $length = strlen($password);
        return $length >= 10
            && $length <= 72
            && !str_contains($password, "\0")
            && preg_match('/[A-Za-z]/', $password) === 1
            && preg_match('/\d/', $password) === 1;
    }

    public static function ensureDemoAccounts(PDO $pdo): void
    {
        $demoPassword = Config::get('DEMO_BOOTSTRAP_PASSWORD', 'Demo123456') ?? '';
        $adminPassword = Config::get('DEMO_ADMIN_PASSWORD') ?? '';
        $lookup = $pdo->prepare('SELECT 1 FROM user_auth WHERE email = ?');
        $lookup->execute(['demo@fittrack.local']);
        $demoMissing = !$lookup->fetchColumn();
        $lookup->execute(['admin@fittrack.local']);
        $adminMissing = !$lookup->fetchColumn();
        if (($demoMissing && !self::validPassword($demoPassword))
            || ($adminMissing && !self::validPassword($adminPassword))) {
            throw new \RuntimeException(
                '示範會員與管理員密碼必須是 10 至 72 bytes、包含英文字母與數字、且不得含 NUL。'
            );
        }
        $ownsTransaction = !$pdo->inTransaction();
        if ($ownsTransaction) {
            Database::beginTransaction($pdo);
        }
        try {
            self::seedDemoAccounts($pdo, $demoPassword, $adminPassword);
            if ($ownsTransaction) {
                $pdo->commit();
            }
        } catch (\Throwable $error) {
            if ($ownsTransaction && $pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }
    }
}
