"""``xgen-app-env`` — Dockerfile 과 스크립트에서 쓰는 명령."""

from __future__ import annotations

import argparse
import json
import sys

from xgen_app_environment import (
    TemplateNotFound,
    __version__,
    copy_template,
    environment,
    export_environment,
    list_templates,
    requirements_path,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xgen-app-env", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="템플릿 목록")
    commands.add_parser("info", help="패키지 버전과 환경 정의(JSON)")
    copy = commands.add_parser("copy", help="템플릿을 폴더에 복사")
    copy.add_argument("template", help="fastapi-react 또는 fastapi-react/1")
    copy.add_argument("dest")
    export = commands.add_parser("export", help="템플릿·잠금·스크립트·환경 정의를 폴더로 꺼냄")
    export.add_argument("dest")
    requirements = commands.add_parser("requirements", help="잠금 파일 경로 출력")
    requirements.add_argument("name", help="app-python 또는 image-libraries")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "list":
            for template in list_templates():
                print(template.ref)
        elif args.command == "info":
            print(json.dumps({"version": __version__, **environment()}, ensure_ascii=False, indent=2))
        elif args.command == "copy":
            for path in copy_template(args.template, args.dest):
                print(path)
        elif args.command == "export":
            print(export_environment(args.dest))
        elif args.command == "requirements":
            print(requirements_path(args.name))
    except (TemplateNotFound, FileExistsError, KeyError) as exc:
        print(f"xgen-app-env: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
