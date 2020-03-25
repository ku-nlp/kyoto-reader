import json
from typing import Tuple, Any
from pathlib import Path
import pytest

from kyoto_reader.scripts.sexp import parse


data_dir = Path(__file__).parent / 'data' / 'jumandic'
with data_dir.joinpath('test.dic').open() as fin:
    objs = parse(fin.read())

test_cases = [(obj, json.load(path.open())) for obj, path in zip(objs, sorted(data_dir.glob('*.json')))]


@pytest.mark.parametrize('test_case', test_cases)
def test_parse(test_case: Tuple[Any, Any]):
    assert test_case[0] == test_case[1]
