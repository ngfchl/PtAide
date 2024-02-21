import re


class FileSizeConvert:
    """文件大小和字节数互转"""

    @staticmethod
    def parse_2_byte(file_size: str) -> int:
        if not file_size:
            return 0
        """将文件大小字符串解析为字节"""
        regex = re.compile(r'(\d+(?:\.\d+)?)\s*([kmgtp]?b)', re.IGNORECASE)

        order = ['b', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb']

        for value, unit in regex.findall(file_size):
            return int(float(value) * (1024 ** order.index(unit.lower())))

    @staticmethod
    def parse_2_file_size(byte: int) -> str:
        if not byte:
            return '0B'
        units = ["B", "KB", "MB", "GB", "TB", "PB", 'EB']
        size = 1024.0
        for i in range(len(units)):
            if (byte / size) < 1:
                return "%.3f %s" % (byte, units[i])
            byte = byte / size
