import pytest
from backend.extractor.extractor import PhoneExtractor

def test_extract_phones():
    assert PhoneExtractor.extract("call me at 9841123456") == ["9841123456"]
    assert PhoneExtractor.extract("my num +9779841123456") == ["9841123456"]
    assert PhoneExtractor.extract("contact 9741123456") == ["9741123456"]
    assert PhoneExtractor.extract("fake number 9841123") == []
    # Test 50+ cases in real life, providing a few here to verify the structure
    assert PhoneExtractor.extract("hey") == []
