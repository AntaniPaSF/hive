#!/usr/bin/env bash
set -euo pipefail

VERSION_FILE="VERSION"
DIST_DIR="dist"
IMAGE_NAME="hive-assistant"
TAG="local"

mkdir -p "${DIST_DIR}"
VERSION=$(cat "${VERSION_FILE}" 2>/dev/null || echo "0.1.0")

# Build image
echo "[package] Building image ${IMAGE_NAME}:${VERSION}..."
docker build -t "${IMAGE_NAME}:${VERSION}" .

# Save image to tar
TAR_PATH="${DIST_DIR}/${IMAGE_NAME}-${VERSION}.tar"
docker save "${IMAGE_NAME}:${VERSION}" -o "${TAR_PATH}"

# Checksums and manifest
SHA256=$(sha256sum "${TAR_PATH}" | awk '{print $1}')
CHECKSUMS_PATH="${DIST_DIR}/checksums.txt"
echo "${SHA256}  $(basename "${TAR_PATH}")" > "${CHECKSUMS_PATH}"

MANIFEST_PATH="${DIST_DIR}/manifest.json"
cat > "${MANIFEST_PATH}" <<JSON
{
  "name": "${IMAGE_NAME}",
  "version": "${VERSION}",
  "created": "$(date -Iseconds)",
  "files": [
    { "path": "$(basename "${TAR_PATH}")", "sha256": "${SHA256}" },
    { "path": "checksums.txt", "sha256": "$(sha256sum "${CHECKSUMS_PATH}" | awk '{print $1}')" }
  ]
}
JSON

echo "[package] Artifact: ${TAR_PATH}"
echo "[package] Manifest: ${MANIFEST_PATH}"
echo "[package] Checksums: ${CHECKSUMS_PATH}"
