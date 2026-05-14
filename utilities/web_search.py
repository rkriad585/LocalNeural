import requests
import json

def search_duckduckgo(query, max_results=5):
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10
        )
        data = resp.json()
        results = []

        abstract = data.get("AbstractText", "")
        if abstract:
            source = data.get("AbstractSource", "")
            url = data.get("AbstractURL", "")
            results.append({"title": source, "snippet": abstract, "url": url})

        for topic in data.get("RelatedTopics", []):
            if "Text" in topic:
                results.append({
                    "title": topic.get("Text", "").split(" - ")[0],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "")
                })
                if len(results) >= max_results:
                    break

        return results[:max_results]

    except Exception as e:
        return [{"title": "Search Error", "snippet": str(e), "url": ""}]
