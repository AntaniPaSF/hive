#!/bin/bash
# Release validation and semantic versioning check
# Validates version format and release readiness

set -e

VERSION="${1}"
CHECK_CHANGES="${2:-true}"  # Check for code changes since last release

if [[ -z "${VERSION}" ]]; then
    echo "Usage: validate-release.sh <version> [check-changes]"
    echo "Example: validate-release.sh v1.0.0"
    exit 1
fi

echo "🔍 Validating release: ${VERSION}"

# Validate semantic versioning format
if ! [[ "${VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$ ]]; then
    echo "❌ Invalid semantic version format: ${VERSION}"
    echo "   Expected: v<MAJOR>.<MINOR>.<PATCH>[-prerelease][+buildmetadata]"
    echo "   Examples: v1.0.0, v1.0.0-alpha, v1.0.0-rc.1"
    exit 1
fi

echo "✅ Version format valid"

# Extract version components
MAJOR=$(echo "${VERSION}" | sed 's/v\([0-9]*\).*/\1/')
MINOR=$(echo "${VERSION}" | sed 's/v[0-9]*\.\([0-9]*\).*/\1/')
PATCH=$(echo "${VERSION}" | sed 's/v[0-9]*\.[0-9]*\.\([0-9]*\).*/\1/')
IS_PRERELEASE=$([[ "${VERSION}" == *"-"* ]] && echo "true" || echo "false")

echo ""
echo "📋 Version Breakdown:"
echo "   Major: ${MAJOR}"
echo "   Minor: ${MINOR}"
echo "   Patch: ${PATCH}"
echo "   Prerelease: ${IS_PRERELEASE}"

# Check for code changes if requested
if [ "${CHECK_CHANGES}" == "true" ]; then
    echo ""
    echo "📝 Checking for code changes..."
    
    # Get last tag
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    
    if [ -z "${LAST_TAG}" ]; then
        echo "⚠️  No previous tags found (first release)"
    else
        # Count commits since last tag
        COMMITS=$(git rev-list "${LAST_TAG}".."HEAD" --count 2>/dev/null || echo 0)
        
        if [ "${COMMITS}" -eq 0 ]; then
            echo "❌ No commits since last tag (${LAST_TAG})"
            exit 1
        fi
        
        echo "✅ Found ${COMMITS} commits since ${LAST_TAG}"
        
        # Show summary of changes
        echo ""
        echo "📊 Changes Summary:"
        git log "${LAST_TAG}".."HEAD" --oneline | head -10
        
        if [ $(git rev-list "${LAST_TAG}".."HEAD" --count) -gt 10 ]; then
            echo "   ... and more"
        fi
    fi
fi

# Check version monotonicity
if git rev-parse "${VERSION}" >/dev/null 2>&1; then
    echo ""
    echo "⚠️  Version tag already exists"
    echo "   Tag: ${VERSION} at $(git show -s --format=%ci ${VERSION})"
    echo "   This is fine for force-releasing, but be careful"
fi

echo ""
echo "✅ Release validation passed"
echo "   Ready to tag: git tag -a ${VERSION} -m 'Release ${VERSION}'"
echo "   Push: git push origin ${VERSION}"
