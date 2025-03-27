# server.py
from collections import defaultdict

import mysql.connector
from mysql.connector import pooling
from flask import Flask, jsonify, request,render_template
from werkzeug.security import safe_join
from flask_cors import CORS
from bm25 import SearchEngine
import os
from XMLParser import XMLParser
from suoyin import MySQLIndexer
from markupsafe import escape
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'w-4_44144',
    'database': 'vsearch',
    'consume_results': True,  # 自动消费未读结果
    'buffered': True          # 缓存结果集
}
connection_pool = pooling.MySQLConnectionPool(
    pool_name="search_pool",
    pool_size=5,
    host='localhost',
    user='root',
    password='w-4_44144',
    database='vsearch',
    auth_plugin='caching_sha2_password'
)
def get_connection_from_pool():
    """从连接池获取连接"""
    return connection_pool.get_connection()

app = Flask(__name__,static_folder='static', static_url_path='/static',template_folder='templates')
CORS(app)  # 解决跨域问题
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 配置项
CONFIG = {
    "xml_dir": "./data",  # XML文档存储目录
    "bm25_script": "bm25.py"  # BM25算法脚本路径
}

def sanitize_json(raw):
    """替换全角符号为半角"""
    replacements = {
        '，': ',',  '；': ';',
        '：': ':',  '‘': "'",
        '“': '"',   '”': '"',
        '\ufeff': ''  # 移除BOM头
    }
    for k, v in replacements.items():
        raw = raw.replace(k, v)
    return raw


def get_doc_metadata(doc_id):
    """从XML文件获取文档元数据"""
    xml_path = safe_join(CONFIG["xml_dir"], f"{doc_id}.xml")
    if not os.path.exists(xml_path):
        return None
    return XMLParser.parse(xml_path)

@app.route('/')
def serve_home():
    """返回前端主页面"""
    return render_template('index.html')

@app.route('/index')
def serve_index():
    """返回前端主页面"""
    return render_template('index.html')

# server.py 添加以下路由
@app.route('/search')
def serve_results():
    """带参数的搜索结果页"""
    query = escape(request.args.get('query', ''))

    # 获取搜索结果
    try:
        se = SearchEngine(db_config)
        raw_scores = se.search(query)
        doc_ids = [item['docid'] for item in raw_scores] if raw_scores else []
    finally:
        se.close()
    if not doc_ids:
        return render_template('res.html', query=query, results=[])
    with get_connection_from_pool() as conn:  # 替换为实际的连接池获取方式
        meta_map = {}
        keywords_map = defaultdict(list)

        try:
            # 元数据查询（带参数校验）
            meta_query = f"""
                SELECT docid, title, summary, publish_time, source, url
                FROM documents 
                WHERE docid IN ({','.join(['%s'] * len(doc_ids))})
            """
            with conn.cursor(dictionary=True) as meta_cursor:
                meta_cursor.execute(meta_query, doc_ids)
                if meta_cursor.with_rows:  # 显式检查结果集
                    meta_map = {row['docid']: row for row in meta_cursor}

            # 关键词查询（流式处理）
            term_query = f"""
                SELECT docid, term 
                FROM doc_terms 
                WHERE docid IN ({','.join(['%s'] * len(doc_ids))})
                ORDER BY tf DESC
            """
            with conn.cursor(buffered=True) as term_cursor:
                term_cursor.execute(term_query, doc_ids)
                for docid, term in term_cursor:
                    keywords_map[docid].append(term)

        except mysql.connector.Error as e:
            print(f"数据库查询失败: {str(e)}")
            return render_template('error.html')

    # 合并结果
    results = []
    for item in raw_scores:
        doc_id = item['docid']
        score = item['score']
        keywords = item.get('keywords', [])  # 安全获取关键词
        meta = meta_map.get(doc_id, {
            'title': f"文档{doc_id}",
            'summary': "内容不可用",
            'publish_time': '1970-01-01',
            'source': '未知来源',
            'url': "#"
        })
        meta.update({
            'score': score,
            'keywords': keywords
        })
        results.append(meta)

    # 按分数排序
    sorted_results = sorted(results, key=lambda x: x["score"], reverse=True) or []
    return render_template('res.html',
                           query=query,
                           results=sorted_results)


@app.route('/online')
def serve_online():
    """在线搜索页面"""
    return render_template('online.html')


@app.route('/onlineres')
def handle_online_search():
    """在线搜索结果页"""
    query = escape(request.args.get('query', ''))


    try:
        # 这里可以接入真正的联网搜索API（例如Google Custom Search）
        # 目前暂时复用本地搜索作为演示
        se = SearchEngine(db_config)
        raw_scores = se.search(query)
        se.close()

        # 处理元数据
        results = []
        for doc_id, score in raw_scores:
            meta = get_doc_metadata(doc_id)
            if meta:
                meta["score"] = score
                results.append(meta)

        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True) or []

        return render_template('onlineres.html',
                               query=query,
                               results=sorted_results,
                               search_type="在线")

    except Exception as e:
        return render_template('error.html',
                               error_message=f"在线搜索失败: {str(e)}")


# 添加API路由（可选）
@app.route('/api/online_search', methods=['GET'])
def handle_online_api():
    query = request.args.get('q', '')
    try:
        # 这里可以调用真正的在线搜索API
        # 示例返回假数据
        return jsonify({
            "status": "success",
            "query": query,
            "results": [{
                "title": "在线结果示例",
                "url": "https://example.com",
            }]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/search', methods=['GET'])
def handle_search():
    """API 搜索端点（与 /search 逻辑对齐）"""
    query = request.args.get('query', '').strip()

    try:
        # 参数校验
        if not query:
            return jsonify({
                "status": "error",
                "error": "Query parameter 'query' is required",
                "results": []
            }), 400

        # 初始化搜索
        se = SearchEngine(db_config)
        raw_scores = se.search(query)
        doc_ids = [item['docid'] for item in raw_scores] if raw_scores else []
        print(doc_ids)

        # 无结果处理
        if not doc_ids:
            return jsonify({
                "status": "success",
                "query": query,
                "results": []
            })

        # 数据库查询（使用连接池）
        with get_connection_from_pool() as conn:  # 替换为实际连接池获取方式
            meta_map = {}
            keywords_map = defaultdict(list)

            try:
                # 元数据查询
                meta_query = f"""
                    SELECT docid, title, publish_time, source, summary, url
                    FROM documents 
                    WHERE docid IN ({','.join(['%s'] * len(doc_ids))})
                """
                with conn.cursor(dictionary=True) as meta_cursor:
                    meta_cursor.execute(meta_query, doc_ids)
                    meta_map = {row['docid']: row for row in meta_cursor}

                # 关键词查询
                term_query = f"""
                    SELECT docid, term 
                    FROM doc_terms 
                    WHERE docid IN ({','.join(['%s'] * len(doc_ids))})
                    ORDER BY tf DESC
                """
                with conn.cursor(buffered=True) as term_cursor:
                    term_cursor.execute(term_query, doc_ids)
                    for docid, term in term_cursor:
                        keywords_map[docid].append(term)

            except mysql.connector.Error as e:
                return jsonify({
                    "status": "error",
                    "error": f"Database error: {str(e)}",
                    "results": []
                }), 500

        # 合并结果
        results = []
        for item in raw_scores:
            doc_id = item['docid']
            score = item['score']

            meta = meta_map.get(doc_id, {
                "title": f"文档{doc_id}",
                "publish_time": "1970-01-01",
                "source": "未知来源",
                "summary": "无摘要内容"
            })

            # 合并关键词
            meta.update({
                "score": round(float(score), 4),
                "keywords": keywords_map.get(doc_id, [])
            })
            results.append(meta)

        # 排序并返回
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

        return jsonify({
            "status": "success",
            "query": query,
            "results": sorted_results
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "results": []
        }), 500

    finally:
        if 'se' in locals():
            se.close()


@app.route('/api/doc/<int:doc_id>', methods=['GET'])
def get_full_document(doc_id):
    """获取完整文档内容"""
    xml_path = safe_join(CONFIG["xml_dir"], f"{doc_id}.xml")
    if not os.path.exists(xml_path):
        return jsonify({"error": "文档不存在"}), 404

    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            "status": "success",
            "content": content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/validate', methods=['POST'])
def validate_xml():
    if 'xml' not in request.files:
        return jsonify(valid=False, message="未接收到文件")

    file = request.files['xml']
    if file.filename == '':
        return jsonify(valid=False, message="空文件名")

    # 保存临时文件
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(temp_path)

    # 执行验证
    is_valid, message = XMLParser.validate_structure(temp_path)
    os.remove(temp_path)  # 清理临时文件

    return jsonify(valid=is_valid, message=message)

@app.route('/upload', methods=['GET'])
def serve_upload():
    """返回文件上传页面"""
    return render_template('upload.html')
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'xml' not in request.files:
        return jsonify(error="未接收到文件"), 400

    file = request.files['xml']
    if file.filename == '':
        return jsonify(error="空文件名"), 400

    # 保存文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    try:
        # 解析XML
        parsed_data = XMLParser.parse(file_path)
        if not parsed_data:
            raise ValueError("XML解析失败")

        # 构建索引
        indexer = MySQLIndexer()
        indexer.process_xml(file.filename)

        return jsonify({
            "status": "success",
            "docid": os.path.splitext(file.filename)[0],
            "data": parsed_data
        })

    except Exception as e:
        return jsonify(error=str(e)), 500

    finally:
        os.remove(file_path)  # 清理上传文件

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',
                         error_code=404,
                         error_message="您寻找的页面已去火星旅行",
                         error_detail=str(e)), 404
# 在server.py中添加全局错误处理
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_errors(e):
    return render_template('error.html',
                         error_code=e.code,
                         error_message=e.description,
                         error_detail=str(e)), e.code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
