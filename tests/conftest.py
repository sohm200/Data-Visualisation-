import os
import tempfile
from pathlib import Path

# Keep test runs out of the developer's logs/app.log. Must be set before config is imported.
TEST_LOG_FILE = Path(tempfile.mkdtemp(prefix="dashboard-tests-")) / "app.log"
os.environ["DASHBOARD_LOG_FILE"] = str(TEST_LOG_FILE)

import pytest  # noqa: E402

import make_test_files  # noqa: E402
import profiler  # noqa: E402
import validator  # noqa: E402


@pytest.fixture(scope="session")
def tf():
    """tf("TF-01") -> (file name, bytes) from the SRS 6.4 test file set."""
    return make_test_files.build


@pytest.fixture
def profile_csv():
    """Read and profile CSV text, without the web server (NFR-18)."""
    def build(text: str, name: str = "data.csv"):
        return profiler.profile(validator.read_upload(name, text.encode("utf-8")))
    return build


@pytest.fixture(scope="session")
def tf_profile():
    """tf_profile("TF-10") -> the profiled test file, built once per test run."""
    cache = {}

    def build(test_file_id: str):
        if test_file_id not in cache:
            cache[test_file_id] = profiler.profile(validator.read_upload(*make_test_files.build(test_file_id)))
        return cache[test_file_id]
    return build
