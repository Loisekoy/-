<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$mediaRoot = $root . '/public/media/exercises';
$outputPath = $argv[1] ?? ($root . '/docs/validation/media-sha256.txt');

if (!is_dir($mediaRoot)) {
    fwrite(STDERR, "Exercise media directory not found.\n");
    exit(1);
}

$paths = [];
$iterator = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($mediaRoot, FilesystemIterator::SKIP_DOTS)
);
foreach ($iterator as $file) {
    if (!$file->isFile() || !in_array(strtolower($file->getExtension()), ['gif', 'jpg', 'jpeg', 'png', 'webp'], true)) {
        continue;
    }
    $absolute = $file->getPathname();
    $paths[] = substr($absolute, strlen($root) + 1);
}
sort($paths, SORT_STRING);

$lines = [
    '# FitTrack exercise media SHA-256 manifest',
    '# Paths are relative to the PHP application root.',
];
foreach ($paths as $relative) {
    $hash = hash_file('sha256', $root . '/' . $relative);
    if ($hash === false) {
        throw new RuntimeException("Unable to hash {$relative}");
    }
    $lines[] = $hash . '  ' . $relative;
}

$directory = dirname($outputPath);
if (!is_dir($directory) && !mkdir($directory, 0775, true) && !is_dir($directory)) {
    throw new RuntimeException("Unable to create {$directory}");
}
$temporary = $outputPath . '.tmp-' . getmypid();
if (file_put_contents($temporary, implode(PHP_EOL, $lines) . PHP_EOL, LOCK_EX) === false
    || !rename($temporary, $outputPath)) {
    @unlink($temporary);
    throw new RuntimeException("Unable to write {$outputPath}");
}

echo "Media manifest written: " . count($paths) . " files.\n";
