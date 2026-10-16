<?php

declare(strict_types=1);

require dirname(__DIR__) . '/src/bootstrap.php';

use FitTrack\Config;
use FitTrack\Database;
use FitTrack\ExerciseDatasetImporter;

$defaultDataset = dirname(Config::root(), 2) . '/參考資料/exercises-dataset-main';
$datasetRoot = $argv[1] ?? $defaultDataset;
$result = ExerciseDatasetImporter::run(Database::connection(), $datasetRoot);

echo "Exercise dataset imported (" . Database::driver() . ").\n";
echo "Records: {$result['records']}\n";
echo "Database: {$result['inserted']} inserted, {$result['updated']} versioned, {$result['unchanged']} unchanged\n";
echo "Media: {$result['copied_images']} JPG copied, {$result['copied_gifs']} GIF copied\n";
echo 'Bundled seed: ' . ($result['bundled_seed_updated'] ? 'updated' : 'unchanged') . "\n";
