import json
import re

import pytest

import xgen_app_environment as env
from xgen_app_environment.cli import main


def _pins(path):
    """주석·옵션·해시 줄을 뺀 이름 → 버전."""
    pins = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9._-]+)(\[[^\]]*\])?==([^ ;\\]+)", line)
        if match:
            pins[match.group(1).lower()] = match.group(3)
    return pins


@pytest.mark.parametrize("ref", ["fastapi-react/1", "fastapi-api/1"])
def test_refs_written_in_existing_app_manifests_resolve(ref):
    """이미 만든 앱의 매니페스트가 이 값을 들고 있다. 이 시험이 깨지면 그 앱들이 깨진다."""
    assert env.get_template(ref).ref == ref
    assert env.get_template(ref.split("/")[0]).ref == ref


@pytest.mark.parametrize("ref", ["", "nope", "fastapi-react/99", "../fastapi-react"])
def test_unknown_template_is_refused(ref):
    with pytest.raises(env.TemplateNotFound):
        env.get_template(ref)


@pytest.mark.parametrize("template", env.list_templates(), ids=lambda t: t.name)
def test_service_contract(template):
    assert template.service["command"] == "uvicorn backend.serve:app --host 0.0.0.0 --port $PORT"
    assert template.service["health"] == "/api/health"
    for relative in template.install_files:
        assert (template.path / relative).is_file(), relative
    for relative in ("backend/serve.py", "backend/apidocs.py", "backend/main.py", ".gitignore"):
        assert (template.path / relative).is_file(), relative


def test_copy_skips_meta_and_keeps_dotfiles(tmp_path):
    files = env.copy_template("fastapi-react", tmp_path / "app")
    assert "template.json" not in files
    assert {".gitignore", "backend/serve.py", "frontend/package-lock.json"} <= set(files)


def test_copy_never_overwrites(tmp_path):
    (tmp_path / "mine.txt").write_text("x")
    with pytest.raises(FileExistsError):
        env.copy_template("fastapi-api", tmp_path)


def test_template_pins_match_the_lock():
    lock = _pins(env.requirements_path("app-python"))
    for template in env.list_templates():
        for name, version in _pins(template.path / "backend" / "requirements.txt").items():
            assert lock[name] == version, name


def test_both_locks_agree_because_they_share_one_image():
    app = _pins(env.requirements_path("app-python"))
    image = _pins(env.requirements_path("image-libraries"))
    for name in app.keys() & image.keys():
        assert app[name] == image[name], name


def test_runtime_image_tags_match_versions():
    spec = env.environment()
    assert spec["python"]["image"].startswith(f"python:{spec['python']['version']}-")
    assert spec["node"]["image"].startswith(f"node:{spec['node']['version']}-")


def test_export_carries_what_a_python_less_build_stage_needs(tmp_path):
    env.export_environment(tmp_path)
    assert (tmp_path / "scripts" / "prime-npm-cache.sh").is_file()
    assert (tmp_path / "templates" / "fastapi-react" / "frontend" / "package-lock.json").is_file()
    assert (tmp_path / "requirements" / "image-libraries.lock").is_file()
    assert json.loads((tmp_path / "environment.json").read_text())["schema"] == 1


def test_cli(capsys, tmp_path):
    assert main(["list"]) == 0
    assert capsys.readouterr().out.split() == ["fastapi-api/1", "fastapi-react/1"]
    assert main(["copy", "nope", str(tmp_path / "x")]) == 1
