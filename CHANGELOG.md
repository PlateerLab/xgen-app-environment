# Changelog

## 0.1.2

- 두 템플릿 API 명세 페이지(`backend/apidocs.py`)의 앱 키 안내를 `Authorization: Bearer` 에서 `X-API-Key` 로 바꿈. 게이트웨이가 세션이 아닌 `Authorization` 을 401 로 끊어 Bearer 로는 API로 배포된 주소에 닿지 못한다

## 0.1.1

- `app-python.lock`·`image-libraries.lock` 의 certifi 를 2026.7.22 → 2026.10.23 으로 올림(GHSA-6q48-6c7w-9gw2, CRITICAL)

## 0.1.0

- `fastapi-react/1`, `fastapi-api/1` 템플릿을 xgen-workflow-sandbox `app/templates`(49389763)에서 내용 변경 없이 옮김
- 템플릿 파이썬 의존성의 전이 잠금(`app-python.lock`)과 이미지 공통 라이브러리 잠금(`image-libraries.lock`) 추가
- 런타임 버전·이미지 digest·npm 설정·시스템 패키지 목록(`environment.json`) 추가
- 파이썬·CLI API와 npm 캐시 준비 스크립트 추가
