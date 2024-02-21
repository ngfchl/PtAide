import logging
import os
import random
import re
import threading
import time
import traceback
from datetime import datetime

import dateutil.parser
import requests
import toml
from lxml import etree
from requests.exceptions import RequestException

from PtAide.base import DotDict
from mysite.models import MySite
from toolbox.file_size_converter import FileSizeConvert
from toolbox.get_sites import get_site
from toolbox.schema import CommonResponse
from toolbox.spider import Spider
from toolbox.tools import get_decimals, baidu_ocr_captcha, extract_storage_size

lock = threading.Lock()

logger = logging.getLogger('ptools')


class PTSpider:
    def __init__(self, my_site: MySite):
        self.my_site = my_site
        self.site = get_site(self.my_site.site)
        self.spider = Spider(
            user_agent=self.my_site.user_agent,
            cookie=self.my_site.cookie,
            proxy=self.my_site.proxy,
        )

    def parse(self, response, rules):
        if self.my_site.mirror in [
            'https://ourbits.club/',
        ]:
            return etree.HTML(response.text).xpath(rules)
        elif self.my_site.mirror in [
            'https://piggo.me/',
        ]:
            return etree.HTML(response.text.encode('utf8')).xpath(rules)
        else:
            return etree.HTML(response.content.decode()).xpath(rules)

    def sign_in_52pt(self):
        url = f'{self.my_site.mirror}{self.site.page_sign_in.lstrip('/')}'
        result = self.spider.send_request(url=url)
        # sign_str = self.parse(result, '//font[contains(text(),"签过到")]/text()')
        sign_str = etree.HTML(result.text).xpath('//font[contains(text(),"签过到")]/text()')
        logger.debug(sign_str)
        if len(sign_str) >= 1:
            # msg = self.parse(result, '//font[contains(text(),"签过到")]/text()')
            return CommonResponse.success(msg='您已成功签到，请勿重复操作！{}'.format(sign_str))

        questionid = self.parse(result, '//input[contains(@name, "questionid")]/@value')
        choices = self.parse(result, '//input[contains(@name, "choice[]")]/@value')

        data = {
            'questionid': questionid,
            'choice[]': choices[random.randint(0, len(choices) - 1)],
            'usercomment': '十步杀一人，千里不流行！',
            'wantskip': '不会'
        }
        logger.debug(data)
        sign_res = self.spider.send_request(
            url=f'{self.my_site.mirror}{self.site.page_sign_in.lstrip('/')}',
            method='post', data=data
        )
        logger.debug(sign_res.text)

        sign_str = self.parse(sign_res, '//font[contains(text(),"点魔力值(连续")]/text()')
        if len(sign_str) < 1:
            return CommonResponse.error(msg='签到失败!')
        else:
            # msg = self.parse(sign_res, '//font[contains(text(),"签过到")]/text()')
            return CommonResponse.success(msg=f'签到成功！{"".join(sign_str)}')

    def sign_in_hd4fans(self):
        url = f'{self.my_site.mirror}{self.site.page_control_panel.lstrip('/')}'
        result = self.spider.send_request(url=url, )
        sign_str = self.parse(result, '//span[@id="checkin"]/a')
        logger.debug(sign_str)
        if len(sign_str) < 1:
            return CommonResponse.success(msg=f'{self.site.name} 已签到，请勿重复操作！！')
        sign_res = self.spider.send_request(
            url=f'{self.my_site.mirror}{self.site.page_sign_in.lstrip('/')}',
            method='post',
            params={'action': 'checkin'}
        )
        msg = '你还需要继续努力哦！此次签到，你获得了魔力奖励：{}'.format(sign_res.text.encode('utf8'))
        logger.debug(msg)
        return CommonResponse.success(msg=msg)

    def sign_in_hdupt(self):
        url = f'{self.my_site.mirror}{self.site.page_control_panel.lstrip('/')}'
        result = self.spider.send_request(url=url, )
        sign_str = self.parse(result, '//span[@id="qiandao"]')
        logger.debug(sign_str)
        if len(sign_str) < 1:
            return CommonResponse.success(msg=f'{self.site.name} 已签到，请勿重复操作！！')
        sign_res = self.spider.send_request(
            url=f'{self.my_site.mirror}{self.site.page_sign_in}'.lstrip('/'),
            method='post'
        ).text
        logger.debug(f'好多油签到反馈：{sign_res}')
        try:
            sign_res = get_decimals(sign_res)
            if int(sign_res) > 0:
                return CommonResponse.success(
                    msg='你还需要继续努力哦！此次签到，你获得了魔力奖励：{}'.format(sign_res)
                )
        except Exception as e:
            logger.error(traceback.format_exc(3))
            return CommonResponse.error(
                msg=f'签到失败！{sign_res}: {e}'
            )

    def get_zhuque_header(self, mirror):
        """获取朱雀csrf-token，并生成请求头"""
        csrf_res = self.spider.send_request(url=mirror)
        # '<meta name="x-csrf-token" content="4db531b6687b6e7f216b491c06937113">'
        x_csrf_token = self.parse(csrf_res, '//meta[@name="x-csrf-token"]/@content')
        logger.debug(f'csrf token: {x_csrf_token}')
        return {
            'user-agent': self.my_site.user_agent,
            'content-type': 'application/json',
            'x-csrf-token': ''.join(x_csrf_token),
        }

    def sign_in_zhuque(self):
        try:
            mirror = self.my_site.mirror
            headers = self.get_zhuque_header(mirror)
            headers['referer'] = 'https://zhuque.in/gaming/genshin/character/list'
            data = {"resetModal": "true", "all": 1, }
            url = f'{mirror}{self.site.page_sign_in}'
            logger.info(url)
            res = self.spider.send_request(method='post', url=url, json=data, headers=headers)
            # res = requests.post(url=url, verify=False, cookies=cookie2dict(self.my_site.cookie), json=data, headers=header)
            """
            {
                "status": 200,
                "data": {
                    "code": "FIRE_GENSHIN_CHARACTER_MAGIC_SUCCESS",
                    "bonus": 0
                }
            }
            """
            logger.debug(res.content)
            return CommonResponse.success(data=res.json())
        except Exception as e:
            # 打印异常详细信息
            logger.error(traceback.format_exc(limit=3))
            return CommonResponse.error(
                msg='{} 签到失败: {}'.format(self.site.name, e)
            )

    def sign_in_hdc(self):
        mirror = self.my_site.mirror
        url = f'{mirror}{self.site.page_control_panel.lstrip('/')}'
        # result = self.spider.send_request(
        #     my_site=self.my_site,
        #     url=url,
        # )
        cookie_dict = self.spider.cookie2dict(self.my_site.cookie)
        cookie_dict.pop('PHPSESSID', None)
        result = requests.get(url=url, verify=False,
                              cookies=cookie_dict,
                              headers={
                                  'user-agent': self.my_site.user_agent
                              })
        logger.debug(f'签到检测页面：{result.text}')
        sign_str = self.parse(result, '//a[text()="已签到"]')
        logger.debug('{}签到检测'.format(self.site.name, sign_str))
        logger.debug(f'{result.cookies.get_dict()}')

        if len(sign_str) >= 1:
            return CommonResponse.success(msg=f'{self.site.name} 已签到，请勿重复操作！！')
        csrf = ''.join(self.parse(result, '//meta[@name="x-csrf"]/@content'))
        logger.debug(f'CSRF字符串：{csrf}')
        # sign_res = self.spider.send_request(
        #     my_site=self.my_site,
        #     url=f'{mirror}{self.site.page_sign_in}',
        #     method=site.sign_in_method,
        #     data={
        #         'csrf': csrf
        #     }
        # )
        cookies = self.spider.cookie2dict(self.my_site.cookie)
        cookies.update(result.cookies.get_dict())
        logger.debug(cookies)
        sign_res = requests.request(url=f'{mirror}{self.site.page_sign_in}', verify=False, method='post',
                                    cookies=cookies,
                                    headers={'user-agent': self.my_site.user_agent}, data={'csrf': csrf})
        logger.debug(sign_res.text)
        res_json = sign_res.json()
        logger.debug(sign_res.cookies)
        logger.info('签到返回结果：{}'.format(res_json))
        if res_json.get('state') == 'success':
            if len(sign_res.cookies) >= 1:
                logger.debug(f'我的COOKIE：{self.my_site.cookie}')
                logger.debug(f'新的COOKIE字典：{sign_res.cookies.items()}')
                cookie = ''
                for k, v in sign_res.cookies.items():
                    cookie += f'{k}={v};'
                logger.debug(f'新的COOKIE：{sign_res.cookies.items()}')
                self.my_site.cookie = cookie
                self.my_site.save()
            msg = f"签到成功，您已连续签到{res_json.get('signindays')}天，本次增加魔力:{res_json.get('integral')}。"
            logger.info(msg)
            return CommonResponse.success(msg=msg)
        else:
            msg = res_json.get('msg')
            logger.error(msg)
            return CommonResponse.error(msg=msg)

    def sign_in_u2(self):
        mirror = self.my_site.mirror
        url = f'{mirror}{self.site.page_sign_in}'.lstrip('/')
        result = self.spider.send_request(url=url, )
        sign_str = ''.join(self.parse(result, '//a[@href="showup.php"]/text()'))
        logger.info(self.site.name + sign_str)
        if '已签到' in sign_str or '已簽到' in sign_str:
            # if '已签到' in converter.convert(sign_str):
            return CommonResponse.success(msg=f'{self.site.name}已签到，请勿重复操作！！')
        req = self.parse(result, '//form//td/input[@name="req"]/@value')
        hash_str = self.parse(result, '//form//td/input[@name="hash"]/@value')
        form = self.parse(result, '//form//td/input[@name="form"]/@value')
        submit_name = self.parse(result, '//form//td/input[@type="submit"]/@name')
        submit_value = self.parse(result, '//form//td/input[@type="submit"]/@value')
        message = '天空飘来五个字儿,幼儿园里没有事儿'
        logger.debug(submit_name)
        logger.debug(submit_value)
        param = []
        for name, value in zip(submit_name, submit_value):
            param.append({name: value})
        data = {
            'req': req[0],
            'hash': hash_str[0],
            'form': form[0],
            'message': message,
        }
        data.update(param[random.randint(0, 3)])
        logger.debug(data)
        response = self.spider.send_request(
            url=f'{mirror}{self.site.page_sign_in.lstrip("/")}?action=show',
            method='post',
            data=data,
        )
        logger.debug(response.content.decode('utf8'))
        if "window.location.href = 'showup.php';" in response.content.decode('utf8'):
            result = self.spider.send_request(url=url, )
            title = self.parse(result, '//h2[contains(text(),"签到区")]/following-sibling::table//h3/text()')
            content = self.parse(
                result,
                '//td/span[@class="nowrap"]/a[contains(@href,"userdetails.php?id={}")]'
                '/parent::span/following-sibling::b[2]/text()'.format(self.my_site.user_id)
            )
            msg = '{}，奖励UCoin{}'.format(''.join(title), ''.join(content))
            logger.info(msg)
            return CommonResponse.success(msg=msg)
        else:
            logger.error('签到失败！')
            return CommonResponse.error(msg='签到失败！')

    def sign_in_opencd(self):
        """皇后签到"""
        mirror = self.my_site.mirror
        check_url = f'{mirror}{self.site.page_user}'
        res_check = self.spider.send_request(url=check_url)
        href_sign_in = self.parse(res_check, '//a[@href="/plugin_sign-in.php?cmd=show-log"]')
        if len(href_sign_in) >= 1:
            return CommonResponse.success(data={'state': 'false'})
        url = f'{mirror}{self.site.page_sign_in}'.lstrip('/')
        logger.debug('# 开启验证码！')
        res = self.spider.send_request(method='get', url=url)
        logger.debug(res.text.encode('utf-8-sig'))
        img_src = ''.join(self.parse(res, '//form[@id="frmSignin"]//img/@src'))
        img_get_url = mirror + img_src
        times = 0
        # imagestring = ''
        ocr_result = None
        while times <= 5:
            ocr_result = baidu_ocr_captcha(img_get_url)
            if ocr_result.code == 0:
                imagestring = ocr_result.data
                logger.debug('验证码长度：{}'.format(len(imagestring)))
                if len(imagestring) == 6:
                    break
            times += 1
            time.sleep(1)
        if ocr_result.code != 0:
            return ocr_result
        data = {
            'imagehash': ''.join(self.parse(res, '//form[@id="frmSignin"]//input[@name="imagehash"]/@value')),
            'imagestring': imagestring
        }
        logger.debug('请求参数：{}'.format(data))
        result = self.spider.send_request(
            method='post',
            url=f'{mirror}plugin_sign-in.php?cmd=signin', data=data)
        logger.debug('皇后签到返回值：{}  \n'.format(result.text.encode('utf-8-sig')))
        return CommonResponse.success(data=result.json())

    def sign_in_hdsky(self):
        """HDSKY签到"""
        mirror = self.my_site.mirror
        url = f'{mirror}{self.site.page_sign_in.lstrip('/')}'
        # sky无需验证码时使用本方案
        # if not captcha:
        #     result = self.spider.send_request(
        #         my_site=self.my_site,
        #         method='post',
        #         url=url
        #     )
        # sky无验证码方案结束
        # 获取img hash
        logger.debug('# 开启验证码！')
        res = self.spider.send_request(
            method='post',
            url=f'{mirror}image_code_ajax.php',
            data={
                'action': 'new'
            }).json()
        # img url
        img_get_url = f'{mirror}image.php?action=regimage&imagehash={res.get("code")}'
        logger.debug(f'验证码图片链接：{img_get_url}')
        # 获取OCR识别结果
        # imagestring = toolbox.baidu_ocr_captcha(img_url=img_get_url)
        times = 0
        # imagestring = ''
        ocr_result = None
        while times <= 5:
            # ocr_result = toolbox.baidu_ocr_captcha(img_get_url)
            ocr_result = baidu_ocr_captcha(img_get_url)
            if ocr_result.code == 0:
                imagestring = ocr_result.data
                logger.debug(f'验证码长度：{len(imagestring)}')
                if len(imagestring) == 6:
                    break
            times += 1
            time.sleep(1)
        if ocr_result.code != 0:
            return ocr_result
        # 组装请求参数
        data = {
            'action': 'showup',
            'imagehash': res.get('code'),
            'imagestring': imagestring
        }
        # logger.debug('请求参数', data)
        result = self.spider.send_request(
            method='post',
            url=url, data=data)
        logger.debug('天空返回值：{}\n'.format(result.text))
        return CommonResponse.success(data=result.json())

    def sign_in_ttg(self):
        """
        TTG签到
        :return:
        """
        mirror = self.my_site.mirror
        url = f'{mirror}{self.site.page_user.format(self.my_site.user_id)}'
        logger.info(f'{self.site.name} 个人主页：{url}')
        try:
            res = self.spider.send_request(url=url)
            # logger.debug(res.text.encode('utf8'))
            # html = self.parse(site,res, '//script/text()')
            html = etree.HTML(res.text).xpath('//script/text()')
            # logger.debug(html)
            text = ''.join(html).replace('\n', '').replace(' ', '')
            logger.debug(text)
            signed_timestamp = get_decimals(re.search("signed_timestamp:\"\d{10}", text).group())

            signed_token = re.search('[a-zA-Z0-9]{32}', text).group()
            params = {
                'signed_timestamp': signed_timestamp,
                'signed_token': signed_token
            }
            logger.debug(f'signed_timestamp:{signed_timestamp}')
            logger.debug(f'signed_token:{signed_token}')

            resp = self.spider.send_request(
                f'{mirror}{self.site.page_sign_in}',
                method='post',
                data=params)
            logger.debug(f'{self.my_site.nickname}: {resp.content.decode("utf8")}')
            return CommonResponse.success(msg=resp.content.decode('utf8'))
        except Exception as e:
            # 打印异常详细信息
            logger.error(traceback.format_exc(limit=3))
            return CommonResponse.error(msg='{} 签到失败: {}'.format(self.site.name, e))

    @staticmethod
    def parse_school_location(text: list):
        logger.info(f'解析学校访问链接：{text}')
        redirect = text[0].split('+')[1].split('=', 1)[1].strip(';').strip('"')
        return redirect

    def update_sign_info(self, message):
        self.my_site.sign_info[str(datetime.now().date())] = {
            'time': datetime.now(),
            'info': message
        }
        self.my_site.save()

    def sign_in(self):
        """签到"""
        logger.info(f'{self.site.name} 开始签到')
        # 如果已有签到记录
        if self.my_site.has_today_sign():
            return CommonResponse.success(msg=f'{self.my_site.nickname} 已签到，请勿重复签到！')
        url = f'{self.my_site.mirror}{self.site.page_sign_in}'.lstrip('/')
        logger.info(f'签到链接：{url}')
        try:
            # with lock:
            if '52pt' in self.my_site.mirror or 'chdbits' in self.my_site.mirror:
                result = self.sign_in_52pt()
                if result.code == 0:
                    self.update_sign_info(result.msg)
                return result
            if 'hd4fans' in self.my_site.mirror:
                result = self.sign_in_hd4fans()
                if result.code == 0:
                    self.update_sign_info(result.msg)
                return result
            # if 'leaves.red' in self.my_site.mirror:
            # 红叶签到，暂不支持
            #     result = self.sign_in_leaves(self.my_site)
            # if result.code == 0:
            #     signin_today.sign_in_today = True
            #     signin_today.sign_in_info = result.msg
            #     signin_today.save()
            # return result
            if 'zhuque.in' in self.my_site.mirror:
                result = self.sign_in_zhuque()
                if result.code == 0 and result.data.get('status') == 200:
                    data = result.data.get("data")
                    bonus = data.get("bonus")
                    message = f'技能释放成功，获得{bonus}灵石'
                    result.msg = message
                return result
            if 'hdupt.com' in self.my_site.mirror:
                result = self.sign_in_hdupt()
                if result.code == 0:
                    self.update_sign_info(result.msg)
                return result
            if 'hdchina' in self.my_site.mirror:
                result = self.sign_in_hdc()
                if result.code == 0:
                    self.update_sign_info(result.msg)
                return result
            if 'totheglory' in self.my_site.mirror:
                result = self.sign_in_ttg()
                if result.code == 0:
                    self.update_sign_info(result.msg)
                return result
            if 'u2.dmhy.org' in self.my_site.mirror:
                result = self.sign_in_u2()
                if result.code == 0:
                    self.update_sign_info(result.msg)
                return result
            if 'hdsky.me' in self.my_site.mirror:
                result = self.sign_in_hdsky()
                if result.code == 0:
                    res_json = result.data
                    if res_json.get('success'):
                        # 签到成功
                        bonus = res_json.get('message')
                        days = (int(bonus) - 10) / 2 + 1
                        message = f'成功,已连续签到{days}天,魔力值加{bonus},明日继续签到可获取{bonus + 2}魔力值！'
                        self.update_sign_info(message)
                        return CommonResponse.success(msg=message)
                    elif res_json.get('message') == 'date_unmatch':
                        # 重复签到
                        message = '您今天已经在其他地方签到了哦！'
                        self.update_sign_info(message)
                        return CommonResponse.success(msg=message)
                    elif res_json.get('message') == 'invalid_imagehash':
                        # 验证码错误
                        return CommonResponse.error(msg='验证码错误')
                    else:
                        # 签到失败
                        return CommonResponse.error(msg='签到失败')
                else:
                    # 签到失败
                    return result
            if 'open.cd' in self.my_site.mirror:
                result = self.sign_in_opencd()
                logger.info(f'皇后签到结果：{result.to_dict()}')
                if result.code == 0:
                    res_json = result.data
                    if res_json.get('state') == 'success':
                        message = f"签到成功，您已连续签到{res_json.get('signindays')}天，本次增加魔力:{res_json.get('integral')}。"
                        self.update_sign_info(message)
                        return CommonResponse.success(msg=message)
                    elif res_json.get('state') == 'false' and len(res_json) <= 1:
                        # 重复签到
                        message = '您今天已经在其他地方签到了哦！'
                        self.update_sign_info(message)
                        return CommonResponse.success(msg=message)
                    # elif res_json.get('state') == 'invalid_imagehash':
                    #     # 验证码错误
                    #     return CommonResponse.error(
                    #         status=StatusCodeEnum.IMAGE_CODE_ERR,
                    #     )
                    else:
                        # 签到失败
                        return CommonResponse.error(msg=res_json.get('msg'))
                else:
                    # 签到失败
                    return result
            if 'hdarea' in self.my_site.mirror:
                res = self.spider.send_request(method='post',
                                               url=url,
                                               data={'action': 'sign_in'}, )
                logger.info(res.text)
                if res.text.find('已连续签到') >= 0 or res.text.find('请不要重复签到哦！') >= 0:

                    self.update_sign_info(res.text)
                    return CommonResponse.success(msg=res.text)
                elif res.status_code == 503:
                    return CommonResponse.error(msg='网站访问失败！')
                else:
                    return CommonResponse.error(msg='签到失败！')
            if 'hares.top' in self.my_site.mirror:
                res = self.spider.send_request(method='post', url=url, headers={"accept": "application/json"})
                logger.debug(res.text)
                code = res.json().get('code')
                # logger.debug('白兔返回码：'+ type(code))
                if int(code) == 0:
                    """
                    "datas": {
                      "id": 2273,
                      "uid": 2577,
                      "added": "2022-08-03 12:52:36",
                      "points": "200",
                      "total_points": 5435,
                      "days": 42,
                      "total_days": 123,
                      "added_time": "12:52:36",
                      "is_updated": 1
                    }
                    """
                    message_template = '签到成功！奖励奶糖{},奶糖总奖励是{},您已连续签到{}天，签到总天数{}天！'
                    data = res.json().get('datas')
                    message = message_template.format(data.get('points'),
                                                      data.get('total_points'),
                                                      data.get('days'),
                                                      data.get('total_days'))
                    self.update_sign_info(message)
                    return CommonResponse.success(msg=message)
                elif int(code) == 1:
                    message = res.json().get('msg')
                    self.update_sign_info(message)
                    return CommonResponse.success(msg=message)
                else:
                    return CommonResponse.error(msg='签到失败！')
            if self.my_site.mirror in [
                'https://wintersakura.net/',
                'https://hudbt.hust.edu.cn/',
            ]:
                # 单独发送请求，解决冬樱签到问题
                logger.info(url)
                res = requests.get(url=url, verify=False, cookies=self.spider.cookie2dict(self.my_site.cookie),
                                   headers={
                                       'user-agent': self.my_site.user_agent
                                   })
                logger.debug(res.text)
            else:
                res = self.spider.send_request(method='post', url=url)
            logger.info(f'{self.my_site.nickname}: {res}')
            if 'pterclub.com' in self.my_site.mirror:
                logger.debug(f'猫站签到返回值：{res.json()}')
                status = res.json().get('status')
                logger.info('{}：{}'.format(self.site.name, status))
                '''
                {
                  "status": "0",
                  "data": "抱歉",
                  "message": "您今天已经签到过了，请勿重复刷新。"
                }
                {
                  "status": "1",
                  "data": "&nbsp;(签到已得12)",
                  "message": "<p>这是您的第 <b>2</b> 次签到，已连续签到 <b>1</b> 天。</p><p>本次签到获得 <b>12</b> 克猫粮。</p>"
                }
                '''
                if status == '0' or status == '1':
                    message = res.json().get('message').replace('\n', '')
                    self.update_sign_info(message)
                    return CommonResponse.success(msg=message)
                else:
                    return CommonResponse.success(msg='签到失败！')

            if 'btschool' in self.my_site.mirror:
                # logger.info(res.status_code)
                logger.debug(f'学校签到：{res.text}')
                text = self.parse(res, '//script/text()')
                logger.debug('解析签到返回信息：{text}')
                if len(text) > 0:
                    location = self.parse_school_location(text)
                    logger.debug(f'学校签到链接：{location}')
                    if 'index.php?action=addbonus' in location:
                        res = self.spider.send_request(url=f'{self.my_site.mirror}{location.lstrip("/")}')
                        logger.info(res.content)
                # sign_in_text = self.parse(res, '//a[@href="index.php"]/font//text()')
                # sign_in_stat = self.parse(res, '//a[contains(@href,"addbouns")]')
                sign_in_text = self.parse(res, self.site.sign_info_content)
                sign_in_stat = self.parse(res, '//a[contains(@href,"index.php?action=addbonus")]')
                logger.info('{} 签到反馈：{}'.format(self.site.name, sign_in_text))
                if res.status_code == 200 and len(sign_in_stat) <= 0:
                    message = ''.join(sign_in_text) if len(sign_in_text) >= 1 else '您已在其他地方签到，请勿重复操作！'
                    self.update_sign_info(message)
                    return CommonResponse.success(msg=message)
                return CommonResponse.error(msg=f'签到失败！请求响应码：{res.status_code}')
            if res.status_code == 200:
                status = res.text
                # logger.info(status)
                # status = ''.join(self.parse(res, '//a[contains(@href,{})]/text()'.format(self.site.page_sign_in)))
                # 检查是否签到成功！
                # if '签到得魔力' in converter.convert(status):
                haidan_sign_str = '<input type="submit" id="modalBtn" ' \
                                  'style="cursor: default;" disabled class="dt_button" value="已经打卡" />'
                if haidan_sign_str in status \
                        or '(获得' in status \
                        or '签到已得' in status \
                        or '簽到已得' in status \
                        or '已签到' in status \
                        or '已簽到' in status \
                        or '已经签到' in status \
                        or '已經簽到' in status \
                        or '签到成功' in status \
                        or '簽到成功' in status \
                        or 'Attend got bonus' in status \
                        or 'Success' in status:
                    pass
                else:
                    return CommonResponse.error(msg='签到失败！')
                title_parse = self.parse(res, self.site.sign_info_title)
                content_parse = self.parse(res, self.site.sign_info_content)
                # if len(content_parse) <= 0:
                #     title_parse = self.parse(res, '//td[@id="outer"]//td[@class="embedded"]/b[1]/text()')
                #     content_parse = self.parse(res, '//td[@id="outer"]//td[@class="embedded"]/text()[1]')
                # if 'hdcity' in self.my_site.mirror:
                #     title_parse = self.parse(
                #         site,
                #         res,
                #         '//p[contains(text(),"本次签到获得魅力")]/preceding-sibling::h1[1]/span/text()'
                #     )
                #     content_parse = self.parse(res, '//p[contains(text(),"本次签到获得魅力")]/text()')
                logger.debug(f'{self.my_site.nickname}: 签到信息标题：{content_parse}')
                logger.debug(f'{self.my_site.nickname}: 签到信息：{content_parse}')
                title = ''.join(title_parse).strip()
                content = ''.join(content_parse).strip().replace('\n', '')
                message = f'{self.my_site} 签到返回信息：{title} {content}'
                logger.info(message)
                if len(message) <= 1:
                    message = f'{datetime.today().strftime("%Y-%m-%d %H:%M:%S")}打卡成功！'
                # message = ''.join(title).strip()
                self.update_sign_info(message)
                logger.info(f'{self.my_site.nickname}: {message}')
                return CommonResponse.success(msg=message)
            else:
                return CommonResponse.error(msg=f'请确认签到是否成功？？网页返回码：{res.status_code}')
        except Exception as e:
            msg = '{}签到失败！原因：{}'.format(self.site.name, e)
            logger.error(msg)
            logger.error(traceback.format_exc(limit=3))
            # raise
            # toolbox.send_text(msg)
            return CommonResponse.error(msg=msg)

    def get_filelist_cookie(self):
        """更新filelist站点COOKIE"""
        mirror = self.my_site.mirror
        logger.info(f'{self.site.name} 开始获取cookie！')
        session = requests.Session()
        headers = {
            'user-agent': self.my_site.user_agent
        }
        res = session.get(url=mirror, headers=headers)
        validator = ''.join(self.parse(res, '//input[@name="validator"]/@value'))
        login_url = ''.join(self.parse(res, '//form/@action'))
        login_method = ''.join(self.parse(res, '//form/@method'))
        filelist = DotDict(toml.load('db/filelist.toml'))
        login_res = session.request(
            url=f'{mirror}{login_url}',
            method=login_method,
            headers=headers,
            data={
                'validator': validator,
                'username': filelist.username,
                'password': filelist.password,
                'unlock': 0,
                'returnto': '',
            })
        cookies = ''
        logger.debug(f'res: {login_res.text}')
        logger.debug(f'cookies: {session.cookies.get_dict()}')
        # expires = [cookie for cookie in session.cookies if not cookie.expires]

        for key, value in session.cookies.get_dict().items():
            cookies += f'{key}={value};'
        self.my_site.cookie = cookies
        self.my_site.save()

    def get_mail_info(self, details_html, headers):
        """获取站点短消息"""
        mirror = self.my_site.mirror
        mail_check = len(details_html.xpath(self.site.my_mailbox_rule))
        notice_category_enable = toml.load('db/notice_category_enable.toml')
        if 'zhuque.in' in mirror:
            mail_res = self.spider.send_request(url=f'{mirror}api/user/getMainInfo', headers=headers)
            logger.debug(f'新消息: {mail_res.text}')
            mail_data = mail_res.json().get('data')
            mail = mail_data.get('unreadAdmin') + mail_data.get('unreadInbox') + mail_data.get('unreadSystem')
            if mail > 0:
                title = f'{self.site.name}有{mail}条新消息！'
                self.my_site.mail = mail
                self.my_site.save()
                # toolbox.send_text(title=title, message=title)
                return
        logger.info(f' 短消息 mail_check：{mail_check}')
        if mail_check > 0:
            title = f'{self.site.name}有新消息！'

            if 'torrentleech' in mirror:
                mail_count = int(''.join(details_html.xpath(self.site.my_mailbox_rule)))
                logger.info(f' 短消息 mail_count：{mail_count}')
                if mail_count <= 0:
                    self.my_site.mail = 0
                    self.my_site.save()
                    return

            if not notice_category_enable.get("message"):
                # toolbox.send_text(title=title, message=title)
                self.my_site.mail = 1
                self.my_site.save()
                return

            if mirror in [
                'https://monikadesign.uk/',
                'https://pt.hdpost.top/',
                'https://reelflix.xyz/',
            ]:
                mail_count = mail_check
            else:
                mail_str = ''.join(details_html.xpath(self.site.my_mailbox_rule))
                mail_count = re.sub(u"([^\u0030-\u0039])", "", mail_str)
                mail_count = int(mail_count) if mail_count else 0
            mail_list = []
            message_list = ''
            if mail_count > 0:
                logger.info(f'{self.site.name} 站点消息')
                if mirror in [
                    'https://hdchina.org/',
                    'https://hudbt.hust.edu.cn/',
                    'https://wintersakura.net/',
                ]:
                    message_res = requests.get(
                        url=f'{mirror}{self.site.page_message}', verify=False,
                        cookies=self.spider.cookie2dict(self.my_site.cookie),
                        headers={
                            'user-agent': self.my_site.user_agent
                        })
                else:
                    message_res = self.spider.send_request(url=f'{mirror}{self.site.page_message}')
                logger.info(f'PM消息页面：{message_res}')
                mail_list = self.parse(message_res, self.site.my_message_title)
                mail_list = [f'#### {mail.strip()} ...\n' for mail in mail_list]
                logger.debug(mail_list)
                mail = "".join(mail_list)
                logger.info(f'PM信息列表：{mail}')
                # 测试发送网站消息原内容
                message = f'\n# {self.site.name} 短消息  \n> 只显示第一页哦\n{mail}'
                message_list += message
            self.my_site.mail = len(mail_list)
            self.my_site.save()
            title = f'{self.site.name}有新消息！{len(mail_list) if len(mail_list) > 0 else ""}'
            # toolbox.send_text(title=title, message=message_list)
        else:
            self.my_site.mail = 0
            self.my_site.save()

    def get_notice_info(self, details_html):
        """获取站点公告信息"""
        mirror = self.my_site.mirror
        notice_category_enable = toml.load('db/notice_category_enable.toml')

        if mirror in [
            'https://monikadesign.uk/',
            'https://pt.hdpost.top/',
            'https://reelflix.xyz/',
        ]:
            pass
        else:
            notice_check = len(details_html.xpath(self.site.my_notice_rule))
            logger.debug(f'{self.site.name} 公告：{notice_check} ')

            if notice_check > 0:
                self.my_site.notice = notice_check
                self.my_site.save()
                title = f'{self.site.name}有新公告！'

                if not notice_category_enable.get("announcement"):
                    # toolbox.send_text(title=title, message=title)
                    return
                if mirror in [
                    'https://totheglory.im/',
                ]:
                    # toolbox.send_text(title=title, message=title)
                    pass
                else:
                    notice_str = ''.join(details_html.xpath(self.site.my_notice_rule))
                    notice_count = re.sub(u"([^\u0030-\u0039])", "", notice_str)
                    notice_count = int(notice_count) if notice_count else 0
                    message_list = ''
                    if notice_count > 0:

                        logger.info(f'{self.site.name} 站点公告')
                        if mirror in [
                            'https://hdchina.org/',
                            'https://hudbt.hust.edu.cn/',
                            'https://wintersakura.net/',
                        ]:
                            # 单独发送请求，解决冬樱签到问题
                            notice_res = requests.get(
                                url=f'{mirror}{self.site.page_index}', verify=False,
                                cookies=self.spider.cookie2dict(self.my_site.cookie),
                                headers={
                                    'user-agent': self.my_site.user_agent
                                })
                        else:
                            notice_res = self.spider.send_request(url=f'{mirror}{self.site.page_index}')
                        # notice_res = self.spider.send_request(self.my_site, url=mirror)
                        logger.debug(f'公告信息 {notice_res}')
                        notice_list = self.parse(notice_res, self.site.my_notice_title)
                        content_list = self.parse(
                            notice_res,
                            self.site.my_notice_content,
                        )
                        logger.debug(f'公告信息：{notice_list}')
                        notice_list = [n.xpath(
                            "string(.)", encoding="utf-8"
                        ).strip("\n").strip("\r").strip() for n in notice_list]
                        logger.debug(f'公告信息：{notice_list}')
                        logger.debug(content_list)
                        if len(content_list) > 0:
                            content_list = [
                                content.xpath("string(.)").replace("\r\n\r\n", "  \n> ").strip()
                                for content in content_list]
                            notice_list = [
                                f'## {title} \n> {content}\n\n' for
                                title, content in zip(notice_list, content_list)
                            ]
                        logger.debug(f'公告信息列表：{notice_list}')
                        # notice = '  \n\n### '.join(notice_list[:notice_count])
                        notice = ''.join(notice_list[:1])
                        message_list += f'# {self.site.name} 公告  \n## {notice}'
                        title = f'{self.site.name}有{notice_count}条新公告！'
                        # toolbox.send_text(title=title, message=message_list)
            else:
                self.my_site.mail = 0
                self.my_site.save()

    def get_userinfo_html(self, headers: dict):
        """请求抓取数据相关页面"""
        mirror = self.my_site.mirror
        user_detail_url = f'{mirror}{self.site.page_user.lstrip('/').format(self.my_site.user_id)}'
        logger.info(f'{self.site.name} 开始抓取站点个人主页信息，网址：{user_detail_url}')
        logger.info(f'当前站点 URL：{mirror}')
        if mirror in [
            'https://hdchina.org/',
            'https://hudbt.hust.edu.cn/',
            'https://wintersakura.net/',
        ]:
            # 单独发送请求，解决冬樱签到问题
            user_detail_res = requests.get(url=user_detail_url, verify=False,
                                           cookies=self.spider.cookie2dict(self.my_site.cookie),
                                           headers={
                                               'user-agent': self.my_site.user_agent
                                           })

        else:
            user_detail_res = self.spider.send_request(url=user_detail_url, headers=headers)
        logger.info(f"个人信息页面：{user_detail_res.status_code}")
        logger.info(f"个人信息页面：{user_detail_res.text}")
        if mirror in [
            'https://piggo.me/',
        ]:
            logger.debug('猪猪')
            html = user_detail_res.text
            if 'window.location.href' in html:
                pattern = r'href ="(.*?)"; </script>'
                match = re.search(pattern, html, re.DOTALL)
                html_code = match.group(1)
                logger.debug(html_code)
                user_detail_url = f'{mirror}{html_code.lstrip("/")}'
                user_detail_res = self.spider.send_request(url=user_detail_url, headers=headers)
                logger.info(f"个人信息页面：{user_detail_res.status_code}")
                logger.info(f"个人信息页面：{user_detail_res.text}")
        if user_detail_res.status_code != 200:
            msg = f'{self.site.name} 个人主页访问错误，错误码：{user_detail_res.status_code}'
            logger.debug(msg)
            return CommonResponse.error(msg=msg)
        if mirror in [
            'https://greatposterwall.com/', 'https://dicmusic.com/',
        ]:
            user_detail = user_detail_res.json()
            if user_detail.get('status') != 'success':
                return CommonResponse.error(
                    msg=f'{self.site.name} 个人主页访问错误，错误：{user_detail.get("status")}')
            details_html = user_detail.get('response')
        elif mirror in [
            'https://zhuque.in/'
        ]:
            user_detail = user_detail_res.json()
            if user_detail.get('status') != 200:
                return CommonResponse.error(
                    msg=f'{self.site.name} 个人主页访问错误，错误：{user_detail.get("status")}')
            details_html = user_detail.get('data')
        elif mirror in [
            'https://totheglory.im/',
        ]:
            details_html = etree.HTML(user_detail_res.content)
        elif mirror in [
            'https://piggo.me/',
        ]:
            logger.debug('猪猪')
            details_html = etree.HTML(user_detail_res.text.encode('utf8'))
        else:
            details_html = etree.HTML(user_detail_res.text)
        if 'btschool' in mirror:
            text = details_html.xpath('//script/text()')
            logger.debug('学校：{}'.format(text))
            if len(text) > 0:
                try:
                    location = self.parse_school_location(text)
                    logger.debug('学校重定向链接：{}'.format(location))
                    if '__SAKURA' in location:
                        res = self.spider.send_request(url=mirror + location.lstrip('/'))
                        details_html = etree.HTML(res.text)
                except Exception as e:
                    logger.debug(f'BT学校个人主页访问失败！{e}')
        if 'hdchina.org' in mirror:
            cookies = ''
            logger.debug(f'res: {user_detail_res.text}')
            logger.debug(f'cookies: {user_detail_res.cookies.get_dict()}')
            # expires = [cookie for cookie in session.cookies if not cookie.expires]
            logger.debug(f'请求中的cookie: {user_detail_res.cookies}')

            # for key, value in user_detail_res.cookies.get_dict().items():
            #     cookies += f'{key}={value};'
            # self.my_site.expires = datetime.now() + timedelta(minutes=30)
            # self.my_site.cookie = cookies
            # self.my_site.save()
        res = self.parse_userinfo_html(details_html=details_html)
        if res.code != 0:
            return res
        return CommonResponse.success(data=details_html)

    def get_seeding_html(self, headers: dict, details_html=None):
        """请求做种数据相关页面"""
        mirror = self.my_site.mirror
        if mirror in [
            'https://hdchina.org/'
        ]:
            seeding_detail_url = mirror + self.site.page_seeding.lstrip('/')
        else:
            seeding_detail_url = mirror + self.site.page_seeding.lstrip('/').format(self.my_site.user_id)
        logger.info(f'{self.site.name} 开始抓取站点做种信息，网址：{seeding_detail_url}')
        if mirror in [
            'https://greatposterwall.com/', 'https://dicmusic.com/'
        ]:
            seeding_detail_res = self.spider.send_request(url=mirror + self.site.page_mybonus).json()
            if seeding_detail_res.get('status') != 'success':
                return CommonResponse.error(
                    msg=f'{self.site.name} 做种信息访问错误，错误：{seeding_detail_res.get("status")}')
            seeding_html = seeding_detail_res.get('response')
        elif mirror in [
            'https://lemonhd.org/',
            'https://www.htpt.cc/',
            'https://pt.btschool.club/',
            'https://pt.keepfrds.com/',
            'https://pterclub.com/',
            'https://monikadesign.uk/',
            'https://pt.hdpost.top/',
            'https://reelflix.xyz/',
            'https://totheglory.im/',
        ]:
            logger.info(mirror)
            seeding_html = details_html
        elif 'hdchina.org' in mirror:
            # logger.info(details_html.content)
            # details_html = etree.HTML(details_html.text)
            csrf = details_html.xpath('//meta[@name="x-csrf"]/@content')
            logger.debug(f'CSRF Token：{csrf}')

            seeding_detail_res = requests.post(
                url=seeding_detail_url, verify=False,
                cookies=self.spider.cookie2dict(self.my_site.cookie),
                headers={
                    'user-agent': self.my_site.user_agent
                },
                data={
                    'userid': self.my_site.user_id,
                    'type': 'seeding',
                    'csrf': ''.join(csrf)
                })
            logger.debug(f'cookie: {self.my_site.cookie}')
            logger.debug(f'做种列表：{seeding_detail_res.text}')
            seeding_html = etree.HTML(seeding_detail_res.text)
        elif 'club.hares.top' in mirror:
            seeding_detail_res = self.spider.send_request(url=seeding_detail_url, headers={
                'Accept': 'application/json'
            })
            logger.debug(f'白兔做种信息：{seeding_detail_res.text}')
            seeding_html = seeding_detail_res.json()
            logger.debug(f'白兔做种信息：{seeding_html}')
        else:
            if mirror in [
                'https://wintersakura.net/',
                'https://hudbt.hust.edu.cn/',
            ]:
                logger.info(f"{self.site.name} 抓取做种信息")
                # 单独发送请求，解决冬樱签到问题
                seeding_detail_res = requests.get(url=seeding_detail_url, verify=False,
                                                  cookies=self.spider.cookie2dict(self.my_site.cookie),
                                                  headers={
                                                      'user-agent': self.my_site.user_agent
                                                  })

            else:
                seeding_detail_res = self.spider.send_request(url=seeding_detail_url, headers=headers)
            # logger.debug('做种信息：{}'.format(seeding_detail_res.text))
            if seeding_detail_res.status_code != 200:
                return CommonResponse.error(
                    msg=f'{self.site.name} 做种信息访问错误，错误码：{seeding_detail_res.status_code}')
            if mirror.find('m-team') > 0:
                seeding_text = self.get_m_team_seeding(seeding_detail_res)
                seeding_html = etree.HTML(seeding_text)
            elif mirror.find('jpopsuki.eu') > 0:
                seeding_text = self.get_jpop_seeding(seeding_detail_res)
                seeding_html = etree.HTML(seeding_text)
            else:
                seeding_html = etree.HTML(seeding_detail_res.text)
        self.parse_seeding_html(seeding_html=seeding_html)
        return CommonResponse.success(data=seeding_html)

    def get_m_team_seeding(self, seeding_detail_res):
        url_list = self.parse(
            seeding_detail_res,
            f'//p[1]/font[2]/following-sibling::'
            f'a[contains(@href,"?type=seeding&userid={self.my_site.user_id}&page=")]/@href'
        )
        if len(url_list) > 0:
            pages = re.search(r'page=(\d+)', url_list[-1]).group(1)
            logger.info(pages)
            url_list = [
                f"?type=seeding&userid={self.my_site.user_id}&page={page}"
                for page in list(range(2, int(pages) + 1))
            ]
        logger.info(url_list)
        seeding_text = seeding_detail_res.text.encode('utf8')
        for url in url_list:
            seeding_url = f'{self.my_site.mirror}getusertorrentlist.php{url}'
            seeding_res = self.spider.send_request(url=seeding_url)
            seeding_text += seeding_res.text.encode('utf8')
        return seeding_text

    def get_jpop_seeding(self, seeding_detail_res):
        url_list = self.parse(
            seeding_detail_res,
            f'//div[@id="ajax_torrents"]/div[@class="linkbox"][1]/a/@href'
        )[:-2]
        if len(url_list) > 0:
            url_list = [''.join(url) for url in url_list]
            logger.info(url_list)

        seeding_text = seeding_detail_res.text.encode('utf8')
        for url in url_list:
            seeding_res = self.spider.send_request(url=url)
            seeding_text += seeding_res.text.encode('utf8')
        return seeding_text

    def get_time_join(self, details_html):
        try:
            mirror = self.my_site.mirror
            if 'greatposterwall' in mirror or 'dicmusic' in mirror:
                logger.debug(details_html)
                details_response = details_html.get('response')
                stats = details_response.get('stats')
                self.my_site.time_join = stats.get('joinedDate')
                self.my_site.latest_active = stats.get('lastAccess')
                self.my_site.save()
            elif 'zhuque.in' in mirror:
                self.my_site.time_join = datetime.fromtimestamp(details_html.get(self.site.my_time_join_rule))
                self.my_site.save()
            else:
                logger.debug(f'注册时间：{details_html.xpath(self.site.my_time_join_rule)}')
                if mirror in [
                    'https://monikadesign.uk/',
                    'https://pt.hdpost.top/',
                    'https://reelflix.xyz/',
                ]:
                    time_str = ''.join(details_html.xpath(self.site.my_time_join_rule))
                    time_str = re.sub(u"[\u4e00-\u9fa5]", "", time_str).strip()
                    time_join = datetime.strptime(time_str, '%b %d %Y')
                    logger.debug(f'注册时间：{time_join}')
                    self.my_site.time_join = time_join
                elif mirror in [
                    'https://hd-torrents.org/',
                ]:
                    self.my_site.time_join = datetime.strptime(
                        ''.join(details_html.xpath(self.site.my_time_join_rule)).replace('\xa0', ''),
                        '%d/%m/%Y %H:%M:%S'
                    )
                elif mirror in [
                    'https://hd-space.org/',
                ]:
                    self.my_site.time_join = datetime.strptime(
                        ''.join(details_html.xpath(self.site.my_time_join_rule)).replace('\xa0', ''),
                        '%B %d, %Y,%H:%M:%S'
                    )
                elif mirror in [
                    'https://jpopsuki.eu/',
                ]:
                    self.my_site.time_join = datetime.strptime(
                        ''.join(details_html.xpath(self.site.my_time_join_rule)).replace('\xa0', ''),
                        '%b %d %Y, %H:%M'
                    )
                elif mirror in [
                    'https://www.torrentleech.org/',
                ]:
                    self.my_site.time_join = dateutil.parser.parse(
                        ''.join(details_html.xpath(self.site.my_time_join_rule)))
                elif mirror in [
                    'https://exoticaz.to/',
                    'https://cinemaz.to/',
                    'https://avistaz.to/',
                ]:
                    time_str = ''.join(details_html.xpath(self.site.my_time_join_rule)).split('(')[0].strip()
                    self.my_site.time_join = datetime.strptime(time_str, '%d %b %Y %I:%M %p')
                else:
                    time_join = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', ''.join(
                        details_html.xpath(self.site.my_time_join_rule)
                    ).strip())
                    self.my_site.time_join = ''.join(time_join)
                self.my_site.latest_active = datetime.now()
                self.my_site.save()
        except Exception as e:
            msg = f'🆘 {self.site.name} 注册时间获取出错啦！{e}'
            logger.error(msg)
            logger.error(traceback.format_exc(3))

    def get_hour_sp(self, headers: dict = dict):
        """获取时魔"""
        mirror = self.my_site.mirror
        url = mirror + self.site.page_mybonus
        if mirror in [
            'https://www.torrentleech.org/',
        ]:
            return CommonResponse.success(data=0)
        if mirror in [
            'https://monikadesign.uk/',
            'https://pt.hdpost.top/',
            'https://reelflix.xyz/',
            'https://exoticaz.to/',
            'https://cinemaz.to/',
            'https://avistaz.to/',
        ]:
            url = url.format(self.my_site.user_id)
        logger.info(f'魔力页面链接：{url}')
        try:
            if 'iptorrents' in mirror:
                bonus_hour = 0
            else:
                if mirror in [
                    'https://hdchina.org/',
                    'https://hudbt.hust.edu.cn/',
                    'https://wintersakura.net/',
                ]:
                    # 单独发送请求，解决冬樱签到问题
                    response = requests.get(url=url, verify=False,
                                            cookies=self.spider.cookie2dict(self.my_site.cookie),
                                            headers={
                                                'user-agent': self.my_site.user_agent
                                            })
                else:
                    response = self.spider.send_request(url=url, headers=headers)
                """
                if 'btschool' in site.url:
                    # logger.info(response.text.encode('utf8'))
                    url = self.parse(response, '//form[@id="challenge-form"]/@action[1]')
                    data = {
                        'md': ''.join(self.parse(response, '//form[@id="challenge-form"]/input[@name="md"]/@value')),
                        'r': ''.join(self.parse(response, '//form[@id="challenge-form"]/input[@name="r"]/@value'))
                    }
                    logger.info(data)
                    logger.debug('学校时魔页面url：', url)
                    response = self.send_request(
                        my_site=my_site,
                        url=mirror + ''.join(url).lstrip('/'),
                        method='post',
                        # headers=headers,
                        data=data,
                        delay=60
                    )
                    """
                # response = converter.convert(response.content)
                # logger.debug('时魔响应：{}'.format(response.content))
                # logger.debug('转为简体的时魔页面：', str(res))
                if 'zhuque.in' in mirror:
                    # 获取朱雀时魔
                    bonus_hour = response.json().get('data').get('E')
                elif mirror in [
                    'https://greatposterwall.com/',
                    'https://dicmusic.com/'
                ]:
                    # 获取朱雀时魔
                    bonus_hour = response.json().get('response').get('userstats').get('seedingBonusPointsPerHour')
                else:
                    if response.status_code == 200:
                        res_list = self.parse(response, self.site.my_per_hour_bonus_rule)
                        if len(res_list) <= 0:
                            CommonResponse.error(msg='时魔获取失败！')
                        if 'u2.dmhy.org' in mirror:
                            res_list = ''.join(res_list).split('，')
                            res_list.reverse()
                        logger.debug('时魔字符串：{}'.format(res_list))
                        if len(res_list) <= 0:
                            message = f'{self.site.name} 时魔获取失败！'
                            logger.error(message)
                            return CommonResponse.error(msg=message, data=0)
                        bonus_hour = get_decimals(res_list[0].replace(',', ''))
                    else:
                        message = f'{self.site.name} 时魔获取失败！'
                        logger.error(message)
                        return CommonResponse.error(msg=message)
            today = str(datetime.now().date())
            self.my_site.status.get(today).update({
                'bonus_hour': bonus_hour if bonus_hour else 0,
                'updated_at': str(datetime.now()),
            })
            self.my_site.save()
            return CommonResponse.success(data=bonus_hour)
        except Exception as e:
            # 打印异常详细信息
            message = f'{self.site.name} 时魔获取失败！{e}'
            logger.error(message)
            logger.error(traceback.format_exc(limit=3))
            return CommonResponse.error(msg=message, data=0)

    def send_status_request(self):
        """请求抓取数据相关页面"""
        mirror = self.my_site.mirror
        # uploaded_detail_url = mirror + self.site.page_uploaded.lstrip('/').format(self.my_site.user_id)
        seeding_detail_url = mirror + self.site.page_seeding.lstrip('/').format(self.my_site.user_id)
        # completed_detail_url = mirror + self.site.page_completed.lstrip('/').format(self.my_site.user_id)
        # leeching_detail_url = mirror + self.site.page_leeching.lstrip('/').format(self.my_site.user_id)
        err_msg = []
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            status_today = self.my_site.status.get(today)

            if status_today is None:
                latest_date = max(self.my_site.status.keys())
                status_latest = self.my_site.status.get(latest_date)
                status_latest['created_at'] = str(datetime.now())
                logger.info(f'status_latest: {status_latest}')
                self.my_site.status[today] = status_latest
                self.my_site.save()
            headers = {}
            if mirror in [
                'https://hdchina.org/',
                'https://hudbt.hust.edu.cn/',
                'https://wintersakura.net/',
            ]:
                headers = {
                    'user-agent': self.my_site.user_agent
                }
            if 'zhuque.in' in mirror:
                zhuque_header = self.get_zhuque_header(mirror)
                headers.update(zhuque_header)
            if mirror in ['https://filelist.io/']:
                # 获取filelist站点COOKIE
                self.get_filelist_cookie()
            # 发送请求，请求个人主页
            details_html = self.get_userinfo_html(headers=headers)
            if details_html.code != 0:
                detail_msg = f'个人主页解析失败!'
                err_msg.append(detail_msg)
                logger.warning(f'{self.my_site.nickname} {detail_msg}')
                return CommonResponse.error(msg=detail_msg)
            # 解析注册时
            self.get_time_join(details_html.data)
            # 发送请求，请求做种信息页面
            if mirror not in [
                'https://zhuque.in/',
            ]:
                seeding_html = self.get_seeding_html(headers=headers, details_html=details_html.data)
                if seeding_html.code != 0:
                    seeding_msg = f'做种页面访问失败!'
                    err_msg.append(seeding_msg)
                    logger.warning(f'{self.my_site.nickname} {seeding_msg}')
            # 请求时魔页面,信息写入数据库
            hour_bonus = self.get_hour_sp(headers=headers)
            if hour_bonus.code != 0:
                bonus_msg = f'时魔获取失败!'
                err_msg.append(bonus_msg)
                logger.warning(f'{self.my_site.nickname} {bonus_msg}')
            # 请求邮件页面，直接推送通知到手机
            if mirror not in [
                'https://dicmusic.com/',
                'https://greatposterwall.com/',
                'https://zhuque.in/',
            ]:
                if details_html.code == 0:
                    # 请求公告信息，直接推送通知到手机
                    self.get_notice_info(details_html.data)
                    # 请求邮件信息,直接推送通知到手机
                    self.get_mail_info(details_html.data, headers=headers)

            # return self.parse_status_html(self.my_site, data)
            status = self.my_site.status.get(today)
            if len(err_msg) <= 3:
                return CommonResponse.success(
                    msg=f'{self.my_site.nickname} 数据更新完毕! {("🆘 " + " ".join(err_msg)) if len(err_msg) > 0 else ""}',
                    data=status)
            return CommonResponse.error(msg=f'{self.my_site.nickname} 数据更新失败! 🆘 {" ".join(err_msg)}')
        except RequestException as nce:
            msg = f'🆘 与网站 {self.my_site.nickname} 建立连接失败，请检查网络？？'
            logger.error(msg)
            logger.error(traceback.format_exc(limit=5))
            return CommonResponse.error(msg=msg)
        except Exception as e:
            message = f'🆘 {self.my_site.nickname} 统计个人数据失败！原因：{err_msg} {e}'
            logger.error(message)
            logger.error(traceback.format_exc(limit=3))
            return CommonResponse.error(msg=message)

    def parse_userinfo_html(self, details_html):
        """解析个人主页"""
        mirror = self.my_site.mirror
        today = str(datetime.now().date())
        today_state = self.my_site.status.get(today)

        with lock:
            try:
                if 'greatposterwall' in mirror or 'dicmusic' in mirror:
                    logger.debug(details_html)
                    stats = details_html.get('stats')
                    downloaded = stats.get('downloaded')
                    uploaded = stats.get('uploaded')
                    ratio_str = stats.get('ratio').replace(',', '')
                    ratio = 'inf' if ratio_str == '∞' else ratio_str
                    if os.getenv("MYSQL_CONNECTION") and ratio == 'inf':
                        ratio = 0
                    my_level = details_html.get('personal').get('class').strip(" ")
                    community = details_html.get('community')
                    seed = community.get('seeding')
                    leech = community.get('leeching')
                    today_state.update({
                        'ratio': float(ratio),
                        'my_level': my_level,
                        'downloaded': downloaded,
                        'uploaded': uploaded,
                        'my_score': 0,
                        'seed': seed,
                        'leech': leech,
                        'updated_at': str(datetime.now())
                    })
                    if 0 < float(ratio) < 1:
                        msg = f'{self.site.name} 分享率 {ratio} 过低，请注意'
                        logger.warning(msg)
                        # 消息发送
                        # toolbox.send_text(title=msg, message=msg)
                elif 'zhuque.in' in mirror:
                    logger.debug(details_html)
                    downloaded = details_html.get('download')
                    uploaded = details_html.get('upload')
                    seeding_size = details_html.get('seedSize')
                    my_bonus = details_html.get('bonus')
                    my_score = details_html.get('seedBonus')
                    seed_days = int(details_html.get('seedTime') / 3600 / 24)
                    ratio = uploaded / downloaded if downloaded > 0 else 'inf'
                    if os.getenv("MYSQL_CONNECTION") and ratio == 'inf':
                        ratio = 0
                    invitation = details_html.get(self.site.my_invitation_rule)
                    my_level = details_html.get('class').get('name').strip(" ")
                    seed = details_html.get('seeding')
                    leech = details_html.get('leeching')
                    if 0 < float(ratio) < 1:
                        msg = f'{self.site.name} 分享率 {ratio} 过低，请注意'
                        # toolbox.send_text(title=msg, message=msg)
                    today_state.update({
                        'ratio': ratio,
                        'downloaded': downloaded,
                        'uploaded': uploaded,
                        'my_bonus': my_bonus,
                        'my_score': my_score,
                        'invitation': invitation,
                        'seed': seed,
                        'leech': leech,
                        'my_level': my_level,
                        'seed_volume': seeding_size,
                        'seed_days': seed_days
                    })

                else:
                    leech_status = details_html.xpath(self.site.my_leech_rule)
                    seed_status = details_html.xpath(self.site.my_seed_rule)
                    msg = f'下载数目字符串：{leech_status} \n  上传数目字符串：{seed_status}'
                    if len(leech_status) + len(seed_status) <= 0 and mirror.find('hd-space') < 0:
                        err_msg = f'{self.my_site.nickname} 获取用户数据失败：{msg}'
                        logger.error(err_msg)
                        return CommonResponse.error(msg=err_msg)
                    logger.info(msg)
                    leech = re.sub(r'\D', '', ''.join(details_html.xpath(self.site.my_leech_rule)).strip())
                    logger.debug(f'当前下载数：{leech}')
                    seed = ''.join(details_html.xpath(self.site.my_seed_rule)).strip()
                    logger.debug(f'当前做种数：{seed}')

                    # seed = len(seed_vol_list)
                    downloaded = ''.join(
                        details_html.xpath(self.site.my_downloaded_rule)
                    ).replace(':', '').replace('\xa0\xa0', '').replace('i', '').replace(',', '').strip(' ')
                    uploaded = ''.join(
                        details_html.xpath(self.site.my_uploaded_rule)
                    ).replace(':', '').replace('i', '').replace(',', '').strip(' ')
                    if 'hdchina' in mirror:
                        downloaded = downloaded.split('(')[0].replace(':', '').strip()
                        uploaded = uploaded.split('(')[0].replace(':', '').strip()
                    downloaded = FileSizeConvert.parse_2_byte(downloaded)
                    uploaded = FileSizeConvert.parse_2_byte(uploaded)
                    # 获取邀请信息
                    invitation = ''.join(
                        details_html.xpath(self.site.my_invitation_rule)
                    ).strip(']:').replace('[', '').strip()
                    logger.debug(f'邀请：{invitation}')
                    if '没有邀请资格' in invitation or '沒有邀請資格' in invitation:
                        invitation = 0
                    elif '/' in invitation:
                        invitation_list = [int(n) for n in invitation.split('/')]
                        invitation = sum(invitation_list)
                    elif '(' in invitation:
                        invitation_list = [int(get_decimals(n)) for n in invitation.split('(')]
                        invitation = sum(invitation_list)
                    elif not invitation:
                        invitation = 0
                    else:
                        invitation = int(re.sub('\D', '', invitation))
                    logger.debug(f'当前获取邀请数："{invitation}"')
                    # 获取用户等级信息
                    my_level_1 = ''.join(
                        details_html.xpath(self.site.my_level_rule)
                    ).replace(
                        'UserClass_Name', ''
                    ).replace('_Name', '').replace('fontBold', '').replace(
                        'Class: ', '').strip(" ").strip()
                    if 'hdcity' in mirror:
                        my_level = my_level_1.replace('[', '').replace(']', '').strip(" ").strip()
                    else:
                        my_level = re.sub(u"([^\u0041-\u005a\u0061-\u007a])", "", my_level_1).strip(" ")
                    my_level = my_level.strip(" ") if my_level != '' else ' '
                    logger.debug('用户等级：{}-{}'.format(my_level_1, my_level))
                    # 获取字符串中的魔力值
                    my_bonus = ''.join(
                        details_html.xpath(self.site.my_bonus_rule)
                    ).replace(',', '').strip()
                    logger.debug('魔力：{}'.format(details_html.xpath(self.site.my_bonus_rule)))
                    if my_bonus:
                        my_bonus = get_decimals(my_bonus)
                    if mirror.find('jpopsuki.eu') > 0:
                        pass
                    # 获取做种积分
                    my_score_1 = ''.join(
                        details_html.xpath(self.site.my_score_rule)
                    ).strip('N/A').replace(',', '').strip()
                    if my_score_1 != '':
                        my_score = get_decimals(my_score_1)
                    else:
                        my_score = 0
                    # 获取HR信息
                    hr = ''.join(
                        details_html.xpath(self.site.my_hr_rule)
                    ).replace('H&R:', '').replace("  ", "").strip()
                    if mirror in [
                        'https://monikadesign.uk/',
                        'https://pt.hdpost.top/',
                        'https://reelflix.xyz/',
                    ]:
                        hr = hr.replace('\n', '').replace('有效', '').replace(':', '').strip('/').strip()
                    my_hr = hr if hr else '0'
                    logger.debug(f'h&r: "{hr}" ,解析后：{my_hr}')
                    # 做种与下载信息
                    seed = int(get_decimals(seed)) if seed else 0
                    leech = int(get_decimals(leech)) if leech else 0
                    logger.debug(f'当前上传种子数：{seed}')
                    logger.debug(f'当前下载种子数：{leech}')
                    # 分享率信息
                    if float(downloaded) == 0:
                        ratio = float('inf')
                        if os.getenv("MYSQL_CONNECTION"):
                            ratio = 0
                    else:
                        ratio = round(int(uploaded) / int(downloaded), 3)
                    if 0 < ratio <= 1:
                        title = f'{self.site.name}  站点分享率告警：{ratio}'
                        message = f'{title}  \n'
                        # toolbox.send_text(title=title, message=message)
                    logger.debug('站点：{}'.format(self.site.name))
                    logger.debug('魔力：{}'.format(my_bonus))
                    logger.debug('积分：{}'.format(my_score if my_score else 0))
                    logger.debug('下载量：{}'.format(FileSizeConvert.parse_2_file_size(downloaded)))
                    logger.debug('上传量：{}'.format(FileSizeConvert.parse_2_file_size(uploaded)))
                    logger.debug('邀请：{}'.format(invitation))
                    logger.debug('H&R：{}'.format(my_hr))
                    logger.debug('上传数：{}'.format(seed))
                    logger.debug('下载数：{}'.format(leech))
                    defaults = {
                        'ratio': float(ratio) if ratio else 0,
                        'downloaded': int(downloaded),
                        'uploaded': int(uploaded),
                        'my_bonus': float(my_bonus),
                        'my_score': float(
                            my_score) if my_score != '' else 0,
                        'seed': seed,
                        'leech': leech,
                        'invitation': invitation,
                        'publish': 0,  # todo 待获取
                        'seed_days': 0,  # todo 待获取
                        'my_hr': my_hr,
                        'my_level': my_level,
                    }
                    if mirror in [
                        'https://nextpt.net/',
                    ]:
                        # logger.debug(self.site.hour_sp_rule)
                        res_bonus_hour_list = details_html.xpath(self.site.my_per_hour_bonus_rule)
                        # logger.debug(details_html)
                        # logger.debug(res_bonus_hour_list)
                        res_bonus_hour = ''.join(res_bonus_hour_list)
                        bonus_hour = get_decimals(res_bonus_hour)
                        # 飞天邀请获取
                        logger.info(f'邀请页面：{mirror}Invites')
                        res_next_pt_invite = self.spider.send_request(f'{mirror}Invites')
                        logger.debug(res_next_pt_invite.text)
                        str_next_pt_invite = ''.join(self.parse(
                            res_next_pt_invite,
                            self.site.my_invitation_rule))
                        logger.debug(f'邀请字符串：{str_next_pt_invite}')
                        list_next_pt_invite = re.findall('\d+', str_next_pt_invite)
                        logger.debug(list_next_pt_invite)
                        invitation = int(list_next_pt_invite[0]) - int(list_next_pt_invite[1])
                        defaults.update({
                            'bonus_hour': bonus_hour,
                            'invitation': invitation,
                            'updated_at': str(datetime.now())
                        })
                    today_state.update(defaults)
                self.my_site.status[today] = today_state
                self.my_site.save()
                return CommonResponse.success(data=today_state)
            except Exception as e:
                # 打印异常详细信息
                message = f'{self.site.name} 解析做种信息：失败！原因：{e}'
                logger.error(message)
                logger.error(traceback.format_exc(limit=3))
                # raise
                # toolbox.send_text('# <font color="red">' + message + '</font>  \n')
                return CommonResponse.error(msg=message)

    def parse_seeding_html(self, seeding_html):
        """解析做种页面"""
        mirror = self.my_site.mirror
        today = str(datetime.now().date())
        today_state = self.my_site.status.get(today)
        logger.info(f'开始解析做种信息，{mirror}')
        with lock:
            try:
                if 'greatposterwall' in mirror or 'dicmusic' in mirror:
                    # logger.debug(seeding_html)
                    mail_str = seeding_html.get("notifications").get("messages")
                    notice_str = seeding_html.get("notifications").get("notifications")
                    mail = int(mail_str) + int(notice_str)
                    if mail > 0:
                        title = f'{self.site.name} 有{mail}条新短消息，请注意及时查收！'
                        msg = f'### <font color="red">{title}</font>  \n'
                        # 测试发送网站消息原内容
                        # toolbox.send_text(title=title, message=msg)
                    if 'greatposterwall' in mirror:
                        userdata = seeding_html.get('userstats')
                        my_bonus = userdata.get('bonusPoints')
                        # if userdata.get('bonusPoints') else 0
                        seeding_size = userdata.get('seedingSize')
                        # if userdata.get('seedingSize') else 0
                        bonus_hour = userdata.get('seedingBonusPointsPerHour')
                        # if userdata.get('seedingBonusPointsPerHour') else 0
                    if 'dicmusic' in mirror:
                        logger.debug('海豚')
                        """未取得授权前不开放本段代码，谨防ban号
                        bonus_res = self.spider.send_request(self.my_site, url=mirror + self.site.page_seeding, timeout=15)
                        sp_str = self.parse(bonus_res, '//h3[contains(text(),"总积分")]/text()')
                        my_bonus = get_decimals(''.join(sp_str))
                        hour_sp_str = self.parse(bonus_res, '//*[@id="bprates_overview"]/tbody/tr/td[3]/text()')
                        self.my_site.bonus_hour = ''.join(hour_sp_str)
                        seeding_size_str = self.parse(bonus_res,
                                                      '//*[@id="bprates_overview"]/tbody/tr/td[2]/text()')
                        seeding_size = FileSizeConvert.parse_2_byte(''.join(seeding_size_str))
                        """
                        my_bonus = 0
                        bonus_hour = 0
                        seeding_size = 0
                    today_state.update({
                        'my_bonus': my_bonus,
                        'my_score': 0,
                        # 做种体积
                        'seed_volume': seeding_size,
                        'bonus_hour': bonus_hour,
                        'mail': mail,
                        'updated_at': str(datetime.now())
                    })

                else:
                    try:
                        seed_vol_list = seeding_html.xpath(self.site.my_seed_vol_rule)
                        logger.debug('做种数量seeding_vol：{}'.format(seed_vol_list))
                    except:
                        pass
                    if mirror in [
                        'https://lemonhd.org/',
                        'https://oldtoons.world/',
                        'https://xingtan.one/',
                        'https://piggo.me/',
                        'http://hdmayi.com/',
                        'https://hdmayi.com/',
                        'https://hdvideo.one/',
                        'https://ptchina.org/',
                        'https://oldtoons.world/',
                        'https://pt.0ff.cc/',
                        'https://1ptba.com/',
                        'https://hdtime.org/',
                        'https://hhanclub.top/',
                        'https://pt.eastgame.org/',
                        'https://wintersakura.net/',
                        'https://gainbound.net/',
                        'http://pt.tu88.men/',
                        'https://srvfi.top/',
                        'https://www.hddolby.com/',
                        'https://gamegamept.cn/',
                        'https://hdatmos.club/',
                        'https://hdfans.org/',
                        'https://audiences.me/',
                        'https://www.nicept.net/',
                        'https://u2.dmhy.org/',
                        'https://hdpt.xyz/',
                        'https://carpt.net/',
                        'https://www.icc2022.com/',
                        'http://leaves.red/',
                        'https://leaves.red/',
                        'https://www.htpt.cc/',
                        'https://pt.btschool.club/',
                        'https://azusa.wiki/',
                        'https://pt.2xfree.org/',
                        'http://www.oshen.win/',
                        'https://www.oshen.win/',
                        'https://ptvicomo.net/',
                        'https://star-space.net/',
                        'https://www.hdkyl.in/',
                        'https://sharkpt.net/',
                        'https://pt.soulvoice.club/',
                        'https://dajiao.cyou/',
                        'https://www.okpt.net/',
                        'https://pandapt.net/',
                        'https://ubits.club/',
                        'https://abroad.agsvpt.com/',
                        'https://www.agsvpt.com/',
                        'https://public.ecustpt.eu.org/',
                        'https://www.ptlsp.com/',
                        'https://ptcafe.club/',
                        'https://hdvbits.com/',
                        'https://pt.gtk.pw/',
                        'https://www.tjupt.org/',
                        'https://tjupt.org/',
                    ]:
                        # 获取到的是整段，需要解析
                        logger.debug('做种体积：{}'.format(len(seed_vol_list)))
                        if len(seed_vol_list) < 1:
                            seed_vol_all = 0
                        else:
                            seeding_str = ''.join(
                                seed_vol_list
                            ).replace('\xa0', ':').replace('i', '')
                            logger.debug('做种信息字符串：{}'.format(seeding_str))
                            # if ':' in seeding_str:
                            #     seed_vol_size = seeding_str.split(':')[-1].strip()
                            # if '：' in seeding_str:
                            #     seed_vol_size = seeding_str.split('：')[-1].strip()
                            # if '&nbsp;' in seeding_str:
                            #     seed_vol_size = seeding_str.split('&nbsp;')[-1].strip()
                            # if 'No record' in seeding_str:
                            #     seed_vol_size = 0
                            seed_vol_size = extract_storage_size(seeding_str)
                            seed_vol_all = FileSizeConvert.parse_2_byte(seed_vol_size)
                    elif mirror in [
                        'https://monikadesign.uk/',
                        'https://pt.hdpost.top/',
                        'https://reelflix.xyz/',
                        'https://pterclub.com/',
                        'https://hd-torrents.org/',
                        'https://hd-space.org/',
                        'https://filelist.io/',
                        'https://www.pttime.org/',
                        'https://www.pttime.top/',
                        'https://pt.keepfrds.com/',
                        'https://springsunday.net/',
                    ]:
                        # 无需解析字符串
                        seed_vol_size = ''.join(
                            seeding_html.xpath(self.site.my_seed_vol_rule)
                        ).replace('i', '').replace('&nbsp;', ' ').replace('\xa0', ' ')
                        logger.debug('做种信息字符串：{}'.format(seed_vol_size))
                        seed_vol_all = FileSizeConvert.parse_2_byte(seed_vol_size)
                        logger.debug(f'做种信息: {seed_vol_all}')
                    elif 'club.hares.top' in mirror:
                        logger.debug(f'白兔做种信息：{seeding_html}')
                        seed_vol_size = seeding_html.get('size')
                        logger.debug(f'白兔做种信息：{seed_vol_size}')
                        seed_vol_all = FileSizeConvert.parse_2_byte(seed_vol_size)
                        logger.debug(f'白兔做种信息：{seed_vol_all}')
                    else:
                        if len(seed_vol_list) > 0 and mirror not in [
                            'https://nextpt.net/',
                            'https://totheglory.im/',
                        ]:
                            seed_vol_list.pop(0)
                        logger.debug('做种数量seeding_vol：{}'.format(len(seed_vol_list)))
                        # 做种体积
                        seed_vol_all = 0
                        for seed_vol in seed_vol_list:
                            if 'iptorrents.com' in mirror:
                                vol = ''.join(seed_vol.xpath('.//text()'))
                                logger.debug(vol)
                                vol = ''.join(re.findall(r'\((.*?)\)', vol))
                                logger.debug(vol)
                            elif mirror in [
                                'https://exoticaz.to/',
                                'https://cinemaz.to/',
                                'https://avistaz.to/',
                            ]:
                                if ''.join(seed_vol) == '\n':
                                    continue
                                vol = ''.join(seed_vol).strip()
                            else:
                                vol = ''.join(seed_vol.xpath('.//text()'))
                            # logger.debug(vol)
                            if len(vol) > 0:
                                # U2返回字符串为mib，gib
                                size = FileSizeConvert.parse_2_byte(vol.replace('i', ''))
                                if size:
                                    seed_vol_all += size
                                else:
                                    msg = f'{self.site.name} 获取做种大小失败，请检查规则信息是否匹配？'
                                    logger.warning(msg)
                                    # toolbox.send_text(title=msg, message=msg)
                                    break
                            else:
                                # seed_vol_all = 0
                                pass
                    logger.debug('做种体积：{}'.format(FileSizeConvert.parse_2_file_size(seed_vol_all)))
                    today_state.update({
                        'seed_volume': seed_vol_all,
                        'updated_at': str(datetime.now())
                    })
                self.my_site.status[today] = today_state
                self.my_site.save()
                return CommonResponse.success(data=today_state)
            except Exception as e:
                logger.error(traceback.format_exc(3))
                return CommonResponse.error(msg=f'{self.site.name} 站点做种信息解析错误~')
