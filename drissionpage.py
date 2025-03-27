import os
from DrissionPage import Chromium
import xml.etree.ElementTree as ET

# 导入必要的模块
doc_dir_path = "data/"
doc_encoding = "utf-8"

def main(doc_id=12252):
    # 读取搜索词文件
    search_file = 'search_words.txt'
    if not os.path.exists(search_file):
        print("搜索词文件不存在，请创建文件并添加搜索词。")
        return

    with open(search_file, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file.readlines()]

    # 连接浏览器
    browser = Chromium()
    try:
        #遍历每行搜索词执行操作
        for idx, search_word in enumerate(lines):
            if not search_word:  # 跳过空行
                continue
            # 获取标签页对象
            tab = browser.latest_tab

            # 访问网页
            tab.get('https://www.bing.com')

            # 获取文本框元素对象
            ele = tab.ele('#sb_form_c')

            # 输入搜索词
            ele.input(search_word+"\n")

            # 点击搜索按钮
            # if search_word.strip() != '':
            #     tab.ele('@class=search icon tooltip').click()


            for k in range(0,10):
                browser.wait.new_tab()

                res = browser.latest_tab

                for i in range(0,10):
                    databm = i + 6
                    attr_value = f"@@class=b_algo@@data-bm={databm}"
                    if not res.ele(attr_value):
                        continue
                    temp = res.ele(attr_value)
                    print(temp)
                    publish_time = "no publish_time"
                    if temp.ele('@class:b_lineclamp'):
                        summary = temp.ele('@class:b_lineclamp').text
                        print(len(summary))
                        for l in range(0, int(len(summary) / 2)):
                            print(l)
                            if summary[l] == '·':
                                publish_time = summary[:l]
                                summary = summary[l + 2:]
                                print("summary:", summary)
                                print("publish_time:", publish_time)
                                break
                    else:
                        continue
                    title = temp.ele('@h:.2').text
                    print("title:", title)
                    source = temp.ele('@class=tptt').text
                    print("source:", source)
                    url = temp.ele('@target=_blank')
                    print("url:", url.attr('href'))
                    print("search_word:", search_word)
                    doc = ET.Element("doc")
                    ET.SubElement(doc, "search_word").text = search_word
                    ET.SubElement(doc, "title").text = title
                    ET.SubElement(doc, "publish_time").text = publish_time
                    ET.SubElement(doc, "summary").text = summary
                    ET.SubElement(doc, "source").text = source
                    ET.SubElement(doc, "url").text = url.attr('href')
                    tree = ET.ElementTree(doc)
                    tree.write(doc_dir_path + "%d.xml" % doc_id, encoding=doc_encoding, xml_declaration=True)
                    doc_id += 1
                if res.ele('@title=下一页'):
                    res('@title=下一页').click()
                else:
                    break

    except Exception as e:
        print(f"发生错误：{e}")

    # 关闭浏览器
    browser.quit()


if __name__ == "__main__":
    main()
