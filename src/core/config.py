import os


def load_config(path='.env'):
    config = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    config[key] = val
    return config
