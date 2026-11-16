#!/usr/bin/env bash
# Run from an imported course repository on the Linux cloud host.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
command -v python3 >/dev/null
command -v docker >/dev/null
sid=$(git config --local user.name)
if [[ ! "$sid" =~ ^[0-9]{6,16}$ ]]; then
  echo '请先在当前仓库设置 git config --local user.name 本人数字学号' >&2
  exit 2
fi
docker info >/dev/null
mkdir -p work
stamp=$(date +%Y%m%d-%H%M%S)-$$
out="work/a-${stamp}"
python3 run_e11e12.py build 2>&1 | tee "work/a-build-${stamp}.log"
python3 run_e11e12.py test 2>&1 | tee "work/a-test-${stamp}.log"
if [[ ! -e data/integration-sample ]]; then
  python3 run_e11e12.py prepare
else
  echo '复用已有 data/integration-sample；未覆盖其提交与请求。'
  test -f data/integration-sample/e11-a.json
fi
python3 run_e11e12.py run --request data/integration-sample/e11-a.json --out "$out" \
  2>&1 | tee "work/a-run-${stamp}.log"
python3 scripts/verify_a.py "$out" --out "work/a-verify-${stamp}.json"
docker run --rm --network none --cap-add SYS_PTRACE \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/course" -w /course "course-e11e12:${sid}" \
  python3 scripts/a_cases.py --out "/course/work/a-cases-${stamp}" \
  2>&1 | tee "work/a-cases-${stamp}.log"
echo "A组执行完成：${out}；自主案例：work/a-cases-${stamp}"
