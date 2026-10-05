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
        $pdo->beginTransaction();
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
            $pdo->commit();
        } catch (\Throwable $error) {
            $pdo->rollBack();
            throw $error;
        }

        self::seedExercises($pdo);
        self::seedDemoAccounts($pdo);
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
        $insert = $pdo->prepare(
            'INSERT INTO exercises '
            . '(exercise_name, body_part_id, difficulty_level, equipment, description, image_url, is_active) '
            . 'VALUES (?, ?, ?, ?, ?, ?, TRUE)'
        );
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
            $insert->execute([
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
        $insert = $pdo->prepare(
            'INSERT INTO exercises '
            . '(exercise_name, body_part_id, difficulty_level, equipment, description, image_url, is_active) '
            . 'VALUES (?, ?, ?, ?, ?, ?, TRUE)'
        );
        foreach ($records as $record) {
            $part = (string) ($record['body_part_name'] ?? '');
            if (!isset($partIds[$part])) {
                continue;
            }
            $insert->execute([
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
        $insert = $pdo->prepare(
            'INSERT INTO exercises '
            . '(exercise_name, body_part_id, difficulty_level, equipment, description, image_url, is_active) '
            . 'VALUES (?, ?, ?, ?, ?, NULL, TRUE)'
        );
        foreach (array_keys($partIds) as $part) {
            for ($index = 1; $index <= 3; $index++) {
                $insert->execute([
                    $part . ' 基礎動作 ' . $index,
                    $partIds[$part],
                    'Beginner',
                    'Bodyweight',
                    '保持穩定呼吸與可控制的動作速度。',
                ]);
            }
        }
    }

    private static function seedDemoAccounts(PDO $pdo): void
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

        $demoPassword = Config::get('DEMO_BOOTSTRAP_PASSWORD', 'Demo12345') ?? '';
        $adminPassword = Config::get('ADMIN_BOOTSTRAP_PASSWORD', 'Admin12345') ?? '';
        if (strlen($demoPassword) < 8 || strlen($adminPassword) < 8) {
            throw new \RuntimeException('示範會員與管理員初始密碼至少需要 8 個字元。');
        }

        $demoUserId = $createUser('示範會員', 'demo@fittrack.local', $demoPassword, false);
        $createUser('系統管理員', 'admin@fittrack.local', $adminPassword, true);

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
    }
}
