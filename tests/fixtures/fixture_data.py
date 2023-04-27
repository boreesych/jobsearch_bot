import random
import string

import pytest


@pytest.fixture
def homework_module():
    import jobsearch_bot
    return jobsearch_bot


@pytest.fixture
def random_message():
    def random_string(string_length=15):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for _ in range(string_length))
    return random_string()
