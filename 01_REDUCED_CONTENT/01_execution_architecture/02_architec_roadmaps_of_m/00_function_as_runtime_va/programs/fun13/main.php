<?php

$users = [
    ["name" => "Ana", "age" => 30],
    ["name" => "Mihai", "age" => 20],
];

usort($users, function ($a, $b) {
    return $a["age"] <=> $b["age"];
});

print_r($users);
