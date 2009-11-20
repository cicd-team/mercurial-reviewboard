from mock import patch

from mercurial_reviewboard import getreviewboard
from mercurial_reviewboard.tests import get_initial_opts, mock_ui

@patch('mercurial_reviewboard.ReviewBoard')
def test_get_credentials_from_config(mock_reviewboard):
        
    # username and password configs are included 
    # in the mock
    ui = mock_ui()
    opts = get_initial_opts()
        
    getreviewboard(ui, opts)
    
    mock_reviewboard.return_value.login.assert_called_with('foo', 'bar')

    