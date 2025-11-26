import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_wikipedia_library():
    with patch('wikipedia.page') as mock_page:
        mock_page.return_value.title = "Mock Page"
        mock_page.return_value.summary = "This is a mock summary."
        mock_page.return_value.links = ["Link1", "Link2"]
        mock_page.return_value.categories = ["Category:Mock"]
        yield mock_page
