#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/7/23 19:03
# @Author  : wgPython
# @File    : app.py.py
# @Software: PyCharm
# @Desc    :
"""

"""

import re
import time
import redis
import random
import hashlib

import requests

from threading import Thread

from utils import up_file  # 工具类上传图片

from flask import Flask, jsonify, request

app = Flask(__name__)

requests.urllib3.disable_warnings()  # 取消 verify 验证提示

redis_cli = redis.Redis(host='127.0.0.1', port=6379)

LoginUrl = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=startlogin"

# 登陆扫描页面  获取 微信号 源号主
GetSourceName = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=validate&lang=zh_CN&account={}&token="

QrCode = "https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=getqrcode&param=4300&rd=123"

CheckLogin = "https://mp.weixin.qq.com/cgi-bin/loginqrcode?action=ask&f=json&ajax=1&random={}"

DoLogin = "https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login"

# 非管理人员扫描需要二次验证
TwoVerify = None


def require_username(func):
    """
    装饰器 验证是否携带 username
         关于endpoint用法解释   https://stackoverflow.com/questions/17256602/assertionerror-view-function-mapping-is-overwriting-an-existing-endpoint-functi
    然后 通过username 获取相应的token和cookie
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        username = request.values.get("username")
        if not username:
            return jsonify({"code": 1, "msg": "请携带username查询"})

        token = redis_cli.get(f"{username}_token").decode()
        cookie = redis_cli.get(f"{username}_cookie").decode()
        if not token and not cookie:
            return jsonify({"code": 1, "msg": "redis中取不到token, 请重新登陆!"})

        return func(username, token, cookie, *args, **kwargs)

    return wrapper


def tool_clear_data(content):
    """
    替换成其他 数据类型
    :param content:
    :return:
    """
    content = content.replace("false", "False")
    content = content.replace("true", "True")
    content = content.replace("null", "None")
    return content


def tool_re_group_clear(data):
    """
    过滤正则提取的工具类
    :param data:
    :return:
    """
    try:
        data = data.group(1)
        return data
    except Exception as e:
        return ""


@app.route('/login', methods=["POST"])
def login_save_account():
    """
    登陆微信公众平台 并保存账号信息到redis
    :return:
    """
    username = request.values.get("username")
    password = request.values.get("password")
    if not username or not password:
        return jsonify({"code": 1, "msg": "请输入账号密码，并且key值必须为username和password"})

    session = requests.session()
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
        return jsonify({"code": 1, "msg": "need input verify code!"})
        # 需要验证码
        # res = session.get("https://mp.weixin.qq.com/cgi-bin/verifycode?username={}&r={}".format(
        #     username, int(time.time() * 1000)), stream=True, verify=False)
        # im = Image.open(BytesIO(res.content))
        # im.show()
        # verify_code = input("请输入登陆验证码: ")
        # session.post(LoginUrl, headers=headers,
        #                        data={"username": username,
        #                              "pwd": hashlib.md5(password.encode('utf-8')).hexdigest(),
        #                              "f": "json",
        #                              "imgcode": verify_code,  #
        #                              })

    # 获取管理员信息
    res = session.get(GetSourceName.format(username), headers={
        "Host": "mp.weixin.qq.com",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://mp.weixin.qq.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    source_name = re.search(r"当前账号\(([\s\S]{1,15})\)存在", res.text)
    if not source_name:
        source_name = "抱歉没有获取到 源账号名称"
    else:
        source_name = source_name.group(1)

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

    # 此处是把图片上传到七牛云 没有七牛云到可以考虑用bse64传输
    qr_code_img_url = up_file(r2.content)

    thr = Thread(target=async_login, args=[session, username])
    thr.start()

    return jsonify({"code": 0, "msg": "请尽快扫描验证码!有效时间5分钟", "QrCode": qr_code_img_url, "source_name": source_name})


def async_login(session, username):
    """
    由于需要扫码  所以异步等待扫码
    :param session: 登陆中的session
    :param username: 用户名
    :return:
    """
    with app.app_context():

        for i in range(60):
            # 声明TwoVerify 为全局变量
            global TwoVerify
            # print("等待扫码登陆")
            res = session.get(CheckLogin.format(random.random()))
            # {"base_resp":{"err_msg":"ok","ret":0},"status":0,"user_category":0}
            scan_res = res.json()
            if str(scan_res.get("status")) == "1" and str(scan_res.get("user_category")) == "2":  # 强转为str类型
                # print("验证码 本人已扫码确认！不用二次验证")
                # print(res.json())
                TwoVerify = False
                break
            elif str(scan_res.get("status")) == "1" and str(scan_res.get("user_category")) == "1":
                # print("验证码， 非管理员已经扫描!, 需要二次扫码验证!")
                TwoVerify = True
                break

            time.sleep(5)
        # 不是账号持有人员扫码， 需要管理员二次验证
        if TwoVerify:
            # print("请管理员验证！")
            for i in range(60):
                # print("管理员验证扫码中.....")
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
            time.sleep(1)

        # 首页
        session.get(f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}")
        cookie_res = str(session.cookies)

        data_bizuin = re.search(r"(data_bizuin=[\s\S]*?)\s", cookie_res)
        bizuin = re.search(r"(bizuin=[\s\S]*?)\s", cookie_res)
        data_ticket = re.search(r"(data_ticket=[\s\S]*?)\s", cookie_res)
        slave_sid = re.search(r"(slave_sid=[\s\S]*?)\s", cookie_res)
        slave_user = re.search(r"(slave_user=[\s\S]*?)\s", cookie_res)

        end_of_cookie = f"noticeLoginFlag=1; mm_lang=zh_CN; noticeLoginFlag=1; rewardsn=; wxtokenkey=777; " \
                        f"{bizuin.group(1)};{data_bizuin.group(1)};{data_ticket.group(1)};{slave_sid.group(1)};{slave_user.group(1)};"

        # 保存 cookie 到redis中
        redis_cli.set(f"{username}_cookie", end_of_cookie)
        redis_cli.set(f"{username}_token", token)


@app.route('/get/history/email', methods=['POST'], endpoint='get_history_email')
@require_username
def get_history_email(username, token, cookie):
    """
    获取历史 邮件信息  需要依赖 username
    :return:
    """

    res = requests.post("https://mp.weixin.qq.com/cgi-bin/sysnotify",
                        data={"token": token,
                              "lang": "zh_CN",
                              "f": "json",
                              "ajax": 1,
                              "random": random.random(),
                              "begin": 0,
                              "count": 20,
                              "status": 0},
                        headers={
                            "Host": "mp.weixin.qq.com",
                            "Connection": "keep-alive",
                            "Content-Length": "93",
                            "Accept": "application/json, text/javascript, */*; q=0.01",
                            "Origin": "https://mp.weixin.qq.com",
                            "X-Requested-With": "XMLHttpRequest",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "Referer": f"https://mp.weixin.qq.com/cgi-bin/frame?t=notification/index_frame&lang=zh_CN&token={token}",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Accept-Language": "zh-CN,zh;q=0.9",
                            "Cookie": cookie,
                        })
    return jsonify(res.json())


@app.route('/get/history/article', methods=['POST'], endpoint='get_history_article')
@require_username
def get_history_article(username, token, cookie):
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
        return jsonify(
            {"code": 1,
             "msg": "没有取到mass_data, cookie可能失效请重新登陆，更新cookie",
             "source_data": {
                 "source_content": res.text,
                 "source_status": res.status_code
             }
             })
    history_article = history_article.group(1)
    # clear_data 替换 true null 等为 Python中的关键字
    history_article = tool_clear_data(history_article)

    # 提取msg id
    msg_list = re.findall(r"appmsgid[\"|\']:(\d+)", history_article)
    msg_list = list(set(msg_list))
    msg_list_to_str = ",".join(msg_list)
    # 获取阅读数 和 好看数
    url = f"https://mp.weixin.qq.com/cgi-bin/appmsgotherinfo?appmsgidlist={msg_list_to_str}&token={token}&token={token}&lang=zh_CN&f=json&ajax=1"
    print(url, "----")
    res = requests.get(url, headers={
        "Host": "mp.weixin.qq.com",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Referer": "https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token=307804371",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cookie": cookie
    }, timeout=30)
    # 文章其他信息 包含阅读数 和 转发数
    article_other_info = res.json()

    # 历史文章(包含链接，标题等) 转换为dict 数据格式
    history_article = eval(history_article)

    # 重新组合 数据
    article_data = {
        "code": 0,
        "history_article": history_article,
        "article_other_info": article_other_info,
    }

    return jsonify(article_data)


@app.route('/get/fans/sex/ratio', methods=['POST'], endpoint='get_fans_sex_ration')
@require_username
def get_fans_sex_ration(username, token, cookie):
    """
    获取关注用户  男女比例
    :return:
    """
    yesterday_timestamp = time.time() - 1 * 60 * 60 * 24
    yesterday_date = time.strftime("%Y-%m-%d", time.localtime(yesterday_timestamp))

    url = f"https://mp.weixin.qq.com/misc/useranalysis?action=attr&begin_date={yesterday_date}&end_date={yesterday_date}&token={token}&lang=zh_CN"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Host": "mp.weixin.qq.com",
        "Referer": f"https://mp.weixin.qq.com/misc/useranalysis?=&token={token}&lang=zh_CN",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Cookie": cookie,
    }
    response = requests.get(url, headers=headers, timeout=30, verify=False)
    if response.text:
        try:
            genders_info = re.search(r"genders:\s?\[([\s\S]*?)\]", response.text)
            genders_info = re.sub(r"[\n\s]", "", genders_info.group(1))
            male = re.search(r".*?男.*?\([\"\'](\d+)[\"\']\)", genders_info)
            female = re.search(r".*?女.*?\([\"\'](\d+)[\"\']\)", genders_info)
            return jsonify({"code": 0, "msg": "OK", "male": male.group(1), "female": female.group(1)})
        except Exception as e:
            return jsonify({"code": 1, "msg": "数据提取错误", "reason": e})
    else:
        return jsonify({"code": 1, "msg": "没有获取到用户分析数据"})


@app.route('/get/public/account/info', methods=['POST'], endpoint='get_public_account_info')
@require_username
def get_public_account_info(username, token, cookie):
    is_get_cache = request.values.get("is_get_cache")
    if is_get_cache:
        account_info = redis_cli.get(f"{username}_account").decode()
        if account_info:
            account_info = eval(account_info)
            return jsonify({"code": 0, "msg": "OK", "account_info": account_info})
        else:
            return jsonify({"code": 1, "msg": "没有存储该账号数据, 请不用携带is_get_cache参数访问后,方可缓存"})

    url = f"https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=index&token={token}&lang=zh_CN"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Host": "mp.weixin.qq.com",
        "Referer": f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={token}",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Cookie": cookie
    }
    response = requests.get(url, headers=headers, timeout=30, verify=False)
    # 从源数据出中提取头像img
    account_image = re.search(r"headimg:\s?[\"\']([\s\S]*?)[\"\'],", response.text)

    res = re.search(r"weui-desktop-layout__main__hd(.*?)\n", response.text)
    data_info = re.sub(r"[\s\n]", "", res.group(1))
    data_info = re.sub(r"</?span[\s\S]*?>", r"", data_info)

    public_account_name = re.search(
        r"setting__item__label[\"\']>名称</label>[\s\S]*?setting__item__main[\"\']>(.*?)<div", data_info)

    wechat_account = re.search(
        r"setting__item__label[\"\']>微信号</label>[\s\S]*?setting__item__main[\"\']>(.*?)<div", data_info)

    public_account_type = re.search(
        r"setting__item__label[\"\']>类型</label>[\s\S]*?setting__item__info[\"\']>(.*?)</div", data_info)

    public_account_desc = re.search(
        r"setting__item__label[\"\']>介绍</label>[\s\S]*?setting__item__info[\"\']>(.*?)</div", data_info)

    public_account_auth = re.search(
        r"setting__item__label[\"\']>认证情况</label>[\s\S]*?setting__item__info[\"\']>(.*?)</div>",
        data_info)

    public_account_address = re.search(
        r"setting__item__label[\"\']>所在地址</label>[\s\S]*?setting__item__info[\"\']>(.*?)</div>",
        data_info)

    public_account_body = re.search(
        r"setting__item__label[\"\']>主体信息</label>[\s\S]*?setting__item__info[\"\']>(.*?)</div>",
        data_info)

    login_email = re.search(r"setting__item__label[\"\']>登录邮箱</label>[\s\S]*?setting__item__info[\"\']>(.*?)</div",
                            data_info)

    source_id = re.search(r"setting__item__label[\"\']>原始ID</label>[\s\S]*?setting__item__main[\"\']>(.*?)<div",
                          data_info)

    account_image = "https://mp.weixin.qq.com" + str(tool_re_group_clear(account_image))
    img_res = requests.get(account_image, headers={
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Host": "mp.weixin.qq.com",
        "Referer": f"https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=index&token={token}&lang=zh_CN",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Cookie": cookie,

    }, timeout=30, stream=True, verify=False)
    public_account_image = up_file(img_res.content)

    # 数据统一过滤
    public_account_name = tool_re_group_clear(public_account_name)
    wechat_account = tool_re_group_clear(wechat_account)
    public_account_type = tool_re_group_clear(public_account_type)
    public_account_desc = tool_re_group_clear(public_account_desc)
    public_account_auth = tool_re_group_clear(public_account_auth)
    public_account_address = tool_re_group_clear(public_account_address)
    public_account_body = tool_re_group_clear(public_account_body)
    login_email = tool_re_group_clear(login_email)
    source_id = tool_re_group_clear(source_id)

    account_info = {
        "public_account_image": public_account_image,
        "public_account_name": public_account_name,
        "wechat_account": wechat_account,
        "public_account_type": public_account_type,
        "public_account_desc": public_account_desc,
        "public_account_auth": public_account_auth,
        "public_account_address": public_account_address,
        "public_account_body": public_account_body,
        "login_email": login_email,
        "source_id": source_id,
    }

    redis_cli.set(f"{username}_account", str(account_info))

    return jsonify({"code": 0, "msg": "OK", "account_info": account_info})


if __name__ == '__main__':
    app.run()
