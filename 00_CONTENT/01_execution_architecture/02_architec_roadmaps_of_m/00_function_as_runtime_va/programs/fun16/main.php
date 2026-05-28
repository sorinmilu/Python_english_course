<?php

$values = [1, 2, 3, 4];

$result = array_map(function ($x) {
    return $x * $x;
}, $values);

print_r($result);
