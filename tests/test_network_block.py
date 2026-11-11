import pytest
import requests


def test_real_network_call_fails_the_test():
    # RuntimeError (not OSError) so code that handles connection errors can't swallow it.
    with pytest.raises(RuntimeError, match="Network access is blocked"):
        requests.get("https://example.com/", timeout=5)
