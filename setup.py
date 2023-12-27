from setuptools import setup

setup(
    name='mercurial-reviewboard',
    version='3.6.1',
    author='Dennis Schoen',
    author_email='dennis.schoen@epublica.de',
    packages=['mercurial_reviewboard'],
    description="A Mercurial extension which adds a post review command to "
        "post changesets for review to a Review Board server",
    long_description=open('README').read(),
    install_requires=['Mercurial']
)
