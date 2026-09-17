from pathlib import Path

import pytest

from minigraphrag import HashingEmbedder, MockLLM, build_index, load_index

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"
QUESTIONS = ROOT / "data" / "questions.jsonl"


@pytest.fixture
def llm():
    return MockLLM()


@pytest.fixture(scope="session")
def index_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("index")
    build_index(CORPUS, out, MockLLM(), HashingEmbedder())
    return out


@pytest.fixture(scope="session")
def index(index_dir):
    return load_index(index_dir)
