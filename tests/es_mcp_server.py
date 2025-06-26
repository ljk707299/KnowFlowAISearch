import json
from fastapi import HTTPException
from elasticsearch import Elasticsearch
from fastmcp import FastMCP

# Initialize Elasticsearch server
mcp = FastMCP("ElasticsearchMCP",  host="127.0.0.1", port=9005)

 
@mcp.tool(description="使用Elasticsearch在my_index索引中搜索title和content字段，返回高亮结果")
def perform_elastic_search(query: str):
    es = Elasticsearch(
        ["http://127.0.0.1:9200"],
        verify_certs=False
    )
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")

        query_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "content"],
                    "type": "best_fields"
                }
            },
            "highlight": {
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"],
                "fields": {
                    "title": {},
                    "content": {}
                }
            }
        }
        response = es.search(index="my_index", body=query_body).body
        response_content = json.dumps(response, ensure_ascii=False)
        print(f"perform_elastic_search 结果: {response_content}")
        return response_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


 

# 启动 MCP 服务
if __name__ == "__main__":
    mcp.run(transport='sse') 