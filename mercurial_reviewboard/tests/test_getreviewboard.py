from mock import patch

from mercurial_reviewboard import getreviewboard
from mercurial_reviewboard.tests import mock_ui

@patch('mercurial_reviewboard.ReviewBoard')
def test_get_credentials_from_config(mock_reviewboard):
        
    # username and password configs are included 
    # in the mock
    ui = mock_ui()
        
    getreviewboard(ui)
    
    mock_reviewboard.return_value.login.assert_called_with('foo', 'bar')

    