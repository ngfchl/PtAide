from typing import Optional, List, Union

from ninja import ModelSchema, Schema

from mysite.models import *


class MySiteSchemaOut(ModelSchema):
    class Meta:
        model = MySite
        exclude = [
            'created_at',
            'passkey',
            'cookie',
            'user_agent'
        ]


class MySiteDoSchemaIn(Schema):
    site_id: int
    sort_id: Optional[int]


class MySiteSchemaIn(Schema):
    id: Optional[int]
    sort_id: int
    site: str
    mirror: Optional[str]
    mirror_switch: bool
    nickname: Optional[str]
    passkey: Optional[str]
    get_info: bool
    sign_in: bool
    brush_rss: bool
    brush_free: bool
    package_file: bool
    repeat_torrents: bool
    hr_discern: bool
    search_torrents: bool
    user_id: Union[str, int]
    user_agent: str
    cookie: str
    rss: Optional[str]
    torrents: Optional[str]
    custom_server: Optional[str]
    remove_torrent_rules: Optional[str]


class MySiteSchemaEdit(ModelSchema):
    # site: create_schema(WebSite, fields=['id', 'name'])
    # downloader_id: Optional[int]

    # id: Optional[int]
    # sort_id: int
    # site: int
    # nickname: Optional[str]
    # passkey: Optional[str]
    # get_info: bool
    # sign_in: bool
    # brush_rss: bool
    # brush_free: bool
    # package_file: bool
    # repeat_torrents: bool
    # hr_discern: bool
    # search_torrents: bool
    # user_id: str
    # joined: str
    # user_agent: str
    # cookie: str
    # rss: Optional[str]
    # torrents: Optional[str]
    # custom_server: Optional[str]
    # remove_torrent_rules: Optional[str]

    # def resolve_downloader_id(self, obj):
    #     if not obj.downloader_id:
    #         if self.downloader:
    #             return self.downloader.id
    #         else:
    #             return None

    class Config:
        model = MySite
        model_exclude = ['created_at', 'updated_at']


class MySiteSortSchemaIn(ModelSchema):
    # site: create_schema(WebSite, fields=['id', 'name'])
    updated: str

    class Config:
        model = MySite
        model_exclude = ['id', 'sort_id']

    def resolve_updated(self, obj):
        return datetime.strftime(self.updated_at, '%Y年%m月%d日%H:%M:%S')


class TorrentInfoSchemaOut(ModelSchema):
    class Config:
        model = TorrentInfo
        model_exclude = ['created_at', 'updated_at']


class PaginateQueryParamsSchemaIn(Schema):
    site_id: Optional[int]
    page: int
    limit: int


class ImportSchema(Schema):
    info: str
    cookies: str
    # userdata: str


class SearchTorrentSchema(Schema):
    site: int
    tid: int
    category: str
    magnet_url: str
    detail_url: str
    poster_url: str
    title: str
    subtitle: Optional[str]
    sale_status: Optional[str]
    sale_expire: Optional[str]
    hr: bool
    published: str
    size: int
    seeders: int
    leechers: int
    completers: int


class SearchResultSchema(Schema):
    results: List[SearchTorrentSchema]
    warning: List[str]
    error: List[str]


class SearchParamsSchema(Schema):
    key: str
    site_list: List[int] = []



# class SiteDataToChart(Schema):
#     status_list: List[SiteStatusSchemaOut]
#     date_list: List[datetime]
