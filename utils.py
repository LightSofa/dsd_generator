# -*- coding: utf-8 -*-
import hashlib
import os

def file_hash(path, algorithm = "md5") -> str:
    h = getattr(hashlib, algorithm)()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def file_stat(file_path: str) -> dict[str, float]:
    """获取文件的大小和修改时间"""
    stat = os.stat(file_path)
    return {
        "size": stat.st_size,
        "mtime": stat.st_mtime
    }

def read_file_content(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return b""