# check_xmls.py
import os
from XMLParser import XMLParser


def validate_all_xmls(xml_dir):
    error_count = 0
    for filename in os.listdir(xml_dir):
        if filename.endswith('.xml'):
            xml_path = os.path.join(xml_dir, filename)
            valid, msg = XMLParser.validate(xml_path)
            status = "✅ 通过" if valid else f"❌ 失败 ({msg})"
            print(f"{filename.ljust(20)} {status}")
            if not valid:
                error_count += 1

    print(f"\n校验完成，发现 {error_count} 个异常文件")


if __name__ == "__main__":
    validate_all_xmls("./data")  # 修改为你的XML目录路径