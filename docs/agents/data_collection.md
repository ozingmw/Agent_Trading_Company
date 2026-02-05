# DataCollectionAgent

Responsibilities:
- Fetch KIS market data on demand.
- Ingest news (Naver, Daum, NewsAPI) and social data (Reddit).
- Produce concise summaries and features for other agents.

Data policy:
- No raw data persistence.
- Use in-memory caching only within a cycle.
