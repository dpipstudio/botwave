#!/bin/bash
set -e

VERSION="$1"
DESCRIPTION="$2"
PREVIOUS_COMMIT="$3"

if [ -z "$VERSION" ]; then
    echo "Error: VERSION not provided"
    exit 1
fi

RELEASE_NOTES="release-notes.md"

{
    # description at the top
    echo "$DESCRIPTION"
    echo "<h3>Updating to this version</h3>"
    echo "<p> To update to this version, run the following command.</p>"
    echo "<pre>bw-update --to $VERSION</pre>"
    echo ""

    if [ -n "$PREVIOUS_COMMIT" ]; then
        echo ""

        echo "<details>"
        echo "<summary><code>Commit history</code></summary>"
        echo "<ul>"

        if git rev-parse "$PREVIOUS_COMMIT" >/dev/null 2>&1; then
            git log --pretty=format:"<li>%s (<code>%h</code>)</li>" "$PREVIOUS_COMMIT"..HEAD
        else
            git log --pretty=format:"<li>%s (<code>%h</code>)</li>" --max-count=50
        fi

        echo "</ul>"
        echo "</details>"
    fi
} > "$RELEASE_NOTES"

echo "Release notes generated in $RELEASE_NOTES"
cat "$RELEASE_NOTES"
