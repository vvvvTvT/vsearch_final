# 基于Web信息检索的可视化查询系统设计与实现
设计并实现一个用户友好的Web界面，允许用户通过可视化的图形界面执行查询操作。前端部分将使用HTML、CSS和JavaScript来构建，确保界面的简洁、美观和响应性。后端将连接数据库，支持用户通过可视化界面输入文字查询条件。针对数据库中查询不到的数据，采用信息检索技术在Web的海量信息中检索合适的结果。
# 基本功能
## 本地检索
### 内容检索
输入关键词后搜索，可在本地数据库依据BM25算法打分排序搜索到最相关的前30条内容。
### 结果筛选
通过搜索结果页面右侧可视化图表，可获取结果关键词、发布时间、来源等相关分布；点击图中对应位置，可对结果进行筛选。
## 联网搜索
利用Google可编程搜索引擎，对关键词进行联网搜索，且可以将结果保存为本地xml。
## 文件上传
通过上传联网搜索保存的或自己编写的xml文件，将搜索结果存入本地，url可指向本地文件，实现本地私有化检索部署。
# Todo
- 优化联网结果保存过程，使其直接入库，省去保存xml到本地的过程；
- 使文件上传可接受多种类型文件；
- 优化关键词，使其准确有效；
- 优化搜索结果页面，使其可连续加载或分页加载；
- 优化UI显示。

[demo](http://search.vvt.icu)

