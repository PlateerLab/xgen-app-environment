# xgen-app-environment

XGEN 앱 템플릿과, 그 앱을 만들고 돌리는 컨테이너들이 함께 쓰는 환경 정의입니다.
여러 이미지가 같은 템플릿, 같은 의존성 버전, 같은 폐쇄망 준비 절차를 쓰도록 한곳에 모았습니다.

런타임 의존성은 없습니다. 파일과 그 파일을 찾는 함수만 있습니다.

## 들어 있는 것

| 경로 (`src/xgen_app_environment/`) | 내용 |
|---|---|
| `templates/fastapi-react/` | 화면이 있는 앱. FastAPI + React(Vite)를 한 프로세스가 서빙 |
| `templates/fastapi-api/` | 화면 없는 앱. FastAPI 백엔드만 서빙 |
| `requirements/app-python.lock` | 템플릿 파이썬 의존성. 전이 의존성까지 해시로 고정 |
| `requirements/image-libraries.lock` | 이미지 공통 라이브러리(PDF·Office·표·웹·그림 처리). 해시로 고정 |
| `environment.json` | Python·Node·npm 버전, 이미지 digest, npm 캐시 설정, 시스템 패키지 목록 |
| `scripts/prime-npm-cache.sh` | 템플릿 npm 의존성을 이미지 안 캐시에 미리 받는 스크립트 |

## 설치

[Release](https://github.com/PlateerLab/xgen-app-environment/releases)의 wheel로 버전을 고정합니다.

```
xgen-app-environment @ https://github.com/PlateerLab/xgen-app-environment/releases/download/v0.1.2/xgen_app_environment-0.1.2-py3-none-any.whl
```

## 사용

```python
from xgen_app_environment import copy_template, environment, get_template, requirements_path

template = get_template("fastapi-react/1")   # 이름만 줘도 된다
template.service                             # install·build·command·health
copy_template("fastapi-react", "apps/demo")  # template.json 은 복사하지 않는다
requirements_path("image-libraries")
environment()["node"]["image"]
```

`copy_template`은 내용이 있는 폴더를 덮어쓰지 않습니다. 파일 소유권과 경로 격리는 쓰는 쪽에서 처리합니다.

```sh
xgen-app-env list
xgen-app-env info
xgen-app-env copy fastapi-api /tmp/app
xgen-app-env export /opt/xgen/app-environment
pip install -r "$(xgen-app-env requirements app-python)"
```

### Dockerfile

```dockerfile
# 이 패키지 자체는 파이썬 단계에서 설치하고 폴더로 꺼낸다.
FROM python:3.14.7-slim AS app-environment
RUN pip install --no-cache-dir "xgen-app-environment @ <wheel 주소>" \
    && xgen-app-env export /opt/app-environment

# 파이썬 의존성
FROM python:3.14.7-slim AS app-python
COPY --from=app-environment /opt/app-environment /opt/app-environment
RUN pip install --no-cache-dir -r /opt/app-environment/requirements/app-python.lock

# 파이썬이 없는 node 이미지에서도 같은 스크립트로 npm 캐시를 채운다.
FROM node:24.21.0-bookworm-slim AS app-node
COPY --from=app-environment /opt/app-environment /opt/app-environment
RUN sh /opt/app-environment/scripts/prime-npm-cache.sh
```

## 이미 만든 앱과의 호환

앱은 만들 때 템플릿을 자기 폴더로 복사하고, 매니페스트에 `fastapi-react/1`을 적어 둡니다.
이미 만든 앱이 계속 돌도록 다음을 지킵니다.

- `fastapi-react/1`, `fastapi-api/1`은 항상 찾을 수 있어야 합니다. 이름을 바꾸거나 `version`을 올리지 않습니다.
- 구조가 달라지는 템플릿은 기존 폴더를 고치지 않고 새 이름의 폴더로 추가합니다.
- 다음 계약은 유지합니다: 실행 명령 `uvicorn backend.serve:app`, 상태 확인 `/api/health`,
  예약 경로 `/api/openapi.json`·`/api/docs`, 잠금 파일 위치 `backend/requirements.txt`·`frontend/package-lock.json`.

## 의존성 올리기

앱은 이미지의 site-packages를 물려받으므로, 앱 의존성은 그 이미지의 잠금 파일과 버전이 같아야 합니다.

1. `requirements/*.in`과 두 템플릿의 `backend/requirements.txt`를 함께 고칩니다.
2. `scripts/compile-requirements.sh <러너 requirements.lock>`로 잠금 파일을 다시 만듭니다.
3. `pyproject.toml`과 `__init__.py`의 버전을 올리고 `CHANGELOG.md`에 적습니다.
4. `vX.Y.Z` 태그를 올리면 Release에 wheel이 붙습니다.

## 개발

```sh
pip install -e ".[dev]"
pytest
```

## 라이선스

Apache-2.0
