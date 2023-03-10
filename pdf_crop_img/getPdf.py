# -*- coding: utf-8 -*-
# @Author : 'Erwin'
# @File : getPdf.py.py
# @Software: PyCharm

import io
import requests


def get_file_func(link_path):
    """
    获取文件流信息
    : param: link_path  数据连接
    """
    response = requests.get(link_path)
    return io.BytesIO(response.content)




