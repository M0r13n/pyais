import platform


def is_linux():
    return platform.system() == 'Linux'
