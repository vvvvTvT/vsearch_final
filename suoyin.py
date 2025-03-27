# -*- coding: utf-8 -*-
"""
MySQL版本索引构建脚本
功能：
1. 从XML文件（命名如1.xml、2.xml）的title和summary构建倒排索引
2. 使用MySQL作为存储后端
3. 硬编码配置参数
"""
import datetime
import os
import xml.etree.ElementTree as ET
import jieba
import mysql.connector
from mysql.connector import errorcode
import re



class Doc:
    def __init__(self, docid, publish_time, tf, ld):
        self.docid = docid
        self.publish_time = publish_time
        self.tf = tf  # 词频
        self.ld = ld  # 文档长度

    def __repr__(self):
        return f"{self.docid}\t{self.publish_time}\t{self.tf}\t{self.ld}"


class MySQLIndexer:
    def __init__(self):
        # 硬编码配置参数
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'w-4_44144',
            'database': 'vsearch'
        }

        self.stop_words = self.load_stopwords('stop_words.txt')  # 停用词文件路径
        self.doc_dir = './data/'  # XML文档目录
        self.postings = {}  # 倒排索引临时存储
        self.doc_terms = {}  # 新增：正向索引 {docid: {term: tf}}
        # 初始化数据库
        self.init_db()

    def parse_publish_time(self, raw_time_str):
        """将非标准日期字符串转换为标准格式（YYYY-MM-DD）"""
        raw_str = str(raw_time_str).strip()

        # 空值处理
        if not raw_str or raw_str.lower() == "no publish_time":
            return "1970-01-01"  # 默认日期

        # 格式1：x年x月x日（支持中文数字）
        if match := re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', raw_str):
            year, month, day = match.groups()
            return self._format_date(year, month, day)

        # 格式2：x天之前（支持中文单位）
        if match := re.search(r'(\d+)\s*天之前', raw_str):
            days_ago = int(match.group(1))
            return self._days_ago(days_ago)

        # 其他格式尝试自动解析
        return self._try_parse_unknown(raw_str) or "1970-01-01"

    def _format_date(self, year, month, day):
        """标准化日期组件"""
        try:
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        except ValueError:
            return "1970-01-01"

    def _days_ago(self, days):
        """计算n天前的日期"""
        try:
            target_date = datetime.datetime.now() - datetime.timedelta(days=days)
            return target_date.strftime("%Y-%m-%d")
        except OverflowError:  # 处理极大天数
            return "1970-01-01"

    def _try_parse_unknown(self, date_str):
        """尝试解析其他日期格式"""
        formats = [
            "%Y-%m-%d",  # 标准格式
            "%Y/%m/%d",  # 带斜杠
            "%Y.%m.%d",  # 带点号
            "%Y年%m月%d日",  # 中文全格式
            "%m月%d日%Y年",  # 中文变体格式
        ]

        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
        return None

    def load_stopwords(self, path):
        """加载停用词表"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return set(f.read().splitlines())
        except FileNotFoundError:
            print(f"警告：未找到停用词文件 {path}")
            return set()

    def init_db(self):
        """初始化数据库连接和表结构"""
        try:
            self.conn = mysql.connector.connect(**self.db_config)
            self.cursor = self.conn.cursor()

            # 创建表
            tables = {
                'postings': (
                    "CREATE TABLE IF NOT EXISTS postings ("
                    "  term VARCHAR(50) PRIMARY KEY,"
                    "  df INT NOT NULL,"  # 文档频率
                    "  docs TEXT NOT NULL"  # 存储序列化的Doc对象
                    ") CHARACTER SET utf8mb4"
                )
            }

            for table_name, ddl in tables.items():
                try:
                    self.cursor.execute(ddl)
                except mysql.connector.Error as err:
                    print(f"创建表失败 {table_name}: {err.msg}")

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("数据库认证失败")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("数据库不存在")
            else:
                print(f"数据库连接失败: {err.msg}")
            exit(1)

    def extract_docid(self, filename):
        """从文件名提取数字ID"""
        try:
            return int(os.path.splitext(filename)[0])
        except ValueError:
            raise ValueError(f"无效文件名格式: {filename}，应为数字ID.xml")

    def process_xml(self, filename):
        """处理单个XML文件"""
        try:
            docid = self.extract_docid(filename)
            tree = ET.parse(os.path.join(self.doc_dir, filename))
            root = tree.getroot()
            # 新增：提取元数据
            title = root.findtext('title', default='无标题').strip()
            summary = root.findtext('summary', default='').strip()
            source = root.findtext('source', default='未知来源').strip()
            raw_time = root.findtext('publish_time', default='')
            url = root.findtext('url', default='#')
            publish_time = self.parse_publish_time(raw_time)

            # 新增：存储元数据到数据库
            self.save_document_meta(docid, title, summary, publish_time, source, url)
            if not self._is_valid_date(publish_time):
                print(f"警告：{filename} 含无效日期 {publish_time}，已重置为默认")
                publish_time = "1970-01-01"
            # 合并内容并分词
            content = f"{title} {summary}"
            words = jieba.lcut(content)

            # 统计词频
            word_counts = {}
            self.doc_terms[docid] = {
                'terms': word_counts,
                'publish_time': publish_time
            }
            doc_length = 0
            for word in words:
                word = word.strip().lower()
                if self.is_valid_word(word):
                    doc_length += 1
                    word_counts[word] = word_counts.get(word, 0) + 1

            # 构建文档对象
            doc = Doc(docid, publish_time, 0, doc_length)  # tf在后续处理

            # 更新倒排索引
            for word, tf in word_counts.items():
                doc.tf = tf
                if word in self.postings:
                    self.postings[word][0] += 1  # 更新df
                    self.postings[word][1].append(doc)
                else:
                    self.postings[word] = [1, [doc]]  # [df, [Doc]]


        except ET.ParseError as pe:

            print(f"XML解析失败 {filename}: {str(pe)}")

        except ValueError as ve:

            print(f"文件ID错误 {filename}: {str(ve)}")

        except Exception as e:

            print(f"处理文件 {filename} 发生未知错误: {str(e)}")

    def save_document_meta(self, docid, title, summary, publish_time, source, url):
        """保存文档元数据到 documents 表"""
        sql = """
            INSERT INTO documents 
            (docid, title, summary, publish_time, source, url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title=VALUES(title),
            summary=VALUES(summary),
            publish_time=VALUES(publish_time),
            source=VALUES(source),
            url=VALUES(url)
        """
        try:
            self.cursor.execute(sql, (
                docid,
                title[:255],  # 防止超长
                summary,
                publish_time,
                source[:100],
                url[:100]
            ))
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"文档元数据存储失败 ID={docid}: {err.msg}")
            self.conn.rollback()
    def _is_valid_date(self, date_str):
        """验证日期是否合法"""
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    def is_valid_word(self, word):
        """过滤有效词语"""
        return (
                len(word) > 1 and
                word not in self.stop_words and
                not word.isdigit() and
                not word.isspace()
        )

    def save_to_mysql(self):
        """将倒排索引保存到MySQL"""
        try:
            delete_sql = "TRUNCATE TABLE postings"
            self.cursor.execute(delete_sql)

            insert_sql = (
                "INSERT INTO postings (term, df, docs) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE df=VALUES(df), docs=VALUES(docs)"
            )

            for term, (df, docs) in self.postings.items():
                # 序列化Doc对象列表
                docs_str = '\n'.join([repr(doc) for doc in docs])
                self.cursor.execute(insert_sql, (term, df, docs_str))

            self.conn.commit()
            print(f"成功写入 {len(self.postings)} 条倒排记录")

        except mysql.connector.Error as err:
            print(f"数据库写入失败: {err.msg}")
            self.conn.rollback()

    def save_doc_terms(self):
        """保存文档-词项关系到数据库"""
        try:
            delete_sql = "TRUNCATE TABLE doc_terms"
            self.cursor.execute(delete_sql)

            insert_sql = (
                "INSERT INTO doc_terms (docid, term, tf, publish_date) "
                "VALUES (%s, %s, %s, %s)"
            )

            batch_data = []
            for docid, data in self.doc_terms.items():
                publish_date = data['publish_time']
                for term, tf in data['terms'].items():
                    batch_data.append((docid, term, tf, publish_date))

                    # 批量插入（每1000条提交一次）
                    if len(batch_data) >= 1000:
                        self.cursor.executemany(insert_sql, batch_data)
                        batch_data = []

            # 插入剩余数据
            if batch_data:
                self.cursor.executemany(insert_sql, batch_data)

            self.conn.commit()
            print(f"写入 {len(self.doc_terms)} 篇文档的词项数据")

        except mysql.connector.Error as err:
            print(f"文档词项写入失败: {err.msg}")
            self.conn.rollback()

    def run(self):
        """主执行流程"""
        try:
            # 遍历文档目录
            for filename in os.listdir(self.doc_dir):
                if filename.endswith('.xml'):
                    self.process_xml(filename)

            # 保存到数据库
            self.save_to_mysql()
            self.save_doc_terms()
        finally:
            self.cursor.close()
            self.conn.close()


if __name__ == "__main__":
    indexer = MySQLIndexer()
    indexer.run()
