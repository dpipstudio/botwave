#!/bin/bash
set -e

RELEASES_FILE="assets/releases.txt"

if [ ! -f "$RELEASES_FILE" ]; then
    echo "Error: $RELEASES_FILE not found"
    exit 1
fi

parse_latest_release() {
    local in_release=false
    local version=""
    local description=""
    
    while IFS= read -r line; do
        if [[ -z "$line" ]]; then
            continue
        fi
        
        if [[ "$in_release" = false ]] && [[ "$line" =~ ^# ]]; then
            continue
        fi

        if [[ "$line" =~ ^=---[[:space:]]*(.+)[[:space:]]*---= ]]; then
            if [ "$in_release" = false ]; then
                version="${BASH_REMATCH[1]}"
                version=$(echo "$version" | xargs | tr -d '\r')
                in_release=true
                continue
            fi
        fi

        if [[ "$line" =~ ^=---[[:space:]]*END[[:space:]]*---= ]]; then
            if [ "$in_release" = true ]; then
                break
            fi
        fi

        if [ "$in_release" = true ]; then
            line=$(echo "$line" | tr -d '\r')
            if [ -n "$description" ]; then
                description="$description"$'\n'"$line"
            else
                description="$line"
            fi
        fi
    done < "$RELEASES_FILE"

    echo "$version"
    echo "---DESCRIPTION---"
    echo "$description"
}

latest_version=""
latest_description=""
in_desc=false

while IFS= read -r line; do
    if [ -z "$latest_version" ]; then
        latest_version="$line"
    elif [ "$line" = "---DESCRIPTION---" ]; then
        in_desc=true
    elif [ "$in_desc" = true ]; then
        if [ -n "$latest_description" ]; then
            latest_description="$latest_description"$'\n'"$line"
        else
            latest_description="$line"
        fi
    fi
done < <(parse_latest_release)

if [ -z "$latest_version" ]; then
    echo "Error: Could not parse latest release from $RELEASES_FILE"
    exit 1
fi

echo "Latest version in releases.txt: $latest_version" >&2

if git rev-parse "$latest_version" >/dev/null 2>&1; then
    echo "Release $latest_version already exists" >&2
    echo "new_release=false" >> $GITHUB_OUTPUT
    exit 0
fi

echo "New release detected: $latest_version" >&2
echo "new_release=true" >> $GITHUB_OUTPUT
echo "version=$latest_version" >> $GITHUB_OUTPUT

echo "$latest_description" > /tmp/release-description.txt
echo "description_file=/tmp/release-description.txt" >> $GITHUB_OUTPUT

previous_commit=""
if [ -f "assets/installation.json" ]; then
    previous_commit=$(grep -oP '"commit":\s*"\K[^"]+' assets/installation.json | head -n 1)
fi

if [ -z "$previous_commit" ]; then
    previous_commit=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
fi

echo "previous_commit=$previous_commit" >> $GITHUB_OUTPUT
echo "Previous commit/tag: $previous_commit" >&2