<?php

declare(strict_types=1);

spl_autoload_register(static function (string $class): void {
    $prefix = 'FitTrack\\';
    if (!str_starts_with($class, $prefix)) {
        return;
    }
    $relative = substr($class, strlen($prefix));
    $path = __DIR__ . '/' . str_replace('\\', '/', $relative) . '.php';
    if (is_file($path)) {
        require $path;
    }
});

date_default_timezone_set('Asia/Taipei');

\FitTrack\Config::load();
