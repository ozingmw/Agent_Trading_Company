# DataCollectionAgent

Responsibilities:
- Fetch KIS market data on demand.
- Ingest news (Naver, Daum, NewsAPI) and social data (Reddit).
- Produce concise summaries and features for other agents.
- Update universe and market trend context from gathered information.

Data policy:
- No raw data persistence.
- Use in-memory caching only within a cycle.
