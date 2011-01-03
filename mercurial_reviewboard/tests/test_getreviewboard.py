from mock import patch

from mercurial_reviewboard import getreviewboard
from mercurial_reviewboard.tests import get_initial_opts, mock_ui


@patch('mercurial_reviewboard.make_rbclient')
def test_get_credentials_from_config(mock_reviewboard):
        
    # username and password configs are included 
    # in the mock
    ui = mock_ui()
    opts = get_initial_opts()
        
    getreviewboard(ui, opts)
    
    mock_reviewboard.assert_called_with('http://example.com', 
        'foo', 'bar', proxy=None, apiver='')

    