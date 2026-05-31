<?php

function make_multiplier($factor) {
    return function ($value) use ($factor) {
        return $value * $factor;
    };
}

$times_three = make_multiplier(3);

echo $times_three(10);
