<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$manifestPath = $argv[1] ?? ($root . '/docs/validation/media-sha256.txt');
if (!is_file($manifestPath)) {
    fwrite(STDERR, "Media manifest not found: {$manifestPath}\n");
    exit(1);
}

$listed = [];
foreach (file($manifestPath, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
    if ($line === '' || str_starts_with($line, '#')) {
        continue;
    }
    if (!preg_match('/^([a-f0-9]{64})  (public\/media\/exercises\/[A-Za-z0-9._-]+)$/', $line, $matches)) {
        throw new RuntimeException("Invalid media manifest line: {$line}");
    }
    [$unused, $expected, $relative] = $matches;
    $absolute = $root . '/' . $relative;
    if (!is_file($absolute)) {
        throw new RuntimeException("Missing media file: {$relative}");
    }
    $actual = hash_file('sha256', $absolute);
    if (!hash_equals($expected, (string) $actual)) {
        throw new RuntimeException("SHA-256 mismatch: {$relative}");
    }
    $listed[$relative] = true;
}

$actualPaths = [];
$iterator = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($root . '/public/media/exercises', FilesystemIterator::SKIP_DOTS)
);
foreach ($iterator as $file) {
    if ($file->isFile() && in_array(strtolower($file->getExtension()), ['gif', 'jpg', 'jpeg', 'png', 'webp'], true)) {
        $actualPaths['public/media/exercises/' . $file->getFilename()] = true;
    }
}
$unlisted = array_diff_key($actualPaths, $listed);
if ($unlisted !== []) {
    throw new RuntimeException('Manifest is missing media files: ' . implode(', ', array_slice(array_keys($unlisted), 0, 5)));
}

echo 'PASS: media SHA-256 manifest verified (' . count($listed) . " files).\n";
