#!/bin/bash
set -e

VERSION="$1"
PREVIOUS_COMMIT="$2"

if [ -z "$VERSION" ]; then
    echo "Error: VERSION not provided"
    exit 1
fi

RELEASE_NOTES="release-notes.md"
DESCRIPTION_FILE="/tmp/release-description.txt"

{
    # description at the top
    if [ -f "$DESCRIPTION_FILE" ]; then
        cat "$DESCRIPTION_FILE"
    fi
    echo ""
    echo "### Updating to this version"
    echo ""
    echo "To update to this version, run the following command:"
    echo ""
    echo '```bash'
    echo "bw-update --to $VERSION"
    echo '```'
    echo ""

    if [ -n "$PREVIOUS_COMMIT" ]; then
        echo ""

        echo "<details>"
        echo "<summary>Commit history</summary>"
        echo ""

        if git rev-parse "$PREVIOUS_COMMIT" >/dev/null 2>&1; then
            git log --pretty=format:"- %s (\`%h\`)" "$PREVIOUS_COMMIT"..HEAD
        else
            git log --pretty=format:"- %s (\`%h\`)" --max-count=50
        fi

        echo ""
        echo "</details>"
    fi
} > "$RELEASE_NOTES"

echo "Release notes generated in $RELEASE_NOTES"
cat "$RELEASE_NOTES"