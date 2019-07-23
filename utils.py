#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/7/23 19:06
# @Author  : wgPython
# @File    : utils.py
# @Software: PyCharm
# @Desc    :
"""
七牛云上传图片

也可以不用七牛云上传 改用base64 传输图片

"""

import uuid
import time

from qiniu import Auth, put_data

# 七牛云配置
ACCESS_KEY = ""
SECRET_KEY = ""
BUCKET_NAME = ""
PREFIX_URL = ""


def up_file(content):
    try:
        q = Auth(ACCESS_KEY, SECRET_KEY)
        # 上传到七牛后保存的文件名 int时间戳+uuid4+后缀 拼接url
        file_path = str(int(time.time())) + str(uuid.uuid4()) + ".png"
        token = q.upload_token(BUCKET_NAME, file_path, 3600)  # 3600指的是token的过期时间
        ret, info = put_data(token, file_path, content)
        if ret:
            return PREFIX_URL + file_path
        else:
            print("上传失败")
            return None
    except Exception as e:
        # 上传失败返回None
        print("上传GG", e)
        return None
