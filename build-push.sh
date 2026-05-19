#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.build.conf"
VERSION_FILE="${SCRIPT_DIR}/.version"

DOCKER_USERNAME=""
DOCKER_REGISTRY=""
SERVICES=()
BUMP="patch"
DRY_RUN=false
BUILD_ONLY=false
REPO_NAME=""

if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

usage() {
    cat <<EOF
Usage: $(basename "$0") --repo NAME --services LIST [OPTIONS]

Build, tag, and push Docker images to Docker Hub.
Configure Docker Hub settings in .build.conf

Required:
  --repo NAME           Repository name prefix (e.g. --repo certifactory)
  --services LIST       Comma-separated list of service directories to build
                        (e.g. --services backend,frontend,proxy)

Options:
  --major               Bump major version (1.0.0 -> 2.0.0)
  --minor               Bump minor version (1.0.0 -> 1.1.0)
  --patch               Bump patch version (1.0.0 -> 1.0.1) [default]
  --set VERSION         Set version explicitly (e.g. --set 2.0.0)
  --build-only          Build and tag locally, don't push
  --dry-run             Show what would happen without building or pushing
  -h, --help            Show this help

Examples:
  $(basename "$0") --repo certifactory --services backend,frontend,proxy
  $(basename "$0") --repo myapp --services api,web --minor
  $(basename "$0") --repo myapp --services api --set 2.0.0 --dry-run
EOF
    exit 0
}

SET_VERSION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --major)    BUMP="major"; shift ;;
        --minor)    BUMP="minor"; shift ;;
        --patch)    BUMP="patch"; shift ;;
        --repo)     REPO_NAME="$2"; shift 2 ;;
        --services) IFS=',' read -ra SERVICES <<< "$2"; shift 2 ;;
        --set)      SET_VERSION="$2"; shift 2 ;;
        --build-only) BUILD_ONLY=true; shift ;;
        --dry-run)  DRY_RUN=true; shift ;;
        -h|--help)  usage ;;
        *)          echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$DOCKER_REGISTRY" ]]; then
    echo "Error: DOCKER_REGISTRY not set. Configure it in ${CONFIG_FILE}"
    echo ""
    echo "Example .build.conf:"
    echo '  DOCKER_REGISTRY="jobongo"'
    echo '  DOCKER_USERNAME="jobongo"'
    exit 1
fi

if [[ -n "$SET_VERSION" && -z "$REPO_NAME" ]]; then
    echo "$SET_VERSION" > "$VERSION_FILE"
    echo "Version set to ${SET_VERSION}"
    exit 0
fi

if [[ -z "$REPO_NAME" ]]; then
    echo "Error: --repo is required (e.g. --repo certifactory)"
    exit 1
fi

if [[ ${#SERVICES[@]} -eq 0 ]]; then
    echo "Error: --services is required (e.g. --services backend,frontend,proxy)"
    exit 1
fi

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "0.0.0" > "$VERSION_FILE"
fi

CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

if [[ -n "$SET_VERSION" ]]; then
    NEW_VERSION="$SET_VERSION"
else
    case $BUMP in
        major) NEW_VERSION="$((MAJOR + 1)).0.0" ;;
        minor) NEW_VERSION="${MAJOR}.$((MINOR + 1)).0" ;;
        patch) NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))" ;;
    esac
fi

echo "Registry: ${DOCKER_REGISTRY}"
echo "Repo:     ${REPO_NAME}"
echo "Version:  ${CURRENT} -> ${NEW_VERSION}"
echo "Services: ${SERVICES[*]}"
echo ""

if $DRY_RUN; then
    for svc in "${SERVICES[@]}"; do
        echo "[dry-run] docker build -t ${DOCKER_REGISTRY}/${REPO_NAME}-${svc}:${NEW_VERSION} ./${svc}"
        echo "[dry-run] docker tag ${DOCKER_REGISTRY}/${REPO_NAME}-${svc}:${NEW_VERSION} ${DOCKER_REGISTRY}/${REPO_NAME}-${svc}:latest"
        echo "[dry-run] docker push ${DOCKER_REGISTRY}/${REPO_NAME}-${svc}:${NEW_VERSION}"
        echo "[dry-run] docker push ${DOCKER_REGISTRY}/${REPO_NAME}-${svc}:latest"
    done
    echo ""
    echo "[dry-run] Would write ${NEW_VERSION} to ${VERSION_FILE}"
    exit 0
fi

if ! $BUILD_ONLY; then
    LOGIN_USER="${DOCKER_USERNAME:-$DOCKER_REGISTRY}"
    if docker info 2>/dev/null | grep -q "Username: ${LOGIN_USER}"; then
        echo "Already logged in as ${LOGIN_USER}"
    else
        echo "Logging in to Docker Hub as ${LOGIN_USER}..."
        docker login -u "${LOGIN_USER}"
    fi
    echo ""
fi

for svc in "${SERVICES[@]}"; do
    IMAGE="${DOCKER_REGISTRY}/${REPO_NAME}-${svc}"
    echo "==> Building ${IMAGE}:${NEW_VERSION}"
    docker build -t "${IMAGE}:${NEW_VERSION}" "./${svc}"
    docker tag "${IMAGE}:${NEW_VERSION}" "${IMAGE}:latest"

    if ! $BUILD_ONLY; then
        echo "==> Pushing ${IMAGE}:${NEW_VERSION}"
        docker push "${IMAGE}:${NEW_VERSION}"
        echo "==> Pushing ${IMAGE}:latest"
        docker push "${IMAGE}:latest"
    fi
    echo ""
done

echo "$NEW_VERSION" > "$VERSION_FILE"

echo "Done. Version ${NEW_VERSION} written to ${VERSION_FILE}"
if $BUILD_ONLY; then
    echo "Images built and tagged locally (not pushed)."
fi
