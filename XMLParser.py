from datetime import datetime
import re
import xml.etree.ElementTree as ET
class XMLParser:
    @staticmethod
    def parse(xml_path):
        """增强型XML解析方法"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            return {
                "title": XMLParser._get_text(root, 'title', '无标题'),
                "snippet": XMLParser._get_text(root, 'summary', '无摘要'),
                "source": XMLParser._get_text(root, 'source', '未知来源'),
                "date": XMLParser._format_date(root.findtext('publish_time')),
                "url": XMLParser._validate_url(root.findtext('url'))
            }
        except ET.ParseError as e:
            print(f"XML解析失败：{xml_path} - {str(e)}")
            return None

    @staticmethod
    def _validate_url(raw_url):
        """专用URL校验方法"""
        if not raw_url:
            return "javascript:void(0);"

        # 清理URL中的特殊字符和空格
        clean_url = raw_url.strip().replace('\n', '').replace('\t', '')

        # 校验协议头
        if not clean_url.startswith(('http://', 'https://')):
            return "javascript:void(0);"

        return clean_url  # 返回原始URL
    @staticmethod
    def _get_text(node, tag, default):
        """安全获取文本内容"""
        elem = node.find(tag)
        return elem.text.strip() if elem is not None and elem.text else default

    @staticmethod
    def _format_date(raw_date):
        """处理多格式日期"""
        # 清理特殊空格和字符
        clean_date = re.sub(r'\s+', '', raw_date).replace(' ', '').replace(' ', '')

        # 支持多种日期格式
        formats = [
            "%Y年%m月%d日",  # 2022年11月09日
            "%Y-%m-%d",  # 2022-11-09
            "%Y/%m/%d",  # 2022/11/09
            "%m月%d日"  # 11月09日（自动补全年份）
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(clean_date, fmt)
                # 处理缺少年份的情况
                if fmt == "%m月%d日":
                    dt = dt.replace(year=datetime.now().year)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return '日期格式异常'

    @classmethod
    def validate_structure(cls, xml_path):
        """XML结构校验方法"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 必需字段检查
            required_fields = ['title', 'publish_time', 'url']
            missing = [field for field in required_fields if root.find(field) is None]
            if missing:
                return False, f"缺少必需字段: {', '.join(missing)}"

            # 字段内容非空检查
            content_fields = ['title', 'url']
            for field in content_fields:
                if not root.findtext(field, '').strip():
                    return False, f"字段内容为空: {field}"

            return True, "校验通过"

        except ET.ParseError as e:
            return False, f"XML解析失败: {str(e)}"
        except Exception as e:
            return False, f"未知错误: {str(e)}"