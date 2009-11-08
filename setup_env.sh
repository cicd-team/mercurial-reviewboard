rm -rf ENV
python virtualenv.py ENV --no-site-packages
ENV/bin/easy_install nose
ENV/bin/easy_install mercurial
