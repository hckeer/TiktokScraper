import pytest
from backend.extractor.extractor_wrapper import start_session
import asyncio

# A minimal test that we can import the module correctly
def test_import_wrapper():
    assert start_session is not None
