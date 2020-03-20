import pytest
from pathlib import Path

from kyoto_reader import KyotoReader
from kyoto_reader import ALL_CASES, ALL_COREFS


data_dir = Path(__file__).parent / 'data'


@pytest.fixture()
def fixture_kyoto_reader():
    reader = KyotoReader(data_dir / 'knp',
                         target_cases=ALL_CASES,
                         target_corefs=ALL_COREFS)
    yield reader
