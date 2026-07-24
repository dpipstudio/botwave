<?php
define('PASSKEY', '6969'); // i feel like making a config.php for this is a bit overkill
define('LATEST_FILE', __DIR__ . '/latest.txt');

header('Content-Type: text/plain');

// update mode: ?pwd=<passkey>&proto=<proto>&release=<release>
if (isset($_GET['pwd'])) {
    if (!hash_equals(PASSKEY, (string)$_GET['pwd'])) {
        http_response_code(403);
        echo "forbidden\n";
        exit;
    }

    $proto = trim($_GET['proto'] ?? '');
    $release = trim($_GET['release'] ?? '');

    if ($proto === '' || $release === '') {
        http_response_code(400);
        echo "missing proto or release\n";
        exit;
    }

    file_put_contents(LATEST_FILE, $proto . "\n" . $release . "\n", LOCK_EX);

    echo "updated\n";
    exit;
}

if (!file_exists(LATEST_FILE)) {
    http_response_code(404);
    echo "not found\n";
    exit;
}

echo file_get_contents(LATEST_FILE);