import os


def get_env() -> str:
    return os.environ.get('ENV', 'easysamdev')
