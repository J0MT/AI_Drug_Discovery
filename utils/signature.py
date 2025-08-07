import hashlib
import json

def compute_training_signature(config, file_paths):
    h = hashlib.sha256()
    h.update(json.dumps({k: v for k, v in config.items() if k != "data_path"}, sort_keys=True).encode())
    for path in file_paths:
        with open(path, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


 