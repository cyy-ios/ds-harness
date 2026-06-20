#!/usr/bin/env bash
# 在同一个 Codex exec session 中顺序执行 fixture 里程碑；所有输出写入 results。
set -euo pipefail
ROOT="${1:?fixture root required}"
OUT_DIR="${2:-$ROOT/eval_codex}"
MAX_MILESTONES="${3:-}"
mkdir -p "$OUT_DIR"
export HARNESS_SHARED_CACHE="${HARNESS_SHARED_CACHE:-/tmp/ds-harness-shared-cache}"
mkdir -p "$HARNESS_SHARED_CACHE"
PROMPTS="$ROOT/prompts/milestones.json"
COMMON_START=(--cd "$ROOT" --skip-git-repo-check --full-auto --json)
COMMON_RESUME=(--skip-git-repo-check --full-auto --json)
python3 - <<'PY' "$PROMPTS" "$OUT_DIR/prompts.txt" "$MAX_MILESTONES"
import json, sys
items=json.load(open(sys.argv[1]))
max_items = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
if max_items is not None:
    items = items[:max_items]
with open(sys.argv[2],'w') as f:
    for it in items:
        f.write(it['id']+'\t'+it['prompt'].replace('\n',' ')+'\n')
PY
first=1
SESSION_ID=""
while IFS=$'\t' read -r id prompt; do
  echo "== $id ==" | tee -a "$OUT_DIR/run.log"
  if [[ "$first" == 1 ]]; then
    codex exec "${COMMON_START[@]}" -o "$OUT_DIR/${id}.last.txt" "$prompt" > "$OUT_DIR/${id}.jsonl" </dev/null
    SESSION_ID=$(python3 - <<'PY' "$OUT_DIR/${id}.jsonl"
import json, sys
for line in open(sys.argv[1]):
    try: o=json.loads(line)
    except Exception: continue
    if o.get("type") == "thread.started":
        print(o.get("thread_id", "")); break
PY
)
    if [[ -z "$SESSION_ID" ]]; then echo "missing session id" >&2; exit 1; fi
    first=0
  else
    codex exec resume "$SESSION_ID" "${COMMON_RESUME[@]}" -o "$OUT_DIR/${id}.last.txt" "$prompt" > "$OUT_DIR/${id}.jsonl" </dev/null
  fi
  # per-milestone evidence collection
  python3 "$(dirname "$0")/collect_evidence.py" "$ROOT" --output-dir "$OUT_DIR/evidence/${id}" --final-only || true
done < "$OUT_DIR/prompts.txt"
