#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/scripts/envs.txt"
GV_FILE="${ROOT_DIR}/ansible/group_vars/all.yml"

die() { echo "❌ $*" >&2; exit 1; }
info() { echo "ℹ️  $*"; }
ok() { echo "✅ $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required tool: '$1'"
}

# ---- Load envs.txt ----
[[ -f "$ENV_FILE" ]] || die "Missing scripts/envs.txt. Create it:\n  cp scripts/envs.example.txt scripts/envs.txt\n  nano scripts/envs.txt"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Defaults
: "${GLAB_AUTO_LOGIN:=0}"
: "${OVERRIDE_PATHS:=0}"
: "${TAGS:=discovery,workspace,scan,action,report,publish}"
: "${VERBOSE:=0}"
: "${FAIL_FAST:=true}"

# ---- Checks ----
require_cmd ansible-playbook
require_cmd git
require_cmd glab
require_cmd jq

[[ -d "${ROOT_DIR}/ansible" ]] || die "Can't find ansible/ in repo root"
[[ -f "${ROOT_DIR}/ansible/playbooks/run.yml" ]] || die "Missing ansible/playbooks/run.yml"

# ---- glab auth ----
if ! glab auth status --hostname "${HAMGIT_HOST}" >/dev/null 2>&1; then
  info "glab is NOT authenticated for host '${HAMGIT_HOST}'."
  if [[ "${GLAB_AUTO_LOGIN}" == "1" ]]; then
    [[ -f "${ROOT_DIR}/${HAMGIT_TOKEN_REL}" ]] || die "Token file not found: ${HAMGIT_TOKEN_REL}"
    info "Trying glab login using token file: ${HAMGIT_TOKEN_REL}"
    cat "${ROOT_DIR}/${HAMGIT_TOKEN_REL}" | glab auth login --hostname "${HAMGIT_HOST}" --stdin >/dev/null
    ok "glab login done."
  else
    die "Please login once:\n  cat ${HAMGIT_TOKEN_REL} | glab auth login --hostname ${HAMGIT_HOST} --stdin\nThen re-run:\n  bash scripts/run.sh"
  fi
fi
ok "glab auth OK for ${HAMGIT_HOST}"

# ---- Generate ansible/group_vars/all.yml (EXACT structure) ----
mkdir -p "${ROOT_DIR}/ansible/group_vars"

info "Generating ansible/group_vars/all.yml from scripts/envs.txt"

# Paths block: either keep playbook_dir defaults OR override
if [[ "${OVERRIDE_PATHS}" == "1" ]]; then
  PATHS_BLOCK=$(cat <<EOF
paths:
  workspace: "${WORKSPACE_PATH}"
  reports: "${REPORTS_PATH}"
EOF
)
else
  PATHS_BLOCK=$(cat <<'EOF'
paths:
  workspace: "{{ playbook_dir }}/../workspace"
  reports: "{{ playbook_dir }}/../reports"
EOF
)
fi

# target_patterns list (supports comma-separated)
# Example: "Dockerfile*,docker-compose.yml"
IFS=',' read -r -a TP_ARR <<< "${TARGET_PATTERNS:-Dockerfile*}"
TP_YAML=""
for p in "${TP_ARR[@]}"; do
  p_trimmed="$(echo "$p" | xargs)"
  [[ -n "$p_trimmed" ]] && TP_YAML+="    - \"${p_trimmed}\"\n"
done
[[ -n "$TP_YAML" ]] || TP_YAML="    - \"Dockerfile*\"\n"

cat > "$GV_FILE" <<YAML
# =========================
# Global configuration
# =========================

# GitLab instance
hamgit:
  host: ${HAMGIT_HOST}
  group_id: ${HAMGIT_GROUP_ID}

  # Token file used ONLY for glab API calls
  token_file: "{{ playbook_dir }}/../../${HAMGIT_TOKEN_REL}"

# =========================
# Workspace & outputs
# =========================

${PATHS_BLOCK}

# =========================
# Git behavior
# =========================

git:
  # Branch created in changed repositories
  branch_name: "${BRANCH_NAME}"

  # Commit message for all changes
  commit_message: "${COMMIT_MESSAGE}"

# =========================
# Action definition
# =========================

action:

  target_patterns:
$(printf "%b" "${TP_YAML}")
  # Example action parameter here is this line: (used by the action role)
  ensure_line: "${ENSURE_LINE}"

# =========================
# Execution behavior
# =========================

execution:
  fail_fast: ${FAIL_FAST}
YAML

ok "Wrote ${GV_FILE}"

# ---- Run ansible ----
info "Running ansible tags: ${TAGS}"
pushd "${ROOT_DIR}/ansible" >/dev/null

if [[ "${VERBOSE}" == "1" ]]; then
  ansible-playbook -i localhost, playbooks/run.yml --tags "${TAGS}"
else
  ansible-playbook -i localhost, playbooks/run.yml --tags "${TAGS}" >/dev/null
fi

popd >/dev/null
ok "Ansible finished."

# ---- Small report ----
REPORT_DIR="${ROOT_DIR}/ansible/reports"
echo
echo "===================="
echo "REPORKER SUMMARY"
echo "===================="
echo "Host:     ${HAMGIT_HOST}"
echo "Group:    ${HAMGIT_GROUP_ID}"
echo "Branch:   ${BRANCH_NAME}"
echo "Tags:     ${TAGS}"
echo "Reports:  ansible/reports/"
echo

if [[ -f "${REPORT_DIR}/changed.json" ]]; then
  echo "Changed repos: $(jq 'length' "${REPORT_DIR}/changed.json" 2>/dev/null || echo "?")"
fi

echo "Report files:"
ls -1 "${REPORT_DIR}" 2>/dev/null | sed 's/^/ - /' || echo " (no files found yet)"

ok "Done."

