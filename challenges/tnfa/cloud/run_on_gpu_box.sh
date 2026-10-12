#!/usr/bin/env bash
# TNF-alpha BoltzGen pilot on a rented Linux GPU box (RTX 4090 / A100 class). Not tested on a real box yet.
# Usage:   bash run_on_gpu_box.sh [SPEC] [N_DESIGNS]        defaults: tnfa_e3_min.yaml 10
# Optional environment variables:
#   HF_ENDPOINT=https://hf-mirror.com   Hugging Face mirror (for networks that cannot reach huggingface.co; third-party, unverified)
#   PIP_INDEX_URL=...                   pip mirror
#   REPO_URL=...                        git URL (default: the public GitHub repo); if cloning fails, put the repo as ~/repo.tar.gz
# Everything is written under ~/tnfa_run. Stop and return the instance when it prints DONE.
set -euo pipefail

SPEC="${1:-tnfa_e3_min.yaml}"
N="${2:-10}"
WORK="$HOME/tnfa_run"
REPO_URL="${REPO_URL:-https://github.com/SyzenShen/adaptyv-binder-challenges}"
mkdir -p "$WORK"; cd "$WORK"
log() { printf '\n=== %s | %s ===\n' "$(date +%H:%M:%S)" "$*"; }

log "1/7 GPU check"
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader || { echo "No NVIDIA GPU visible"; exit 1; }

log "2/7 Python >= 3.11 check (BoltzGen 0.3.2 requirement)"
PY=python3
$PY -c 'import sys; assert sys.version_info >= (3, 11), sys.version' || { echo "Need Python 3.11+: create one with conda or uv, then re-run with PATH set"; exit 1; }

log "3/7 virtual environment and BoltzGen 0.3.2 (pinned)"
[ -d venv ] || $PY -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip -q install --upgrade pip
pip -q install "boltzgen==0.3.2"
python -c 'import torch; print("torch", torch.__version__, "cuda", torch.cuda.is_available())'
python -c 'import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)' || { echo "PyTorch cannot see the GPU"; exit 1; }

log "4/7 repository (inputs and scripts)"
if [ ! -d repo ]; then
  git clone --depth 1 "$REPO_URL" repo || { [ -f "$HOME/repo.tar.gz" ] && mkdir repo && tar -xzf "$HOME/repo.tar.gz" -C repo --strip-components=1; }
fi
cd repo/challenges/tnfa/boltz && ls

log "5/7 model weights to local disk (about 9 GB), then verify the zip"
CACHE="$WORK/bg_cache"; mkdir -p "$CACHE"; export HF_HOME="$CACHE/hf"
boltzgen download all --cache "$CACHE"
python - <<PY
import glob, zipfile
z = glob.glob("$CACHE/datasets--boltzgen--inference-data/snapshots/*/mols.zip")
assert z, "mols.zip missing"
assert zipfile.ZipFile(z[0]).testzip() is None
print("mols.zip OK")
PY

log "6/7 spec check on CPU, then $N designs with $SPEC"
boltzgen check "$SPEC" --cache "$CACHE"
START=$(date +%s)
boltzgen run "$SPEC" --output "$WORK/out_${SPEC%.yaml}" --protocol protein-anything --num_designs "$N" --budget 5 \
  --inverse_fold_avoid C --cache "$CACHE" --reuse 2>&1 | tee "$WORK/run_${SPEC%.yaml}.log"
END=$(date +%s)
echo "seconds $((END-START))  seconds_per_design $(( (END-START) / N ))" | tee "$WORK/timing_${SPEC%.yaml}.txt"

log "7/7 summary and packaging"
python ../scripts/tnfa_summarize_run.py "${SPEC%.yaml}=$WORK/out_${SPEC%.yaml}" || true
tar -czf "$WORK/results_${SPEC%.yaml}.tar.gz" -C "$WORK" "out_${SPEC%.yaml}/final_ranked_designs" "timing_${SPEC%.yaml}.txt" "run_${SPEC%.yaml}.log"
ls -la "$WORK"/results_*.tar.gz
echo "DONE. Download $WORK/results_${SPEC%.yaml}.tar.gz, then return the instance (do not just close the browser tab)."
