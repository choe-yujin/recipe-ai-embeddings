import requests
import json

# OpenSearch 노드 정보 확인
def check_opensearch_plugins():
    try:
        response = requests.get('http://localhost:9201/_nodes/plugins')
        data = response.json()
        
        # 설치된 플러그인 확인
        for node_id, node_info in data['nodes'].items():
            plugins = node_info['plugins']
            print(f"Node {node_id} plugins:")
            for plugin in plugins:
                print(f"  - {plugin['name']} ({plugin['version']})")
                
            # Nori 플러그인 확인
            nori_installed = any(plugin['name'] == 'analysis-nori' for plugin in plugins)
            print(f"Nori plugin installed: {nori_installed}")
            
    except Exception as e:
        print(f"Error checking plugins: {e}")

# Nori 분석기 테스트
def test_nori_analyzer():
    try:
        # 임시 인덱스로 Nori 분석기 테스트
        test_data = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "korean_analyzer": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text", "analyzer": "korean_analyzer"}
                }
            }
        }
        
        response = requests.put('http://localhost:9201/test_nori', 
                              headers={'Content-Type': 'application/json'},
                              data=json.dumps(test_data))
        
        if response.status_code == 200:
            print("✅ Nori analyzer test successful!")
            # 테스트 인덱스 삭제
            requests.delete('http://localhost:9201/test_nori')
        else:
            print(f"❌ Nori analyzer test failed: {response.text}")
            
    except Exception as e:
        print(f"Error testing Nori analyzer: {e}")

if __name__ == "__main__":
    print("🔍 OpenSearch Nori Plugin Check")
    print("=" * 40)
    check_opensearch_plugins()
    print("\n" + "=" * 40)
    test_nori_analyzer()
