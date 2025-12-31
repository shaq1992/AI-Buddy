#!/bin/bash

# ==============================================================================
# Configuration
# ==============================================================================

# Name of the folder where the dump files will be saved
OUTPUT_DIR="code_dump"

# Regex pattern for files/folders to ignore (passed to grep -vE)
# We strictly ignore the OUTPUT_DIR to avoid scanning generated files
IGNORE_FILES_OR_FOLDER="(\.git|__pycache__|venv|env|\.idea|\.vscode|\.DS_Store|$OUTPUT_DIR)"

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# ==============================================================================
# Helper Function
# ==============================================================================

generate_dump() {
    local TARGET_DIR="$1"
    local OUTPUT_FILENAME="$2"
    local MAX_DEPTH="$3"       # Pass "-maxdepth 1" for root, or empty string for recursive
    local INCLUDE_REQS="$4"    # "yes" to include requirements.txt, "no" otherwise

    # Temp file to build content; ensures we don't create empty files if no code exists
    local TEMP_FILE=".temp_dump_creation"
    > "$TEMP_FILE"

    echo "Scanning: $TARGET_DIR ..."

    # 1. Build the find command dynamically
    # We always look for .py, Dockerfile, docker-compose.yml
    local FIND_CMD="find \"$TARGET_DIR\" $MAX_DEPTH -type f \( -name \"*.py\" -o -name \"Dockerfile\" -o -name \"docker-compose.yml\""

    # Add requirements.txt only if requested (usually for root only)
    if [ "$INCLUDE_REQS" == "yes" ]; then
        FIND_CMD="$FIND_CMD -o -name \"requirements.txt\""
    fi

    # Close the find parentheses
    FIND_CMD="$FIND_CMD \)"

    # 2. Execute Find -> Filter (Ignore) -> Sort -> Loop
    # We use eval because the command string contains quotes and parentheses
    eval "$FIND_CMD" | grep -vE "$IGNORE_FILES_OR_FOLDER" | sort | while read -r filepath; do
        
        # Clean path for display (remove leading ./ if present)
        local clean_path="${filepath#./}"

        # PRINT TO CONSOLE (The requested change)
        echo "    -> Adding: $clean_path"

        # Write XML Tags and Content to temp file
        echo "<$clean_path>" >> "$TEMP_FILE"
        cat "$filepath" >> "$TEMP_FILE"
        echo -e "\n</$clean_path>\n" >> "$TEMP_FILE"
    done

    # 3. Finalize
    # Check if temp file has content (size > 0). If so, move to final output folder.
    if [ -s "$TEMP_FILE" ]; then
        mv "$TEMP_FILE" "$OUTPUT_DIR/$OUTPUT_FILENAME"
        echo "  [OK] Created $OUTPUT_DIR/$OUTPUT_FILENAME"
    else
        rm -f "$TEMP_FILE"
        echo "  [SKIP] No matching files found in $TARGET_DIR"
    fi
}

# ==============================================================================
# Main Execution Logic
# ==============================================================================

echo "Starting Code Dump..."
echo "Target Folder: $OUTPUT_DIR"
echo "Ignore Pattern: $IGNORE_FILES_OR_FOLDER"
echo "----------------------------------------"

# 1. Process Root Directory
# Depth 1 (non-recursive), Include requirements.txt = yes
generate_dump "." "root_folder_code_dump.txt" "-maxdepth 1" "yes"

# 2. Process Sub-directories
# Iterate over all directories in current path
for dir in */; do
    # Remove trailing slash (e.g., "app/" -> "app")
    dir_name="${dir%/}"

    # Check if the folder itself should be ignored
    if echo "$dir_name" | grep -qE "$IGNORE_FILES_OR_FOLDER"; then
        continue
    fi

    # Depth unlimited (recursive), Include requirements.txt = no
    generate_dump "$dir_name" "${dir_name}_code_dump.txt" "" "no"
done

echo "----------------------------------------"
echo "Done."