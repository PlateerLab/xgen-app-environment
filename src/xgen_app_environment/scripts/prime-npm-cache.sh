#!/bin/sh
# 앱 템플릿의 npm 의존성을 이미지 안의 캐시에 미리 받아 둔다.
#
# 이렇게 해 두면 앱의 `npm ci` 가 네트워크 없이 끝난다. 폐쇄망에서는 이것이 유일한 길이고, 열린 망에서도
# 앱마다 다시 받지 않는다. node_modules 는 버린다 — 앱마다 자기 폴더에 새로 풀고, 이미지에는 캐시만 남긴다.
# node 만 있으면 된다(파이썬 불필요). 위치는 environment.json 의 npm 값과 같다.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
template="${here}/../templates/fastapi-react/frontend"
cache="${XGEN_NPM_CACHE:-/opt/xgen/npm-cache}"
npmrc="${XGEN_NPMRC:-/usr/local/etc/npmrc}"

mkdir -p "$cache" "$(dirname -- "$npmrc")"
printf 'cache=%s\nprefer-offline=true\nfund=false\naudit=false\nupdate-notifier=false\n' "$cache" > "$npmrc"

work=$(mktemp -d)
cp "$template/package.json" "$template/package-lock.json" "$work/"
cd "$work"
npm ci --no-audit --no-fund
node -e "require('vite/package.json'); require('react/package.json'); console.log('template npm deps cached')"
cd /
rm -rf "$work"

# 앱은 세션마다 다른 uid 로 돈다. npm ci 는 캐시 히트에도 색인을 갱신하므로 누구나 쓸 수 있어야 한다.
chmod -R a+rwX "$cache"
