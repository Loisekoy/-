<?php

declare(strict_types=1);

namespace FitTrack;

use PDO;
use RuntimeException;

final class ExerciseDatasetImporter
{
    private const BODY_PARTS = [
        'Chest',
        'Back',
        'Shoulders',
        'Biceps',
        'Triceps',
        'Legs',
        'Glutes',
        'Core',
    ];

    /**
     * @return array{
     *     records:int,
     *     inserted:int,
     *     updated:int,
     *     unchanged:int,
     *     copied_images:int,
     *     copied_gifs:int,
     *     bundled_seed_updated:bool
     * }
     */
    public static function run(PDO $pdo, string $datasetRoot): array
    {
        $records = self::loadRecords($datasetRoot);
        $mediaDirectory = Config::root() . '/public/media/exercises';
        if (!is_dir($mediaDirectory) && !mkdir($mediaDirectory, 0775, true) && !is_dir($mediaDirectory)) {
            throw new RuntimeException('無法建立動作媒體目錄。');
        }

        $copiedImages = 0;
        $copiedGifs = 0;
        foreach ($records as $record) {
            if (self::copyIfChanged($record['_image_source'], $mediaDirectory . '/' . basename($record['_image_source']))) {
                $copiedImages++;
            }
            if (self::copyIfChanged($record['_gif_source'], $mediaDirectory . '/' . basename($record['_gif_source']))) {
                $copiedGifs++;
            }
        }

        $bundleRecords = array_map(static fn (array $record): array => [
            'exercise_name' => $record['exercise_name'],
            'body_part_name' => $record['body_part_name'],
            'difficulty_level' => $record['difficulty_level'],
            'equipment' => $record['equipment'],
            'description' => $record['description'],
            'image_url' => $record['image_url'],
        ], $records);
        $bundleUpdated = self::writeBundle($bundleRecords);

        $partRows = $pdo->query('SELECT body_part_id, body_part_name FROM body_parts')->fetchAll();
        $partIds = [];
        foreach ($partRows as $row) {
            $partIds[(string) $row['body_part_name']] = (int) $row['body_part_id'];
        }
        foreach (self::BODY_PARTS as $part) {
            if (!isset($partIds[$part])) {
                throw new RuntimeException("資料庫缺少身體部位：{$part}");
            }
        }

        $currentRows = $pdo->query(
            'SELECT e.exercise_id, e.body_part_id, ev.version_no, ev.exercise_name, '
            . 'ev.difficulty_level, ev.equipment, ev.description, ev.image_url '
            . 'FROM exercises e JOIN exercise_versions ev ON ev.exercise_id = e.exercise_id '
            . 'WHERE ev.version_no = ('
            . 'SELECT MAX(v2.version_no) FROM exercise_versions v2 WHERE v2.exercise_id = e.exercise_id)'
        )->fetchAll();
        $currentByDatasetId = [];
        foreach ($currentRows as $row) {
            if (preg_match('/#([0-9]+)$/', (string) $row['exercise_name'], $matches)) {
                $currentByDatasetId[$matches[1]] = $row;
            }
        }

        $inserted = 0;
        $updated = 0;
        $unchanged = 0;
        Database::beginTransaction($pdo);
        try {
            foreach ($records as $record) {
                $partId = $partIds[$record['body_part_name']];
                $current = $currentByDatasetId[$record['_dataset_id']] ?? null;
                if ($current === null) {
                    self::insertExercise($pdo, $record, $partId);
                    $inserted++;
                    continue;
                }

                $changed = (int) $current['body_part_id'] !== $partId
                    || (string) $current['exercise_name'] !== $record['exercise_name']
                    || (string) $current['difficulty_level'] !== $record['difficulty_level']
                    || (string) ($current['equipment'] ?? '') !== (string) ($record['equipment'] ?? '')
                    || (string) $current['description'] !== $record['description']
                    || (string) ($current['image_url'] ?? '') !== (string) ($record['image_url'] ?? '');
                if (!$changed) {
                    $unchanged++;
                    continue;
                }

                $exerciseId = (int) $current['exercise_id'];
                if ((int) $current['body_part_id'] !== $partId) {
                    $pdo->prepare('UPDATE exercises SET body_part_id = ? WHERE exercise_id = ?')
                        ->execute([$partId, $exerciseId]);
                }
                $pdo->prepare(
                    'INSERT INTO exercise_versions '
                    . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
                    . 'VALUES (?, ?, ?, ?, ?, ?, ?)'
                )->execute([
                    $exerciseId,
                    (int) $current['version_no'] + 1,
                    $record['exercise_name'],
                    $record['difficulty_level'],
                    $record['equipment'],
                    $record['description'],
                    $record['image_url'],
                ]);
                $updated++;
            }
            $pdo->commit();
        } catch (\Throwable $error) {
            if ($pdo->inTransaction()) {
                $pdo->rollBack();
            }
            throw $error;
        }

        return [
            'records' => count($records),
            'inserted' => $inserted,
            'updated' => $updated,
            'unchanged' => $unchanged,
            'copied_images' => $copiedImages,
            'copied_gifs' => $copiedGifs,
            'bundled_seed_updated' => $bundleUpdated,
        ];
    }

    /** @return list<array<string, mixed>> */
    private static function loadRecords(string $datasetRoot): array
    {
        $jsonPath = rtrim($datasetRoot, '/') . '/data/exercises.json';
        if (!is_file($jsonPath)) {
            throw new RuntimeException("找不到動作資料：{$jsonPath}");
        }
        $decoded = json_decode((string) file_get_contents($jsonPath), true, 512, JSON_THROW_ON_ERROR);
        if (!is_array($decoded) || $decoded === []) {
            throw new RuntimeException('動作資料集是空的。');
        }

        $seenIds = [];
        $partOrdinals = array_fill_keys(self::BODY_PARTS, 0);
        $normalized = [];
        foreach ($decoded as $index => $source) {
            if (!is_array($source)) {
                throw new RuntimeException('動作資料格式不正確，索引：' . $index);
            }
            $datasetId = trim((string) ($source['id'] ?? ''));
            if ($datasetId === '' || isset($seenIds[$datasetId])) {
                throw new RuntimeException("動作資料集 ID 缺漏或重複：{$datasetId}");
            }
            $seenIds[$datasetId] = true;

            $bodyPart = self::classifyExercise($source);
            $partOrdinals[$bodyPart]++;
            $position = (($partOrdinals[$bodyPart] - 1) % 6) + 1;
            $difficulty = $position <= 3 ? 'Beginner' : ($position <= 5 ? 'Intermediate' : 'Advanced');
            $suffix = ' #' . $datasetId;
            $rawName = trim((string) ($source['name'] ?? 'Exercise'));
            $name = mb_substr($rawName, 0, 120 - mb_strlen($suffix)) . $suffix;
            $imageRelative = self::validatedMediaPath((string) ($source['image'] ?? ''), 'images', ['jpg', 'jpeg', 'png', 'webp']);
            $gifRelative = self::validatedMediaPath((string) ($source['gif_url'] ?? ''), 'videos', ['gif']);
            $imageSource = rtrim($datasetRoot, '/') . '/' . $imageRelative;
            $gifSource = rtrim($datasetRoot, '/') . '/' . $gifRelative;
            if (!is_file($imageSource) || !is_file($gifSource)) {
                throw new RuntimeException("動作 {$datasetId} 缺少 JPG 或 GIF 媒體檔。");
            }

            $steps = $source['instruction_steps']['zh'] ?? [];
            if (!is_array($steps) || $steps === []) {
                $fallback = trim((string) ($source['instructions']['zh'] ?? $source['instructions']['en'] ?? ''));
                $steps = $fallback === '' ? ['請依正確姿勢完成動作。'] : [$fallback];
            }
            $description = implode("\n", array_map(
                static fn (mixed $step, int $stepIndex): string => ($stepIndex + 1) . '. ' . trim((string) $step),
                $steps,
                array_keys($steps)
            ));
            $description .= "\n\n媒體來源：" . trim((string) ($source['attribution'] ?? 'Gym visual'));

            $normalized[] = [
                '_dataset_id' => $datasetId,
                '_image_source' => $imageSource,
                '_gif_source' => $gifSource,
                'exercise_name' => $name,
                'body_part_name' => $bodyPart,
                'difficulty_level' => $difficulty,
                'equipment' => mb_substr(ucwords(trim((string) ($source['equipment'] ?? 'Bodyweight'))), 0, 100),
                'description' => mb_substr($description, 0, 4000),
                'image_url' => '/media/exercises/' . basename($gifSource),
            ];
        }

        return $normalized;
    }

    private static function classifyExercise(array $record): string
    {
        $category = mb_strtolower((string) ($record['category'] ?? ''));
        $target = mb_strtolower((string) ($record['target'] ?? ''));
        $name = mb_strtolower((string) ($record['name'] ?? ''));

        if (str_contains($target, 'triceps') || str_contains($name, 'triceps')) {
            return 'Triceps';
        }
        if (str_contains($target, 'biceps') || str_contains($target, 'forearm') || str_contains($name, 'curl')) {
            return 'Biceps';
        }
        if (str_contains($target, 'glute') || str_contains($name, 'hip thrust')) {
            return 'Glutes';
        }
        if (in_array($target, ['lats', 'traps', 'upper back'], true)) {
            return 'Back';
        }

        return match ($category) {
            'chest' => 'Chest',
            'back' => 'Back',
            'shoulders', 'neck' => 'Shoulders',
            'upper arms', 'lower arms' => 'Biceps',
            'upper legs', 'lower legs' => 'Legs',
            'waist', 'cardio' => 'Core',
            default => 'Core',
        };
    }

    /** @param list<string> $extensions */
    private static function validatedMediaPath(string $path, string $directory, array $extensions): string
    {
        $path = str_replace('\\', '/', trim($path));
        $extension = mb_strtolower((string) pathinfo($path, PATHINFO_EXTENSION));
        if (!preg_match('#^' . preg_quote($directory, '#') . '/[A-Za-z0-9._-]+$#', $path)
            || !in_array($extension, $extensions, true)) {
            throw new RuntimeException("不合法的動作媒體路徑：{$path}");
        }
        return $path;
    }

    private static function copyIfChanged(string $source, string $destination): bool
    {
        if (is_file($destination)
            && filesize($source) === filesize($destination)
            && hash_file('sha256', $source) === hash_file('sha256', $destination)) {
            return false;
        }
        if (!copy($source, $destination)) {
            throw new RuntimeException("無法複製媒體檔：{$source}");
        }
        return true;
    }

    /** @param list<array<string, mixed>> $records */
    private static function writeBundle(array $records): bool
    {
        $path = Config::root() . '/database/exercises-seed.json';
        $json = json_encode($records, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n";
        if (is_file($path) && (string) file_get_contents($path) === $json) {
            return false;
        }
        $temporary = tempnam(dirname($path), 'exercise-seed-');
        if ($temporary === false || file_put_contents($temporary, $json, LOCK_EX) === false
            || !rename($temporary, $path)) {
            if (is_string($temporary) && is_file($temporary)) {
                unlink($temporary);
            }
            throw new RuntimeException('無法更新動作種子資料。');
        }
        return true;
    }

    /** @param array<string, mixed> $record */
    private static function insertExercise(PDO $pdo, array $record, int $bodyPartId): void
    {
        $exerciseId = Database::insert(
            $pdo,
            'INSERT INTO exercises (body_part_id, is_active) VALUES (?, TRUE)',
            [$bodyPartId],
            'exercise_id'
        );
        $pdo->prepare(
            'INSERT INTO exercise_versions '
            . '(exercise_id, version_no, exercise_name, difficulty_level, equipment, description, image_url) '
            . 'VALUES (?, 1, ?, ?, ?, ?, ?)'
        )->execute([
            $exerciseId,
            $record['exercise_name'],
            $record['difficulty_level'],
            $record['equipment'],
            $record['description'],
            $record['image_url'],
        ]);
    }
}
