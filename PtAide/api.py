import logging
from http.client import HTTPException

from django.http import HttpResponse
from ninja import NinjaAPI
from ninja.errors import ValidationError
from ninja.security import HttpBearer

from configuration.views import router as config_router
# from download.views import router as download_router
# from monkey.views import router as monkey_router
from mysite.views import router as mysite_router

# from schedule.views import router as schedule_router
# from website.views import router as website_router

logger = logging.getLogger('ptools')


class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


api_v1 = NinjaAPI(version='1.0.0', auth=GlobalAuth())
# api_v1.add_router('/website', website_router)
api_v1.add_router('/mysite', mysite_router)

api_v1.add_router('/config', config_router)
# api_v1.add_router('/download', download_router)

# api_v1.add_router('/monkey', monkey_router)


# api_v1.add_router('/schedule', schedule_router)


@api_v1.exception_handler(ValidationError)
def validation_errors(request, exc):
    logger.error(request.body)
    return HttpResponse("Invalid input", status=422)


@api_v1.exception_handler(HTTPException)
async def http_exception_v1(request, exc: HTTPException):
    """
    # 改变成字符串响应
    :param request: 不可省略
    :param exc: HTTPException
    :return:
    """
    return HttpResponse(str(exc.detail), status_code=400)
