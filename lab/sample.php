<?php

$s = str_repeat('A', 3000000);
serialize($s);
echo "done\n";
