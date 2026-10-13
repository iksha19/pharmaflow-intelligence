#!/usr/bin/env bash
# PharmaFlow Intelligence - single-command pipeline (synthetic data). Usage: bash scripts/run_pipeline.sh [--skip-tests]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SKIP_TESTS=0; [[ "${1:-}" == "--skip-tests" ]] && SKIP_TESTS=1
mkdir -p reports data/raw data/processed data/exports
LOG="reports/pipeline.log"; : > "$LOG"

if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements.txt >>"$LOG" 2>&1

FAILED=()
run_step() {  # run_step "label" command...
  local label="$1"; shift
  printf '>> %-34s' "$label"
  if "$@" >>"$LOG" 2>&1; then echo "ok"; else echo "FAILED (see $LOG)"; FAILED+=("$label"); fi
}

run_step "1. generate data + build DB"     python scripts/generate_data.py
# Validation exits 1 when Critical rules fail. The synthetic data deliberately contains injected defects, so that is a FINDING, not a pipeline failure.
printf '>> %-34s' "2. data-quality validation"
set +e; python scripts/validate_data.py >>"$LOG" 2>&1; VRC=$?; set -e
if   [[ $VRC -eq 0 ]]; then echo "ok (no critical findings)"
elif [[ $VRC -eq 1 ]]; then echo "ok (critical findings reported - expected for injected defects)"
else echo "FAILED (exit $VRC, see $LOG)"; FAILED+=("validation"); fi
run_step "3. KPIs + SQL queries + recs"    python scripts/calculate_kpis.py
run_step "4. process mining"               python scripts/run_process_mining.py
run_step "5. Power BI export"              python scripts/export_powerbi.py
run_step "6. documentation pack"           python scripts/generate_docs.py
if [[ $SKIP_TESTS -eq 0 ]]; then run_step "7. automated tests"  python -m pytest -q; fi

echo; echo "== Outputs =="
echo "database      : $(ls -1 data/processed/*.db 2>/dev/null | head -1)"
echo "raw CSVs      : $(ls -1 data/raw/*.csv 2>/dev/null | wc -l)"
echo "processed CSVs: $(ls -1 data/processed/*.csv 2>/dev/null | wc -l)"
echo "Power BI CSVs : $(ls -1 data/exports/powerbi/*.csv 2>/dev/null | wc -l)"
echo "charts        : $(ls -1 reports/*.html 2>/dev/null | wc -l)"
echo "docs          : $(find docs -name '*.md' | wc -l) markdown files"
if [[ ${#FAILED[@]} -gt 0 ]]; then echo "FAILED STEPS: ${FAILED[*]}"; exit 1; fi
echo "Pipeline completed. Launch the app with:  streamlit run app.py"
