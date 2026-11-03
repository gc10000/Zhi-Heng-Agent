"""预检必须实际消费catalog；错误路径不得建目录或读取模型凭据。"""
import importlib
from pathlib import Path
import pytest


def module():
    return importlib.import_module('app.evaluation.connection_048_preflight')


def test_preparation_refuses_existing_output_without_overwriting(tmp_path):
    saved=tmp_path/'keep.txt';saved.write_text('原证据',encoding='utf-8')
    with pytest.raises((FileExistsError,ValueError)):
        module().prepare_catalog(tmp_path)
    assert saved.read_text(encoding='utf-8')=='原证据' and len(list(tmp_path.iterdir()))==1


def test_preflight_missing_catalog_is_not_reported_as_ready(tmp_path):
    with pytest.raises((FileNotFoundError,ValueError)):
        module().preflight_catalog(tmp_path/'missing.json',control_database='synthetic-control')


def test_new_catalog_output_cannot_point_at_old_authorized_ledger():
    with pytest.raises(ValueError,match='目录|路径'):
        module().prepare_catalog(Path(__file__).resolve().parents[2]/'output/m6-authorized-products/forbidden')
