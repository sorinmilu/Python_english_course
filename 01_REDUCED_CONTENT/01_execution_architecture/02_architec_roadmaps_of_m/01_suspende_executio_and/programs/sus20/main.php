<?php

function non_empty_lines($path) {
    $file = fopen($path, "r");

    while (($line = fgets($file)) !== false) {
        $line = trim($line);

        if ($line !== "") {
            yield $line;
        }
    }

    fclose($file);
}

foreach (non_empty_lines("log.txt") as $line) {
    echo $line . PHP_EOL;
}
