<?php
$url = 'https://raw.githubusercontent.com/dpipstudio/botwave/refs/heads/main/assets/latest.ver.txt';

$options = [
    "http" => [
        "method" => "GET",
        "header" => "User-Agent: botwavephp\r\n"
    ]
];
$context = stream_context_create($options);

$content = @file_get_contents($url, false, $context);

if ($content !== false) {
    header('Content-Type: text/plain');
    echo $content;
} else {
    http_response_code(500);
    echo "1.0.0";
}
