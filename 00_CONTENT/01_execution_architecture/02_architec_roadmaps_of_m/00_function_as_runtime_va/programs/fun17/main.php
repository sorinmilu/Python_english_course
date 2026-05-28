<?php

function make_counter() {
    $count = 0;

    return function () use (&$count) {
        $count += 1;
        return $count;
    };
}

$counter = make_counter();

echo $counter(); // 1
echo $counter(); // 2
echo $counter(); // 3
