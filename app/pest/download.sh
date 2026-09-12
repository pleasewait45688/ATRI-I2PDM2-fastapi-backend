#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Optional dev convenience only — Docker builds no longer call this script,
# they expect model files to already exist in ./model (see app/pest/model/README).
# Set DROPBOX_URL yourself before running this, it is never committed here.
if [ -z "$DROPBOX_URL" ]; then
    echo "DROPBOX_URL is not set. Export your own link before running this script, e.g.:"
    echo "  DROPBOX_URL='https://www.dropbox.com/scl/fi/.../model.zip?...&dl=0' ./download.sh"
    exit 1
fi
ZIP_FILE="model.zip"                  # Name of the downloaded zip file

# Ensure we're operating in the script's directory
cd "$SCRIPT_DIR"

# Remove the existing "model" directory, if it exists
rm -rf model

# Modify Dropbox link to enable direct download (`?dl=0` -> `?dl=1`)
DOWNLOAD_URL="${DROPBOX_URL/?dl=0/?dl=1}"

# Use wget to download the zip file
echo "Downloading file $ZIP_FILE from Dropbox..."
wget -O $ZIP_FILE $DOWNLOAD_URL
if [ $? -ne 0 ]; then
    echo "Download failed! Please check if the Dropbox link is correct."
    exit 1
fi
echo "Download completed!"

# Unzip the file
echo "Unzipping file $ZIP_FILE..."
unzip $ZIP_FILE
if [ $? -ne 0 ]; then
    echo "Unzip failed! Please check if the zip file is valid."
    exit 1
fi
echo "Unzipping completed! Directory structure restored."

# Clean up the zip file
rm -f $ZIP_FILE
