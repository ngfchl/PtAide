from django.db import models


class BaseEntity(models.Model):
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name='更新时间', auto_now=True)

    class Meta:
        abstract = True


class DownloaderCategory(models.TextChoices):
    # 下载器名称
    # Deluge = 'De', 'Deluge'
    Transmission = 'Tr', 'Transmission'
    qBittorrent = 'Qb', 'qBittorrent'


class TorrentBaseInfo:
    category_list = {
        0: "空类型",
        1: "电影Movies",
        2: "电视剧TV Series",
        3: "综艺TV Shows",
        4: "纪录片Documentaries",
        5: "动漫Animations",
        6: "音乐视频Music Videos",
        7: "体育Sports",
        8: "音乐Music",
        9: "电子书Ebook",
        10: "软件Software",
        11: "游戏Game",
        12: "资料Education",
        13: "旅游Travel",
        14: "美食Food",
        15: "其他Misc",
    }
    sale_list = {
        1: '无优惠',
        2: 'Free',
        3: '2X',
        4: '2XFree',
        5: '50%',
        6: '2X50%',
        7: '30%',
        8: '6xFree'
    }

    download_state = {
        'allocating': '分配',
        'checkingDL': '校验中',
        'checkingResumeData': '校验恢复数据',
        'checkingUP': '',
        'downloading': '下载中',
        'error': '错误',
        'forcedDL': '强制下载',
        'forcedMetaDL': '强制下载元数据',
        'forcedUP': '强制上传',
        'metaDL': '下载元数据',
        'missingFiles': '文件丢失',
        'moving': '移动中',
        'pausedDL': '暂停下载',
        'pausedUP': '完成',
        'queuedDL': '下载队列中',
        'queuedUP': '下载队列中',
        'stalledDL': '等待下载',
        'stalledUP': '做种',
        'unknown': '未知',
        'uploading': '上传中',
    }


class Trigger(models.TextChoices):
    # date = 'date', '单次任务'
    interval = 'interval', '间隔任务'
    cron = 'cron', 'cron任务'


class MessageTemplate:
    """消息模板"""
    status_message_template = "{} 等级：{} 魔力：{} 时魔：{} 积分：{} 分享率：{} " \
                              "做种量：{} 上传量：{} 下载量：{} 上传数：{} 下载数：{} " \
                              "邀请：{} H&R：{}\n"


class DotDict(dict):
    """实现支持 "." 表示法的字典类"""

    def __getattr__(self, attr):
        try:
            return self[attr]
        except Exception:
            return None

    def __setattr__(self, attr, value):
        self[attr] = value

