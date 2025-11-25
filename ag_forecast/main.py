import asyncio
import os

from ag_forecast.src.backends.openai_backend import OpenAIBackend
from ag_forecast.src.bot.forecasting_bot import ForecastingBot
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import MeanConsensus
from ag_forecast.src.data_mcps.asknews_mcp import AskNewsMCP
from ag_forecast.src.data_mcps.perplexity_mcp import PerplexityMCP
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.workflows.researcher_agent import ResearcherAgent


async def main() -> None:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
    asknews_client_id = os.getenv("ASKNEWS_CLIENT_ID")
    asknews_secret = os.getenv("ASKNEWS_SECRET")

    if not openai_api_key:
        print("Please set OPENAI_API_KEY environment variable.")
        return

    backend = OpenAIBackend(api_key=openai_api_key, model_name="gpt-4o")

    data_mcps: dict[str, object] = {}
    if perplexity_api_key:
        data_mcps["perplexity"] = PerplexityMCP(api_key=perplexity_api_key)
    else:
        print("Warning: PERPLEXITY_API_KEY not found. Retrieval might be limited.")

    if asknews_client_id and asknews_secret:
        data_mcps["asknews"] = AskNewsMCP(client_id=asknews_client_id, client_secret=asknews_secret)
    else:
        print("Warning: ASKNEWS_CLIENT_ID or ASKNEWS_SECRET not found. AskNews will be disabled.")

    retrieval = AgenticRetrieval(backend, data_mcps)

    agents = [ResearcherAgent(backend) for _ in range(3)]
    community = Community(agents)

    consensus = MeanConsensus()

    bot = ForecastingBot(retrieval, community, consensus)

    question = "Will SpaceX successfully launch Starship to orbit before 2025?"
    print(f"Forecasting: {question}")

    try:
        result = await bot.forecast(question)
        print("\n--- Result ---")
        print(f"Aggregated Prediction: {result['aggregated_prediction']}")
        print(f"Retrieval Summary: {result['retrieval_summary'][:200]}...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
