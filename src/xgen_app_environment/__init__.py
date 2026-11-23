"""XGEN 앱 템플릿과, 그 앱을 만들고 돌리는 컨테이너들이 함께 쓰는 환경 정의.

의존성이 없고 파일과 그 파일을 찾는 함수만 있다. 파일 소유권·경로 격리처럼 실행 환경마다
다른 일은 쓰는 쪽의 몫이다.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__version__ = "0.1.1"

__all__ = [
    "ENVIRONMENT_FILE",
    "REQUIREMENTS_DIR",
    "SCAFFOLD_SKIP",
    "SCRIPTS_DIR",
    "TEMPLATES_DIR",
    "Template",
    "TemplateNotFound",
    "copy_template",
    "environment",
    "export_environment",
    "get_template",
    "list_templates",
    "requirements_path",
]

_PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = _PACKAGE_DIR / "templates"
REQUIREMENTS_DIR = _PACKAGE_DIR / "requirements"
SCRIPTS_DIR = _PACKAGE_DIR / "scripts"
ENVIRONMENT_FILE = _PACKAGE_DIR / "environment.json"

#: 앱에 복사하지 않는 것 — 산출물과 의존성은 그 자리에서 새로 만들고, 메타는 앱의 파일이 아니다.
SCAFFOLD_SKIP = frozenset({"node_modules", "dist", "__pycache__", ".git", "template.json"})


class TemplateNotFound(LookupError):
    """없는 템플릿이거나 없는 버전이다."""


@dataclass(frozen=True)
class Template:
    name: str
    version: int
    path: Path
    service: dict[str, Any]
    install_files: tuple[str, ...]

    @property
    def ref(self) -> str:
        """앱 매니페스트의 ``template`` 값 (``fastapi-react/1``)."""
        return f"{self.name}/{self.version}"


def _load(directory: Path) -> Template:
    meta = json.loads((directory / "template.json").read_text(encoding="utf-8"))
    return Template(
        name=meta["name"],
        version=meta["version"],
        path=directory,
        service=dict(meta.get("service") or {}),
        install_files=tuple(meta.get("install_files") or ()),
    )


def list_templates() -> list[Template]:
    return [
        _load(d)
        for d in sorted(TEMPLATES_DIR.iterdir())
        if d.is_dir() and (d / "template.json").is_file()
    ]


def get_template(ref: str) -> Template:
    """``fastapi-react`` 또는 이미 만든 앱의 매니페스트가 적은 ``fastapi-react/1`` 로 찾는다."""
    name, _, version = str(ref or "").strip().partition("/")
    for template in list_templates():
        if template.name == name and (not version or version == str(template.version)):
            return template
    raise TemplateNotFound(f"템플릿이 없습니다: {ref}")


def copy_template(ref: str, dest: str | Path) -> list[str]:
    """템플릿을 ``dest`` 에 복사하고 복사한 파일의 상대 경로를 돌려준다. 내용이 있는 폴더는 덮어쓰지 않는다."""
    template = get_template(ref)
    target = Path(dest)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"이미 내용이 있습니다: {target}")

    def _skip(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in SCAFFOLD_SKIP}

    shutil.copytree(template.path, target, ignore=_skip, dirs_exist_ok=True)
    return sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())


def environment() -> dict[str, Any]:
    """런타임 버전·이미지 digest·npm 설정·시스템 패키지 목록."""
    return json.loads(ENVIRONMENT_FILE.read_text(encoding="utf-8"))


def requirements_path(name: str) -> Path:
    """``app-python`` 또는 ``image-libraries`` 잠금 파일의 경로."""
    relative = environment()["requirements"].get(name)
    if relative is None:
        raise KeyError(f"잠금 파일이 없습니다: {name}")
    return _PACKAGE_DIR / relative


def export_environment(dest: str | Path) -> Path:
    """템플릿·잠금·스크립트·환경 정의를 폴더로 꺼낸다.

    파이썬이 없는 빌드 단계(node 이미지)가 ``COPY --from`` 으로 받아 쓰게 하려는 것이다.
    """
    target = Path(dest)
    target.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__")
    for directory in (TEMPLATES_DIR, REQUIREMENTS_DIR, SCRIPTS_DIR):
        shutil.copytree(directory, target / directory.name, ignore=ignore, dirs_exist_ok=True)
    shutil.copy2(ENVIRONMENT_FILE, target / ENVIRONMENT_FILE.name)
    return target
