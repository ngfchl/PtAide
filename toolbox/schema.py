from typing import Generic, TypeVar, List, Optional, Any

from ninja import Schema
from ninja.pagination import PaginationBase

# class BaseResponse(Schema):

T = TypeVar('T')


class CommonResponse(Schema, Generic[T]):
    code: int
    msg: Optional[str]
    data: Optional[T] = None

    """
    统一的json返回格式
    """

    def __init__(self, code: int = 0, data: object = None, msg: str = ''):
        super().__init__(code=code, data=data, msg=msg)
        # self.data = data
        # self.code = code.3333
        # if msg is None:
        #     self.msg = ''
        # else:
        #     self.msg = msg

    @classmethod
    def success(cls, code=0, data=None, msg=''):
        return cls(code, data, msg)

    @classmethod
    def error(cls, code=-1, data=None, msg=''):
        return cls(code, data, msg)

    def to_dict(self):
        return {
            "code": self.code,
            "msg": self.msg,
            "data": self.data
        }


class CustomPagination(PaginationBase):
    # only `skip` param, defaults to 5 per page
    class Input(Schema):
        skip: int

    class Output(Schema):
        items: List[Any]  # `items` is a default attribute
        total: int
        per_page: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        skip = pagination.skip
        return {
            'items': queryset[skip: skip + 5],
            'total': queryset.count(),
            'per_page': 5,
        }


class CommonPaginateSchema(Schema, Generic[T]):
    per_page: int
    total: int
    items: List[T]


class DotDict(dict):
    """实现支持 "." 表示法的字典类"""

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value
