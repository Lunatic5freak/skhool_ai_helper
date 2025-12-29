import requests
import json
import time

BASE_URL = "http://localhost:8000"


def test_multi_stage_queries():
    """Test multi-stage query processing with agent"""

    print("🤖 Testing Multi-Stage Query Processing")
    print("=" * 60)

    complex_queries = [
        {
            "message": "First show me what tables are available, then find electronics products under $500",
            "user_id": 1,
            "endpoint": "/chat/agent",
            "description": "Multi-step: Schema lookup then query"
        },
        {
            "message": "I want to understand my shopping pattern. Show me my orders, what products I bought, and how much I spent each month",
            "user_id": 1,
            "endpoint": "/chat/agent",
            "description": "Complex: Multi-table join with aggregation"
        },
        {
            "message": "What are the different product categories and how many products are in each? Also show me sample products from Electronics",
            "user_id": 2,
            "endpoint": "/chat/agent",
            "description": "Multi-part: Aggregation then sample data"
        },
        {
            "message": "Show me products that are low in stock and also tell me which of these products have been ordered recently",
            "user_id": 3,
            "endpoint": "/chat/agent",
            "description": "Complex: Inventory analysis with order history"
        }
    ]

    for i, query in enumerate(complex_queries, 1):
        print(f"\n🔹 Test {i}: {query['description']}")
        print(f"   Query: '{query['message']}'")
        print(f"   Endpoint: {query['endpoint']}")

        try:
            start_time = time.time()

            response = requests.post(
                f"{BASE_URL}{query['endpoint']}",
                json={
                    "message": query["message"],
                    "user_id": query["user_id"]
                },
                timeout=120
            )

            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success (Time: {elapsed_time:.2f}s)")
                print(f"   Response preview: {result['response'][:200]}...")
                if result.get('sql_query'):
                    print(f"   SQL Generated: {result['sql_query'][:100]}...")
                if result.get('data'):
                    print(f"   Data rows: {len(result['data'])}")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")


def compare_agents():
    """Compare agent vs direct approaches"""

    print("\n🔄 Comparing Agent vs Direct Approaches")
    print("=" * 60)

    test_queries = [
        "Show my recent orders",
        "What electronics products do you have?",
        "How much have I spent in total?"
    ]

    for query in test_queries:
        print(f"\n📝 Query: '{query}'")

        for endpoint in ["/chat/agent", "/chat/direct"]:
            print(f"  {endpoint}:")

            try:
                start_time = time.time()

                response = requests.post(
                    f"{BASE_URL}{endpoint}",
                    json={
                        "message": query,
                        "user_id": 1
                    },
                    timeout=30
                )

                elapsed_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    print(f"    Time: {elapsed_time:.2f}s")
                    print(f"    Response length: {len(result['response'])} chars")
                    if result.get('sql_query'):
                        print(f"    SQL: {result['sql_query'][:80]}...")
                else:
                    print(f"    ❌ Failed: {response.status_code}")

            except Exception as e:
                print(f"    ❌ Exception: {str(e)}")


def test_tool_functionality():
    """Test individual tool functionality"""

    print("\n🛠️ Testing Individual Tools")
    print("=" * 60)

    # Test schema lookup
    print("\n📋 Testing Schema Lookup:")
    response = requests.get(f"{BASE_URL}/tables")
    tables = response.json().get('tables', [])
    print(f"  Available tables: {', '.join(tables)}")

    # Test sample data
    print("\n📊 Testing Sample Data:")
    response = requests.get(f"{BASE_URL}/sample/products?limit=2")
    sample = response.json()
    print(f"  Sample products: {sample['count']} rows")
    for item in sample['data']:
        print(f"    - {item['name']} (${item['price']})")

    # Test custom query
    print("\n⚡ Testing Custom Query:")
    response = requests.get(f"{BASE_URL}/query", params={
        "query": "SELECT category, COUNT(*) as count FROM products GROUP BY category"
    })
    result = response.json()
    print(f"  Query results: {result['count']} rows")
    for row in result['data']:
        print(f"    - {row['category']}: {row['count']} products")


def test_health():
    """Test health endpoint"""
    print("\n🏥 Testing Health Endpoint")
    response = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {response.json()}")


def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive Tests")
    print("=" * 60)

    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print("✅ Server is running!")
        print(f"Version: {response.json().get('version')}")

        # Run tests
        test_health()
        test_tool_functionality()
        test_multi_stage_queries()
        compare_agents()

        print("\n" + "=" * 60)
        print("🎉 All tests completed!")
        print("\n📋 Architecture Summary:")
        print("- Agent-based approach: Uses ReAct agent with 6 specialized tools")
        print("- Direct approach: Simple LLM → SQL → Execute flow")
        print("- Multi-stage queries: Agent can plan complex multi-step operations")
        print("- Tool-based: Each database operation has a dedicated tool")

    except requests.ConnectionError:
        print("❌ Server is not running. Please start the server:")
        print("   cd app && python main.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()