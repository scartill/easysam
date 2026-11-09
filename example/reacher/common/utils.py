import os


def get_env():
    return os.environ.get('ENV', 'dev')
