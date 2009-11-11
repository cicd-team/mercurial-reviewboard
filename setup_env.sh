rm -rf ENV
python virtualenv.py ENV --no-site-packages

# use INSTALL_OPTS to customize easy install 
# behavior (e.g. to point to a PyPI mirror)
ENV/bin/easy_install $INSTALL_OPTS Mercurial
ENV/bin/easy_install $INSTALL_OPTS nose
ENV/bin/easy_install $INSTALL_OPTS mock
