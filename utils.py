# -*- coding: utf-8 -*-
import hashlib
import os
from PyQt6.QtCore import QCoreApplication, qInfo, qCritical, qDebug, qWarning

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

def _2ascii(msg: str) -> str:
    # 将由UTF8编码的中文字符串转为ASCII编码
    return msg.encode('ascii', 'xmlcharrefreplace').decode('ascii')

def _qInfo(msg: str):
    # 将消息转换为ASCII编码并打印
    qInfo(_2ascii(msg))
def _qWarning(msg: str):
    # 将消息转换为ASCII编码并打印
    qWarning(_2ascii(msg))
def _qCritical(msg: str):
    # 将消息转换为ASCII编码并打印
    qCritical(_2ascii(msg)) 
def _qDebug(msg: str):
    # 将消息转换为ASCII编码并打印
    qDebug(_2ascii(msg))
def tr(msg: str) -> str:
    """翻译函数，使用QCoreApplication的translate方法"""
    return QCoreApplication.translate("ESP2DSD batch Convertor", msg)