import json
from operator import itemgetter
import math
import jieba
import mysql.connector


class SearchEngine:
    def __init__(self, db_config):
        try:
            self.K1 = 1.5
            self.B = 0.75
            self.db_config = db_config
            self.conn = mysql.connector.connect(**db_config)  # 仅连接一次
            self.N = self._get_doc_count()
            self.AVG_L = self._get_avg_length()  # 已删除重复连接
        except Exception as e:
            print(f"初始化失败: {str(e)}")
            self.close()
            raise

    def _get_keywords_for_docs(self, doc_ids):
        """批量获取文档关键词 (优化版)"""
        if not doc_ids:
            return {}

        try:
            cursor = self.conn.cursor(dictionary=True)
            # 生成动态占位符
            placeholders = ', '.join(['%s'] * len(doc_ids))
            query = f"""
                SELECT docid, GROUP_CONCAT(term ORDER BY tf DESC) AS keywords 
                FROM doc_terms 
                WHERE docid IN ({placeholders})
                GROUP BY docid
            """
            cursor.execute(query, doc_ids)
            return {row['docid']: row['keywords'].split(',') for row in cursor}
        except mysql.connector.Error as err:
            print(f"关键词查询失败: {err.msg}")
            return {}
        finally:
            cursor.close()

    def _get_doc_count(self):
        """获取文档总数"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM postings")
        return cursor.fetchone()[0]

    def _get_avg_length(self):
        """增强健壮性的平均长度获取"""
        cursor = self.conn.cursor()
        try:
            # 先检查表是否存在
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'global_stats'
            """)
            if cursor.fetchone()[0] == 0:
                print("警告: global_stats 表不存在，使用默认值 100")
                return 100.0  # 默认平均长度

            # 再获取数据
            cursor.execute("SELECT avg_l FROM global_stats ORDER BY update_time DESC LIMIT 1")
            result = cursor.fetchone()

            if result is None:
                return 100.0

            return float(result[0])
        except mysql.connector.Error as err:
            print(f"数据库错误: {err.msg}")
            return 100.0  # 安全默认值
        finally:
            cursor.close()

    def _fetch_postings(self, term):
        """从MySQL获取倒排列表"""
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT df, docs FROM postings WHERE term = %s"
        cursor.execute(query, (term,))
        result = cursor.fetchone()
        cursor.close()
        return result

    def _parse_doc_entry(self, doc_str):
        """解析文档条目字符串为结构化数据"""
        try:
            parts = doc_str.split('\t')
            return {
                'docid': int(parts[0]),
                'publish_time': parts[1],
                'tf': int(parts[2]),
                'ld': int(parts[3])
            }
        except (IndexError, ValueError) as e:
            print(f"文档条目解析失败: {doc_str} - {str(e)}")
            return None

    def _calculate_bm25(self, df, tf, ld):
        """计算BM25得分"""
        idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
        numerator = self.K1 * tf
        denominator = tf + self.K1 * (1 - self.B + self.B * (ld / self.AVG_L))
        return idf * (numerator / denominator)

    def search(self, query):
        """执行搜索查询"""
        # 分词处理
        seg_list = jieba.lcut(query, cut_all=False)
        valid_terms = [term for term in seg_list if len(term) > 1]

        scores = {}
        for term in valid_terms:
            # 获取倒排列表
            postings = self._fetch_postings(term)
            if not postings:
                continue

            df = postings['df']
            docs = postings['docs'].split('\n')

            # 计算每个文档的得分
            for doc_entry in docs:
                doc_data = self._parse_doc_entry(doc_entry)
                if not doc_data:
                    continue

                score = self._calculate_bm25(df, doc_data['tf'], doc_data['ld'])
                doc_id = doc_data['docid']

                # 累加得分
                if doc_id in scores:
                    scores[doc_id] += score
                else:
                    scores[doc_id] = score

            # 获取前30个结果的doc_ids
            sorted_results = sorted(scores.items(), key=itemgetter(1), reverse=True)[:30]
            doc_ids = [doc_id for doc_id, _ in sorted_results]

            # 批量获取关键词
            keywords_map = self._get_keywords_for_docs(doc_ids)

            # 重组结果结构
            return [
                {
                    "docid": doc_id,
                    "score": score,
                    "keywords": keywords_map.get(doc_id, [])
                }
                for doc_id, score in sorted_results
            ]

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


# 使用示例
if __name__ == "__main__":
    # 数据库配置（与索引器保持一致）
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'w-4_44144',
        'database': 'vsearch'
    }

    se = SearchEngine(db_config)
    results = se.search("联想")
    print(results)

    se.close()
