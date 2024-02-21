import cloudscraper
import requests


class Spider:
    """爬虫"""

    def __init__(self,
                 user_agent: str,
                 cookie: str = None,
                 proxy: str = None,
                 *args, **kwargs):
        session = requests.Session()
        session.headers['User-Agent'] = user_agent
        if cookie is not None:
            session.cookies = self.cookie2dict(cookie)
        if proxy is not None:
            session.proxies = {'http': proxy, 'https': proxy, }
        browser = {
            'browser': 'chrome',
            'platform': 'darwin',
            'mobile': False
        }
        self.scraper = cloudscraper.create_scraper(sess=session, browser=browser, delay=15)

    @staticmethod
    def cookie2dict(source_str: str) -> dict:
        """
        cookies字符串转为字典格式,传入参数必须为cookies字符串
        """
        if len(source_str) <= 0:
            return {}
        return {cookie.split('=')[0].strip(): cookie.split('=')[1].strip() for cookie in source_str.split(';') if
                cookie.strip()}

    def send_request(self,
                     url: str,
                     method: str = 'get',
                     data: dict = None,
                     params: dict = None,
                     json: dict = None,
                     headers: dict = None,
                     timeout: int = 75,
                     ):
        headers = headers or {}
        return self.scraper.request(
            url=url,
            method=method,
            data=data,
            timeout=timeout,
            params=params,
            json=json,
            headers=headers
        )


if __name__ == '__main__':
    url = 'https://www.baidu.com'
    spider = Spider(user_agent='')
    res = spider.send_request(url)
    print(res.content.decode())
