<?php

$fiberA = new Fiber(function () {
    echo "A start\n";
    Fiber::suspend();
    echo "A done\n";
});

$fiberB = new Fiber(function () {
    echo "B start\n";
    Fiber::suspend();
    echo "B done\n";
});

$fiberA->start();
$fiberB->start();

$fiberA->resume();
$fiberB->resume();
