import asyncio
import os
from dotenv import load_dotenv
from ag_forecast.src.backends.openrouter_backend import OpenRouterBackend
from ag_forecast.src.data_mcps.openrouter_perplexity_mcp import OpenRouterPerplexityMCP
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.workflows.researcher_agent import ResearcherAgent
from ag_forecast.src.workflows.analyst_agent import AnalystAgent
from ag_forecast.src.workflows.supervisor_agent import SupervisorAgent
from ag_forecast.src.workflows.iterative_research import IterativeResearchWorkflow
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import MeanConsensus
from ag_forecast.src.utils.logger import ForecastLogger

from ag_forecast.src.workflows.schema_agent import SchemaAgent
from ag_forecast.src.utils.report_generator import ReportGenerator

# Load environment variables from .env file if present
load_dotenv()

async def main():
    # Initialize logger
    logger = ForecastLogger(base_dir="logs")
    logger.section("INITIALIZATION")
    logger.info(f"Log file: {logger.get_log_path()}")
    
    # Configuration
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not openrouter_api_key:
        logger.error("OPENROUTER_API_KEY not found in environment variables")
        print("Please set OPENROUTER_API_KEY environment variable.")
        return

    logger.info("Initializing Bot with OpenRouter...")
    print(f"Initializing Bot with OpenRouter...")
    print(f"Logs will be saved to: {logger.get_log_path()}")

    # 1. Setup Components
    backend = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-4o")
    logger.info(f"Backend: OpenRouter with model openai/gpt-4o")
    
    # Data MCPs - Using Perplexity via OpenRouter
    data_mcps = {
        "perplexity": OpenRouterPerplexityMCP(api_key=openrouter_api_key)
    }
    logger.info(f"Data MCPs: {list(data_mcps.keys())}")
    
    # Initialize Components
    retrieval = AgenticRetrieval(backend, data_mcps, max_rounds=3, logger=logger)
    analyst = AnalystAgent(backend, logger=logger)
    supervisor = SupervisorAgent(backend, logger=logger)
    schema_agent = SchemaAgent(backend, logger=logger)
    
    # Create Community of Researchers (Forecasters)
    researchers = [
        ResearcherAgent(backend, logger=logger, agent_id=i+1) 
        for i in range(3)
    ]
    community = Community(researchers, logger=logger)
    
    consensus = MeanConsensus()
    
    # Initialize Iterative Workflow
    bot = IterativeResearchWorkflow(
        retrieval=retrieval,
        analyst_agent=analyst,
        supervisor=supervisor,
        schema_agent=schema_agent,
        community=community,
        consensus=consensus,
        max_loop_rounds=3,
        logger=logger
    )
    
    # Run Forecast
    question = "What will the highest percentage of overall compute capacity held by a single organisation be on January 1, 2028?"
    
    print(f"\nForecasting: {question}")
    print(f"Check {logger.get_log_path()} for detailed logs\n")
    
    try:
        result = await bot.run(question)
    
        print("\n" + "="*80)
        print("RESULT")
        print("="*80)
        print(f"Aggregated Prediction: {result['aggregated_prediction']}")
        print(f"Full logs saved to: {logger.get_log_path()}")
        
        # Generate Report
        print("\nGenerating Report...")
        report_gen = ReportGenerator(logger.get_run_dir())
        report_gen.generate()
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
