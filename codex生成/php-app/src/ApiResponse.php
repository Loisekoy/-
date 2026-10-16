<?php

declare(strict_types=1);

namespace FitTrack;

use DateTimeImmutable;
use DateTimeZone;

final class ApiResponse
{
    public static function normalize(mixed $value, ?string $key = null): mixed
    {
        if (is_array($value)) {
            foreach ($value as $childKey => $childValue) {
                $value[$childKey] = self::normalize(
                    $childValue,
                    is_string($childKey) ? $childKey : null
                );
            }
            return $value;
        }

        if (!is_string($value) || $key === null || !str_ends_with($key, '_at')) {
            return $value;
        }

        try {
            if (preg_match('/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?$/', $value)) {
                $timestamp = new DateTimeImmutable($value, new DateTimeZone('UTC'));
            } else {
                $timestamp = new DateTimeImmutable($value);
            }
            return $timestamp->setTimezone(new DateTimeZone('UTC'))->format('Y-m-d\TH:i:s\Z');
        } catch (\Throwable) {
            return $value;
        }
    }
}
