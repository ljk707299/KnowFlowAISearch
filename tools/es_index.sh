#!/bin/bash

# 定义索引名称
INDEX_NAME="my_index"

# 1. 测试分词器
echo -e "\n\033[1;36m1. 测试中文分词器...\033[0m"
curl -X POST "http://localhost:9200/_analyze" -H "Content-Type: application/json" -d '{
  "analyzer": "ik_max_word",
  "text": "这是一个中文测试,五一假期过的真的很充实"
}'
echo -e "\n"

# 2. 检查IK插件
echo -e "\n\033[1;36m2. 检查中文分词插件是否安装...\033[0m"
curl -X GET "http://localhost:9200/_cat/plugins?pretty"
echo -e "\n"

# 3. 创建索引
echo -e "\n\033[1;36m3. 创建索引($INDEX_NAME)并设置IK分词器...\033[0m"
curl -X PUT "http://localhost:9200/$INDEX_NAME" -H "Content-Type: application/json" -d '{
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
echo -e "\n"

# 4. 验证索引映射
echo -e "\n\033[1;36m4. 验证索引映射...\033[0m"
sleep 1  # 等待索引创建完成
curl -X GET "http://localhost:9200/$INDEX_NAME/_mapping?pretty"
echo -e "\n"

# 5. 插入测试数据
echo -e "\n\033[1;36m5. 插入测试数据...\033[0m"

# 文档1
curl -X POST "http://localhost:9200/$INDEX_NAME/_doc/1" -H "Content-Type: application/json" -d '{
  "title": "好莱坞被吓懵了",
  "content": "一言不合就加关税。在全世界眼中，好莱坞一直都很强势。2023年，美国电影出口额226亿美元，其中153亿是顺差。但在特朗普眼里，美国电影业正在\"迅速消亡\"，\"好莱坞和美国许多其他领域正遭受重创。这是其他国家共同筹划的行动，构成了对国家安全的威胁\"！这都是国家安全？！不得不说，现在的美国，太虚了。怎么办？特朗普宣布，对所有进口电影，立刻加征关税100%。在特朗普的推文中，最后这句话所有字母都是大写，应该也是他看重的：\"我们要电影再次在美国制作！\"美国电影，你请回来。特朗普号令一出，美国商务部长卢特尼克立刻回复：\"我们正在处理此事。\"但好莱坞都目瞪口呆。"
}'
echo -e "\n"

# 文档2
curl -X POST "http://localhost:9200/$INDEX_NAME/_doc/2" -H "Content-Type: application/json" -d '{
  "title": "全家不工作、吸血瘫痪哥哥！",
  "content": "近日，上海浦东检察院破获一起触目惊心的工伤诈骗案：弟弟冒用高位截瘫哥哥的身份领取高额工伤保险金，全家不工作，住新房。而真正的工伤受害者哥哥在破旧的老宅躺着硬板床，连护理床都没有，直至因感染而去世。"
}'
echo -e "\n"

# 文档3
curl -X POST "http://localhost:9200/$INDEX_NAME/_doc/3" -H "Content-Type: application/json" -d '{
  "title": "以色列总理：将占领加沙领土，平民将被转移！",
  "content": "当地时间5月5日，以色列总理内塔尼亚胡表示，以色列计划在加沙地带扩大的军事行动将是\"高强度\"的。据以媒体报道，内塔尼亚胡称此次军事行动计划重点将转向\"占领领土并在加沙地带维持以军的持续存在\"。"
}'
echo -e "\n"

# 6. 验证数据插入
echo -e "\n\033[1;36m6. 验证数据插入...\033[0m"
sleep 1  # 等待数据索引完成
curl -X GET "http://localhost:9200/$INDEX_NAME/_search?pretty"
echo -e "\n"

# 7. 全文检索测试
echo -e "\n\033[1;36m7. 全文检索测试(搜索\"好莱坞\")...\033[0m"
curl -X POST "http://localhost:9200/$INDEX_NAME/_search?pretty" -H "Content-Type: application/json" -d '{
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
echo -e "\n"

# 8. 清理测试数据
echo -e "\n\033[1;36m8. 清理测试数据...\033[0m"
read -p "是否要删除测试索引 $INDEX_NAME? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    curl -X DELETE "http://localhost:9200/$INDEX_NAME"
    echo -e "\n索引 $INDEX_NAME 已删除"
else
    echo -e "\n保留测试索引 $INDEX_NAME"
fi

echo -e "\n\033[1;32m所有操作已完成！\033[0m"
