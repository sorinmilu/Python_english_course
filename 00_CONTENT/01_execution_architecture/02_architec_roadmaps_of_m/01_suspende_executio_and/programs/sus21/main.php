<?php

function count_up_to($limit) {
    $current = 1;

    while ($current <= $limit) {
        yield $current;
        $current += 1;
    }
}

foreach (count_up_to(3) as $value) {
    echo $value . PHP_EOL;
}
