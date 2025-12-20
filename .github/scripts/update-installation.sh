#!/bin/bash
set -e

VERSION="$1"
COMMIT_SHA="$2"

if [ -z "$VERSION" ] || [ -z "$COMMIT_SHA" ]; then
    echo "Error: VERSION and COMMIT_SHA must be provided"
    exit 1
fi

INSTALLATION_FILE="assets/installation.json"

if [ ! -f "$INSTALLATION_FILE" ]; then
    echo "Error: $INSTALLATION_FILE not found"
    exit 1
fi

TEMP_FILE=$(mktemp)

jq --arg version "$VERSION" --arg commit "$COMMIT_SHA" \
    '.releases = [{codename: $version, commit: $commit}] + .releases' \
    "$INSTALLATION_FILE" > "$TEMP_FILE"

mv "$TEMP_FILE" "$INSTALLATION_FILE"

echo "Updated $INSTALLATION_FILE with release $VERSION (commit: $COMMIT_SHA)"