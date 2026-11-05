#!/bin/sh
# requirements/*.lock 을 다시 만든다. 사용: scripts/compile-requirements.sh [러너 requirements.lock]
# 러너 잠금을 주면 그 버전을 제약으로 건다. 앱이 러너 이미지의 패키지를 그대로 물려받으므로 버전이 갈리면 안 된다.
set -eu
cd "$(dirname "$0")/../src/xgen_app_environment/requirements"
base=""
[ $# -ge 1 ] && base="--constraint $1"
common="--universal --python-version 3.14 --only-binary :all: --generate-hashes --no-header --quiet"
# shellcheck disable=SC2086
uv pip compile app-python.in $common $base --output-file app-python.lock
# 두 잠금은 한 이미지에 함께 설치되므로 뒤의 것이 앞의 것을 제약으로 삼는다.
uv pip compile image-libraries.in $common $base --constraint app-python.lock --output-file image-libraries.lock
