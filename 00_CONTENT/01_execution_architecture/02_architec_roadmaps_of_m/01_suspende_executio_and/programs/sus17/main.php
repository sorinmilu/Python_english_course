<?php

function accumulator() {
    $total = 0;

    while (true) {
        $value = yield $total;
        $total += $value;
    }
}

$acc = accumulator();

echo $acc->current() . PHP_EOL; // starts, yields 0

$acc->send(5);
echo $acc->current() . PHP_EOL; // 5

$acc->send(7);
echo $acc->current() . PHP_EOL; // 12
