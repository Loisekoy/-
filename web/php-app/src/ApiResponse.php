<?php

declare(strict_types=1);

namespace FitTrack;

use DateTimeImmutable;
use DateTimeZone;

final class ApiResponse
{
    private const DECIMAL_KEYS = [
        'height_cm',
        'height_cm_snapshot',
        'weight_kg',
        'weight_kg_snapshot',
        'current_weight_kg',
        'target_weight_kg',
        'set_volume',
        'total_volume',
        'weighted_volume',
        'external_load_volume_kg_reps',
        'latest_weight',
        'average_weight',
        'weight',
        'volume',
    ];

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

        if ($key !== null && in_array($key, self::DECIMAL_KEYS, true)
            && $value !== null && (is_int($value) || is_float($value) || is_numeric($value))) {
            return number_format((float) $value, 2, '.', '');
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
