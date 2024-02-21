import json
import logging
import traceback
from typing import List, Optional

import demjson3
from django.db import IntegrityError
from ninja import Router

from mysite.models import MySite
from mysite.schema import MySiteSchemaOut, MySiteSchemaEdit, MySiteSchemaIn
from toolbox.get_sites import get_site_file_choices
from toolbox.schema import CommonResponse

# Create your views here.
router = Router(tags=['mysite'])
logger = logging.getLogger('ptools')


@router.get('/website', response=CommonResponse[List[str]], description="获取支持的站点列表")
def get_website_list(request):
    website_list = get_site_file_choices()
    return CommonResponse.success(data=website_list)


@router.get('/website/new', response=CommonResponse[List[str]], description="获取未添加的站点列表")
def get_website_new_list(request):
    id_list = MySite.objects.values_list('site', flat=True)
    website_list = get_site_file_choices()
    website_list = list(set(website_list) - set(id_list))
    website_list.sort()
    return CommonResponse.success(data=list(website_list))


@router.get('/mysite', response=CommonResponse[List[MySiteSchemaOut]], description='我的站点-列表')
def get_mysite_list(request):
    return CommonResponse.success(data=list(MySite.objects.order_by('time_join')))


@router.get('/mysite/{mysite_id}', response=CommonResponse[Optional[MySiteSchemaEdit]], description='我的站点-单个')
def get_mysite(request, mysite_id: int):
    try:
        my_site = MySite.objects.get(id=mysite_id)
        return CommonResponse.success(data=my_site)
    except Exception as e:
        print(e)
        return CommonResponse.error(msg='没有这个站点的信息哦')


@router.post('/mysite', response=CommonResponse, description='我的站点-添加')
def add_mysite(request, my_site_params: MySiteSchemaIn):
    try:
        website_list = get_site_file_choices()
        if my_site_params.site not in website_list:
            return CommonResponse.error(msg=f'{my_site_params.nickname} 保存失败，请检查站点信息！')
        logger.info(f'开始处理：{my_site_params.nickname}')
        my_site_params.id = None
        params = my_site_params.dict()
        if my_site_params.nickname is not None:
            params.update({
                "nickname": my_site_params.site
            })
        params.update({
            "remove_torrent_rules": json.dumps(demjson3.decode(my_site_params.remove_torrent_rules),
                                               indent=2) if my_site_params.remove_torrent_rules else '{}'
        })
        logger.info(params)
        my_site = MySite.objects.create(**params)
        if my_site:
            msg = f'处理完毕：{my_site.nickname}，保存成功！'
            logger.info(msg)
            return CommonResponse.success(msg=msg)
        return CommonResponse.error(msg=f'处理完毕：{my_site.nickname}，保存失败！')
    except IntegrityError as e:
        msg = f'{my_site_params.nickname} 站点信息已存在，请勿重复添加~！'
        return CommonResponse.error(msg=msg)
    except Exception as e:
        logger.info(traceback.format_exc(3))
        msg = f'{my_site_params.nickname} 参数有误，请确认后重试！{e}'
        return CommonResponse.error(msg=msg)


@router.put('/mysite/{mysite_id}', response=CommonResponse, description='我的站点-更新')
def edit_mysite(request, mysite_id: int, my_site_params: MySiteSchemaIn):
    try:
        logger.info(f'开始更新：{my_site_params.nickname}')
        print(my_site_params)
        params = my_site_params.dict()
        params.update({
            "remove_torrent_rules": json.dumps(demjson3.decode(my_site_params.remove_torrent_rules),
                                               indent=2) if my_site_params.remove_torrent_rules else '{}'
        })
        logger.info(params)
        my_site_res = MySite.objects.filter(id=mysite_id).update(**my_site_params.dict())
        if my_site_res > 0:
            logger.info(f'处理完毕：{my_site_params.nickname}，成功处理 {my_site_res} 条数据！')
            return CommonResponse.success(
                msg=f'{my_site_params.nickname} 信息更新成功！'
            )
        return CommonResponse.error(
            msg=f'{my_site_params.nickname} 信息更新失败！'
        )
    except Exception as e:
        logger.info(traceback.format_exc(3))
        msg = f'{my_site_params.nickname} 参数有误，请确认后重试！{e}'
        logger.info(msg)
        return CommonResponse.error(msg=msg)


@router.delete('/mysite/{mysite_id}', response=CommonResponse, description='我的站点-删除')
def remove_mysite(request, mysite_id: int):
    try:
        logger.info(f'开始删除站点：{mysite_id}')
        my_site_res = MySite.objects.get(id=mysite_id).delete()
        logger.info(my_site_res)
        if my_site_res[0] > 0:
            my_site = my_site_res[1]
            logger.info(f'删除成功：，成功删除 {my_site_res[0]} 条数据！')
            return CommonResponse.success(
                msg=f'站点删除成功！'
            )
        return CommonResponse.error(
            msg=f'站点删除失败！'
        )
    except Exception as e:
        logger.info(traceback.format_exc(30))
        msg = f'站点删除失败！{e}'
        logger.info(msg)
        return CommonResponse.error(msg=msg)
