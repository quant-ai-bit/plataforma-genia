import httpx

token = "ccee360b-863e-4aba-8411-6cc3e0d26889"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

url = "https://backboard.railway.app/graphql/v2"

query = """
query {
  service(id: "a725bb0f-983e-42ec-afd7-abfdba97e916") {
    name
    serviceInstances {
      edges {
        node {
          source {
            image
          }
        }
      }
    }
  }
}
"""

try:
    resp = httpx.post(url, headers=headers, json={"query": query})
    print(resp.json())
except Exception as e:
    print("Error:", e)
