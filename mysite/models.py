from datetime import datetime

from django.db import models
from django.db.models import ManyToManyField, DateTimeField

from PtAide.base import BaseEntity


# Create your models here.

class MySite(BaseEntity):
    site = models.CharField(verbose_name='站点', max_length=16, unique=True)
    nickname = models.CharField(verbose_name='站点昵称', max_length=16, default=' ')
    sort_id = models.IntegerField(verbose_name='排序', default=1)
    mail = models.IntegerField(verbose_name='短消息', default=0)
    notice = models.IntegerField(verbose_name='公告', default=0)
    # 用户信息
    user_id = models.CharField(verbose_name='用户ID', max_length=16,
                               help_text='请填写<font color="orangered">数字UID</font>，'
                                         '<font color="orange">* az,cz,ez,莫妮卡、普斯特等请填写用户名</font>')
    passkey = models.CharField(max_length=128, verbose_name='PassKey', blank=True, null=True)
    cookie = models.TextField(verbose_name='COOKIE', help_text='与UA搭配使用效果更佳，请和UA在同一浏览器提取')
    user_agent = models.TextField(verbose_name='User-Agent', help_text='请填写你获取cookie的浏览器的User-Agent',
                                  default='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                                          '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0')
    rss = models.URLField(verbose_name='RSS地址', null=True, blank=True, help_text='RSS链接')
    torrents = models.CharField(verbose_name='种子地址', null=True, blank=True, help_text='免费种子链接',
                                max_length=512)
    # 用户设
    sign_in = models.BooleanField(verbose_name='开启签到', default=True, help_text='是否开启签到')
    get_info = models.BooleanField(verbose_name='抓取信息', default=True, help_text='是否抓取站点数据')
    repeat_torrents = models.BooleanField(verbose_name="辅种支持", default=False)
    brush_free = models.BooleanField(verbose_name="Free刷流", default=True)
    brush_rss = models.BooleanField(verbose_name="RSS刷流", default=False, help_text="硬刚刷流")
    package_file = models.BooleanField(verbose_name="拆包刷流", default=False,
                                       help_text="拆包刷流，只下载一部分，针对大包小硬盘")
    hr_discern = models.BooleanField(verbose_name='开启HR下载', default=False, help_text='是否下载HR种子')
    search_torrents = models.BooleanField(verbose_name='开启搜索', default=True, help_text='是否开启搜索')
    proxy = models.URLField(verbose_name='代理服务器', null=True, blank=True, help_text='部分站点需要')
    remove_torrent_rules = models.TextField(verbose_name='刷流删种', null=True, blank=True,
                                            help_text='详细内容请查看文档')
    mirror = models.URLField(verbose_name='CDN网址', null=True, blank=True)

    # 用户数据 自动拉取
    time_join = models.DateTimeField(verbose_name='注册时间',
                                     default=datetime(2024, 2, 1),
                                     help_text='请务必填写此项！')
    sign_info = models.JSONField(verbose_name='签到信息', null=True, blank=True, default=dict)
    status = models.JSONField(verbose_name='站点数据', null=True, blank=True, default=dict)

    def __str__(self):
        return self.nickname

    class Meta:
        verbose_name = '我的站点'
        verbose_name_plural = verbose_name

    @classmethod
    def has_today_sign(cls):
        today = datetime.now().date()
        return cls.objects.filter(sign_info__has_key=str(today)).exists()

    @classmethod
    def has_today_state(cls):
        today = datetime.now().date()
        return cls.objects.filter(status__has_key=str(today)).exists()


# 种子信息
class TorrentInfo(BaseEntity):
    site = models.ForeignKey(to=MySite, to_field='site', on_delete=models.CASCADE, verbose_name='所属站点', null=True)
    tid = models.IntegerField(verbose_name='种子ID')
    title = models.CharField(max_length=256, verbose_name='种子名称', default='')
    subtitle = models.CharField(max_length=256, verbose_name='标题', default='')
    category = models.CharField(max_length=128, verbose_name='分类', default='')
    magnet_url = models.URLField(verbose_name='下载链接', default='')
    tags = models.CharField(max_length=64, verbose_name='种子标签', default='')
    size = models.BigIntegerField(verbose_name='文件大小', default=0)
    hr = models.BooleanField(verbose_name='H&R考核', default=True, help_text='绿色为通过或无需HR考核')
    sale_status = models.CharField(verbose_name='优惠状态', default='', max_length=16)
    sale_expire = models.DateTimeField(verbose_name='到期时间', blank=True, null=True, )
    published = models.DateTimeField(verbose_name='发布时间', blank=True, null=True)
    seeders = models.IntegerField(verbose_name='做种人数', default=0, )
    leechers = models.IntegerField(verbose_name='下载人数', default=0, )
    completers = models.IntegerField(verbose_name='完成人数', default=0, )
    hash_string = models.CharField(max_length=128, verbose_name='Info_Hash', default='')
    filelist = models.CharField(max_length=128, verbose_name='文件列表', default='')
    douban_url = models.URLField(verbose_name='豆瓣链接', default='')
    imdb_url = models.URLField(verbose_name='imdb', default='')
    poster = models.URLField(verbose_name='海报', default='')
    files_count = models.IntegerField(verbose_name='文件数目', default=0)
    completed = models.IntegerField(verbose_name='已下载', default=0)
    uploaded = models.IntegerField(verbose_name='已上传', default=0)
    pieces_qb = models.CharField(verbose_name='pieces_qb', default='', max_length=128)
    pieces_tr = models.CharField(verbose_name='pieces_tr', default='', max_length=128)
    state = models.IntegerField(verbose_name='推送状态', default=0)
    pushed = models.BooleanField(verbose_name='推送至服务器', default=False, help_text='推送至辅种服务器')

    class Meta:
        verbose_name = '种子管理'
        verbose_name_plural = verbose_name
        unique_together = ('site', 'tid')
        abstract = True

    def __str__(self):
        return self.title

    def to_dict(self, fields=None, exclude=None):
        data = {}
        for f in self._meta.fields:
            value = f.value_from_object(self)

            if fields and f.name not in fields:
                continue

            if exclude and f.name in exclude:
                continue

            if isinstance(f, ManyToManyField):
                value = [i.id for i in value] if self.pk else None

            if isinstance(f, DateTimeField):
                value = value.strftime('%Y-%m-%d %H:%M:%S') if value else None

            if f.name == 'site':
                data['site_id'] = self.site_id
            else:
                data[f.name] = value

        return data
