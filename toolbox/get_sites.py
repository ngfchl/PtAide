import os

import toml

from PtAide.base import DotDict
from PtAide.settings import BASE_DIR


def get_site_file_choices():
    # 动态获取文件夹下所有Toml文件名
    folder_path = f'{BASE_DIR}/sites'  # 请替换为实际的文件夹路径
    toml_files = [file.replace('.toml', '') for file in os.listdir(folder_path) if file.endswith('.toml')]
    # choices = [(file, file) for file in toml_files]
    toml_files.sort()
    return toml_files


def get_site(site: str):
    """从配置文件解析获取相关项目"""
    try:
        file_path = f'{BASE_DIR}/sites/{site}.toml'
        data = toml.load(file_path)
        return DotDict(data)
    except Exception as e:
        return DotDict()


if __name__ == '__main__':
    x = get_site_file_choices()
    print(x)
