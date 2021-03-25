# coding=UTF8
from mercurial_reviewboard import reviewboard

SAMPLE_DIFF = '''diff -r 000000000000 -r 95a59137df3f file_with_special_char.txt
--- /dev/null	Thu Jan 01 00:00:00 1970 +0000
+++ b/file_with_special_char.txt	Thu Feb 03 15:38:42 2011 -0600
@@ -0,0 +1,1 @@
+Look it up in the encyclopædia.
\ No newline at end of file
'''


def test_utf8_files():
    files = {'path': {'content': SAMPLE_DIFF, 'filename': 'diff'}}
    client = reviewboard.HttpClient(b'http://example.org')
    content_type, content = client._encode_multipart_formdata({}, files)
    expected_substring = 'Look it up in the encyclop\xe6dia.'

    unicode_content = content.decode('utf-8')

    assert unicode_content.index(expected_substring)
