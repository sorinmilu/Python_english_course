<?php

$fiber = new Fiber(function () {
    echo "before wait\n";

    Fiber::suspend("waiting");

    echo "after wait\n";
});

$value = $fiber->start();
echo $value . PHP_EOL;

$fiber->resume();
