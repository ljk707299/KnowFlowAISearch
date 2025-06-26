

启动ES：

方法一：
在dockerDesktop 启动

方法二：

脚本启动

docker pull elasticsearch:8.18.0

执行es.sh 启动，此处关闭了安全认证


docker compose up --build



elasticsearch版本：8.18.0

进入docker容器内部：

bin/elasticsearch-plugin install https://get.infini.cloud/elasticsearch/analysis-ik/8.18.0


bin/elasticsearch-plugin list


curl -X POST "http://localhost:9200/_analyze" -H "Content-Type: application/json" -d '{
  "analyzer": "ik_max_word",
  "text": "这是一个中文测试,五一假期过的真的很充实"
}'





from elasticsearch import Elasticsearch

# 初始化 Elasticsearch 客户端
es = Elasticsearch(
    ["http://localhost:9200"],
    verify_certs=False  # 开发环境忽略 SSL 验证
)

# 测试分词器
response = es.indices.analyze(
    body={
        "analyzer": "ik_max_word",
        "text": "这是一个中文测试"
    }
)

# 打印分词结果
for token in response["tokens"]:
    print(f"Token: {token['token']}, Type: {token['type']}, Position: {token['position']}")






# 禁用 HTTPS（如果不需要）

elasticsearch.yml


- xpack.security.enabled=false
- xpack.security.http.ssl.enabled=false
- discovery.type=single-node



# 查看中文分词插件是否安装ok？

http://localhost:9200/_cat/plugins?pretty



# 创建索引（使用 ik_max_word）

我们将创建一个名为 my_index 的索引，字段 title 和 content 使用 ik_max_word 分词器。


curl -X PUT "http://localhost:9200/my_index1" -H "Content-Type: application/json" -d '{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "ik_max_word"
      },
      "content": {
        "type": "text",
        "analyzer": "ik_max_word"
      }
    }
  }
}'


# 验证索引创建

curl -X GET "http://localhost:9200/my_index/_mapping?pretty"





# 插入 10 条数据


## 数据示例 ：以下是 3 条新闻数据，包含中文内容：

标题：好莱坞被吓懵了  
内容：一言不合就加关税。 在全世界眼中，好莱坞一直都很强势。2023年，美国电影出口额226亿美元，其中153亿是顺差。 但在特朗普眼里，美国电影业正在“迅速消亡”，“好莱坞和美国许多其他领域正遭受重创。这是其他国家共同筹划的行动，构成了对国家安全的威胁”！ 这都是国家安全？！ 不得不说，现在的美国，太虚了。 怎么办？ 特朗普宣布，对所有进口电影，立刻加征关税100%。 在特朗普的推文中，最后这句话所有字母都是大写，应该也是他看重的：“我们要电影再次在美国制作！” 美国电影，你请回来。 特朗普号令一出，美国商务部长卢特尼克立刻回复：“我们正在处理此事。” 但好莱坞都目瞪口呆。

标题：全家不工作、吸血瘫痪哥哥！ 
内容：近日，上海浦东检察院破获一起触目惊心的工伤诈骗案：弟弟冒用高位截瘫哥哥的身份领取高额工伤保险金，全家不工作，住新房。而真正的工伤受害者哥哥在破旧的老宅躺着硬板床，连护理床都没有，直至因感染而去世。

标题：以色列总理：将占领加沙领土，平民将被转移！ 
内容：当地时间5月5日，以色列总理内塔尼亚胡表示，以色列计划在加沙地带扩大的军事行动将是“高强度”的。据以媒体报道，内塔尼亚胡称此次军事行动计划重点将转向“占领领土并在加沙地带维持以军的持续存在”。
 

# 文档 1
curl -X POST "http://localhost:9200/my_index/_doc/1" -H "Content-Type: application/json" -d '{
  "title": "好莱坞被吓懵了",
  "content": "一言不合就加关税。 在全世界眼中，好莱坞一直都很强势。2023年，美国电影出口额226亿美元，其中153亿是顺差。 但在特朗普眼里，美国电影业正在“迅速消亡”，“好莱坞和美国许多其他领域正遭受重创。这是其他国家共同筹划的行动，构成了对国家安全的威胁”！ 这都是国家安全？！ 不得不说，现在的美国，太虚了。 怎么办？ 特朗普宣布，对所有进口电影，立刻加征关税100%。 在特朗普的推文中，最后这句话所有字母都是大写，应该也是他看重的：“我们要电影再次在美国制作！” 美国电影，你请回来。 特朗普号令一出，美国商务部长卢特尼克立刻回复：“我们正在处理此事。” 但好莱坞都目瞪口呆。"
}'

# 文档 2
curl -X POST "http://localhost:9200/my_index/_doc/2" -H "Content-Type: application/json" -d '{
  "title": "全家不工作、吸血瘫痪哥哥！",
  "content": "近日，上海浦东检察院破获一起触目惊心的工伤诈骗案：弟弟冒用高位截瘫哥哥的身份领取高额工伤保险金，全家不工作，住新房。而真正的工伤受害者哥哥在破旧的老宅躺着硬板床，连护理床都没有，直至因感染而去世。"
}'

# 文档 3
n


curl -X POST "http://localhost:9200/my_index/_doc/4" -H "Content-Type: application/json" -d '{
  "title": "以色列总理：将占领加沙领土，平民将被转移！",
  "content": "内容：当地时间5月5日，以色列总理内塔尼亚胡表示，以色列计划在加沙地带扩大的军事行动将是“高强度”的。据以媒体报道，内塔尼亚胡称此次军事行动计划重点将转向“占领领土并在加沙地带维持以军的持续存在”。"
}'


# 删除文档

curl -X DELETE "http://localhost:9200/my_index/_doc/11"

# 删除整个索引

curl -X DELETE "http://localhost:9200/my_index"

# 查看单个文档

curl -X GET "http://localhost:9200/my_index/_doc/1?pretty"

# 验证插入的数据

 http://localhost:9200/my_index/_search?pretty



# 全文检索

curl -X POST "http://localhost:9200/my_index/_search?pretty" -H "Content-Type: application/json" -d '{
  "query": {
    "multi_match": {
      "query": "好莱坞",
      "fields": ["title", "content"]
    }
  },
  "highlight": {
    "fields": {
      "title": {},
      "content": {}
    }
  }
}'



pip install --root-user-action=ignore --upgrade pip

pip  uninstall --root-user-action=ignore   elasticsearch

pip install elasticsearch 8.18.0


