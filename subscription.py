#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/7/4 20:23
# @Author  : wgPython
# @File    : subscription.py
# @Software: PyCharm
# @Desc    :
"""
微信公众平台登陆
"""

import re
import time
import random
import hashlib

import requests

from io import BytesIO

from PIL import Image

# import base64
# with requests.get("https://www.baidu.com/img/bd_logo1.png") as f:
#
#     base64_data = base64.b64encode(f.content)
#
# print("data:image/jpg;base64,", base64_data.decode())


LoginUrl = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=startlogin"

# 登陆扫描页面  获取 微信号 源号主
GetSourceName = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account={}&token="

QrCode = "https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=getqrcode&param=4300&rd=123"

CheckLogin = "https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=ask&f=json&ajax=1&random={}"

DoLogin = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login"

# 非管理人员扫描需要二次验证
TwoVerify = None

username = "xxx"
password = "xxx"

session = requests.session()

requests.urllib3.disable_warnings()


def login_save_account():
    """
    登陆微信公众平台 并保存账号信息到redis
    :return:
    """
    session.get("https://mp.weixin.qq.com/", verify=False)

    headers = {
        "Host": "mp.weixin.qq.com",
        "Connection": "keep-alive",
        "Content-Length": "135",
        "Origin": "https://mp.weixin.qq.com",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Referer": "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account={}".format(
            username),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",

    }
    r1 = session.post(LoginUrl, headers=headers,
                      data={"username": username,
                            "pwd": hashlib.md5(password.encode('utf-8')).hexdigest(),
                            "f": "json",
                            "imgcode": "",  # 默认没有 验证码
                            }, verify=False)
    if "verify code" in r1.text:
        # 这里需要输入验证码, 线上两种方式解决 一 打码平台   二 自己写图像识别算法识别
        res = session.get("https://mp.weixin.qq.com/cgi-bin/verifycode?username={}&r={}".format(
            username, int(time.time() * 1000)), stream=True, verify=False)
        im = Image.open(BytesIO(res.content))
        # 弹出
        im.show()
        verify_code = input("请输入登陆验证码: ")
        session.post(LoginUrl, headers=headers,
                     data={"username": username,
                           "pwd": hashlib.md5(password.encode('utf-8')).hexdigest(),
                           "f": "json",
                           "imgcode": verify_code,  #
                           })

    r2 = session.get(QrCode, headers={
        "Host": "mp.weixin.qq.com",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account={}&token=".format(
            username),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",

    }, cookies=r1.cookies, stream=True, verify=False)
    # qr_code_img_url = up_file(r2.content)
    im = Image.open(BytesIO(r2.content))
    # 弹出二维码
    im.show()

    for i in range(60):
        # 声明TwoVerify 为全局变量
        global TwoVerify
        print("等待扫码登陆")
        res = session.get(CheckLogin.format(random.random()))
        # {"base_resp":{"err_msg":"ok","ret":0},"status":0,"user_category":0}
        scan_res = res.json()
        if str(scan_res.get("status")) == "1" and str(scan_res.get("user_category")) == "2":  # 强转为str类型
            print("验证码 本人已扫码确认！不用二次验证")
            # print(res.json())
            TwoVerify = False
            break
        elif str(scan_res.get("status")) == "1" and str(scan_res.get("user_category")) == "1":
            print("验证码， 非管理员已经扫描!, 需要二次扫码验证!")
            TwoVerify = True
            break
        time.sleep(5)

    # 不是账号持有人员扫码， 需要管理员二次验证
    if TwoVerify:
        print("请管理员验证！")
        for i in range(60):
            print("管理员验证扫码中.....")
            res = session.get(
                "https://mp.weixin.qq.com/cgi-bin/loginauth?action=ask&token=&lang=zh_CN&f=json&ajax=1",
                headers={
                    "Host": "mp.weixin.qq.com",
                    "Connection": "keep-alive",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "*/*",
                    "Referer": "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account={}&token=".format(
                        username),
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                })
            # print("状态码!", res.status_code)
            # print("管理员验证数据", res.text)
            if str(res.json().get("status")) == "1":
                # print("管理员已经确认")
                break
            time.sleep(5)

    # 这个token 和 后面的cookie是登陆凭证
    token = None
    for i in range(3):
        res = session.post(DoLogin, headers={
            "Host": "mp.weixin.qq.com",
            "Origin": "https://mp.weixin.qq.com",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": f"https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account={username}&token=",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }, data={
            "userlang": "zh_CN",
            "token": "",
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
            "redirect_url": "",
        }, verify=False)
        login_info = res.json()
        redirect_url = login_info.get("redirect_url")
        if redirect_url:
            token = re.search(r"token=(\d+)", redirect_url)
            token = token.group(1)
            break
        time.sleep(2)

    # 获取主页token
    session.get(f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}")
    cookie_res = str(session.cookies)

    data_bizuin = re.search(r"(data_bizuin=[\s\S]*?)\s", cookie_res)
    bizuin = re.search(r"(bizuin=[\s\S]*?)\s", cookie_res)
    data_ticket = re.search(r"(data_ticket=[\s\S]*?)\s", cookie_res)
    slave_sid = re.search(r"(slave_sid=[\s\S]*?)\s", cookie_res)
    slave_user = re.search(r"(slave_user=[\s\S]*?)\s", cookie_res)

    end_of_cookie = f"noticeLoginFlag=1; mm_lang=zh_CN; noticeLoginFlag=1; rewardsn=; wxtokenkey=777; " \
                    f"{bizuin.group(1)};{data_bizuin.group(1)};{data_ticket.group(1)};{slave_sid.group(1)};{slave_user.group(1)};"

    print('token:', token)
    print("\n")
    print('end_of_cookie: ', end_of_cookie)
    # 保存 cookie 到redis中
    # redis_cli.set(f"{username}_cookie", end_of_cookie)
    # redis_cli.set(f"{username}_token", token)


def get_history_article(token, cookie):
    """
    获取历史文章   文章链接  点击数等
    需要 username
    :return:
    """
    url = f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}"
    # 获取历史文章
    res = requests.get(url, headers={
        "Host": "mp.weixin.qq.com",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://mp.weixin.qq.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": cookie,
    }, verify=False)
    history_article = re.search(r"mass_data=([\s\S]*?});", res.text)
    if not history_article:
        print("没有取到mass_data, cookie可能失效请重新登陆，更新cookie")
        return
    history_article = history_article.group(1)
    print("历史文章: ", history_article)


if __name__ == '__main__':
    # login_save_account()
    token = ""
    end_of_cookie = ""

    get_history_article(token, end_of_cookie)
