import ipaddress
import logging
import re
import traceback

import aip
import toml

from PtAide.base import DotDict
from toolbox.schema import CommonResponse

logger = logging.getLogger('ptools')


def is_valid_ip_address(ip_str):
    """
    判断字符串是否为ip地址
    :param ip_str:
    :return:
    """
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ipaddress.AddressValueError:
        pass

    try:
        ipaddress.IPv6Address(ip_str)
        return True
    except ipaddress.AddressValueError:
        pass

    return False


def extract_storage_size(input_string):
    """
    从字符串正则解析文件大小
    :param input_string:
    :return: ‘’MB，GB，TB，PB
    """
    # 定义正则表达式
    pattern = re.compile(r'(\d+(\.\d+)?)\s+(B|KB|MB|GB|TB|PB)')

    # 使用正则表达式进行匹配
    match = pattern.search(input_string)

    # 提取匹配的结果
    if match:
        value = float(match.group(1))
        unit = match.group(3)
        return f"{value} {unit}"
    else:
        return "0"


def get_decimals(x):
    match = re.search(r"\d+(\.\d+)?", x)
    return match.group() if match else '0'


def parse_toml(cmd) -> dict:
    """从配置文件解析获取相关项目"""
    try:
        data = toml.load(f'db/{cmd}.toml')
        return data.get(cmd, {})
    except Exception as e:
        return dict()


def baidu_ocr_captcha(img_url):
    """百度OCR高精度识别，传入图片URL"""
    # 获取百度识别结果
    ocr = parse_toml("ocr")
    # ocr = BaiduOCR.objects.filter(enable=True).first()
    if not ocr:
        logger.error('未设置百度OCR文本识别API，无法使用本功能！')
        return CommonResponse.error(msg='未设置百度OCR文本识别API，无法使用本功能！')
    try:
        ocr = DotDict(ocr)
        ocr_client = aip.AipOcr(appId=ocr.app_id, secretKey=ocr.secret_key, apiKey=ocr.api_key)
        res1 = ocr_client.basicGeneralUrl(img_url)
        logger.info(res1)
        if res1.get('error_code'):
            res1 = ocr_client.basicAccurateUrl(img_url)
        logger.info('res1: {}'.format(res1))
        if res1.get('error_code'):
            return CommonResponse.error(msg=res1.get('error_msg'))
        res2 = res1.get('words_result')[0].get('words')
        # 去除杂乱字符
        imagestring = ''.join(re.findall('[A-Za-z0-9]+', res2)).strip()
        logger_info = '百度OCR天空验证码：{}，长度：{}'.format(imagestring, len(imagestring))
        logger.info(logger_info)
        # 识别错误就重来

        return CommonResponse.success(data=imagestring)
    except Exception as e:
        msg = '百度OCR识别失败：{}'.format(e)
        logger.info(traceback.format_exc(limit=3))
        # raise
        # self.send_text(title='OCR识别出错咯', message=msg)
        return CommonResponse.error(msg=msg)
