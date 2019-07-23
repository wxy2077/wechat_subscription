# wechat_subscription
微信公众号模拟登陆

## 声明此代码仅供技术交流学习，擅自用于其他，一切后果与本人无关

```
# 简单环境 由于我这个直接用的本地环境，导致很多依赖,所以requirements.txt太多了
Python3.6+ 
Flask==1.0.2  
Pillow==6.1.0
qiniu   # 七牛云上传sdk
```

如果对你有帮助的话，可以点击star 🌈
对应博客 

- csdn: https://blog.csdn.net/wgPython/article/details/94719862
- segmentfault: https://segmentfault.com/a/1190000019673928


# Run
> 我省时间就直接写在一个.py文件里面，flask项目工程文件结构可参考我另一个项目：https://github.com/wgPython/Fantastic
```

> python3 app.py

```

# idea:
- [x] 封装成API接口，可以管理多个公众号，避免每天重复登陆。
- [x] 获取当前公众号的历史文章，点赞阅读，粉丝信息，账户信息等等。

#### 封装成api接口
- 1 登陆接口
```
POST  /login

params:
    username  {str}  
    password  {str}
    
return:
    {"code": 0, "msg": "请尽快扫描验证码!有效时间5分钟", "QrCode": "二维码链接", "source_name": source_name}

``` 
- 2 获取邮箱信息
```
POST /get/history/email
params:
    username {str}
return:
    微信原始接口信息    
```

- 3 获取历史文章，以及在看阅读数
```
POST /get/history/article
params:
    username {str}
return:
    article_data = {
        "code": 0,
        "history_article": 微信文章信息,
        "article_other_info": 微信在看阅读,
    }
```

- 4 获取关注用户男女比例
```
POST /get/fans/sex/ratio
params:
    username {str}
return:
    {"code": 0, "msg": "OK", "male": "数量", "female": "数量"}

```
- 5 获取账号信息
```
POST /get/public/account/info
params:
    username {str}
return:
       {"code": 0, 
       "msg": "OK", 
       "account_info":
        "public_account_image": 头像链接,
        "public_account_name": 名称,
        "wechat_account": 微信号,
        "public_account_type": 类型,
        "public_account_desc": 描述,
        "public_account_auth": 认证情况,
        "public_account_address": 所在地址,
        "public_account_body": 主体信息,
        "login_email": 登陆邮箱,
        "source_id": 原始ID,
       }
```



