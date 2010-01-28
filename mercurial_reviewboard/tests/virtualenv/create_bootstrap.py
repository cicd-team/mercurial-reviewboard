import virtualenv

after_install = '''
def after_install(options, home_dir):
    install_package(home_dir, 'Mercurial')
    install_package(home_dir, 'mock')
    install_package(home_dir, 'nose')

def install_package(home_dir, package_name):
    import os
    opts = os.environ.get("INSTALL_OPTS","").split()
    cmd = [join(home_dir, 'bin', 'easy_install')]
    for opt in opts:
        cmd.append(opt)
    cmd.append(package_name)
    print "Running cmd: %s" % cmd.__str__()
    subprocess.call(cmd)
'''

if __name__ == '__main__':
    script = virtualenv.create_bootstrap_script(after_install)
    file = open('mercurial_reviewboard/tests/virtualenv/bootstrap.py', 'w')
    file.write(script)
    file.close()
