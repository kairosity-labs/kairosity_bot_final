import argparse
import asyncio
import logging
import os
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from forecasting_tools import (
    BinaryQuestion,
    ForecastBot,
    GeneralLlm,
    MetaculusApi,
    MetaculusQuestion,
    MultipleChoiceQuestion,
    NumericDistribution,
    NumericQuestion,
    Percentile,
    BinaryPrediction,
    PredictedOptionList,
    ReasonedPrediction,
    clean_indents,
    structure_output,
)

# AGForecast Imports
from ag_forecast.src.backends.openrouter_backend import OpenRouterBackend
from ag_forecast.src.data_mcps.asknews_mcp import AskNewsMCP
from ag_forecast.src.data_mcps.openrouter_perplexity_mcp import OpenRouterPerplexityMCP
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.workflows.researcher_agent import ResearcherAgent
from ag_forecast.src.workflows.analyst_agent import AnalystAgent
from ag_forecast.src.workflows.supervisor_agent import SupervisorAgent
from ag_forecast.src.workflows.iterative_research import IterativeResearchWorkflow
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import MeanConsensus
from ag_forecast.src.workflows.schema_agent import SchemaAgent
from ag_forecast.src.utils.logger import ForecastLogger

logger = logging.getLogger(__name__)


class AGForecastBot(ForecastBot):
    """
    Forecasting Bot powered by AGForecast's Iterative Research Workflow.
    Uses OpenRouter for LLMs and Perplexity for retrieval.
    """

    def __init__(self, openrouter_api_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize AGForecast components
        self.ag_logger = ForecastLogger(base_dir="logs")
        
        # Backends
        # User request: "anthropic/claude-sonnet-4.5". 
        self.backend_simple = OpenRouterBackend(api_key=openrouter_api_key, model_name="anthropic/claude-sonnet-4.5")
        self.backend_supervisor = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-5.1")
        
        # Community Backends
        self.backend_c1 = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-5.1")
        self.backend_c2 = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/o3-mini-high")
        self.backend_c3 = OpenRouterBackend(api_key=openrouter_api_key, model_name="google/gemini-3-pro-preview")
        
        # Data MCPs
        self.data_mcps = {
            "perplexity": OpenRouterPerplexityMCP(
                api_key=openrouter_api_key,
                model="openai/gpt-4o-mini-search-preview",
            )
        }
        asknews_client_id = os.getenv("ASKNEWS_CLIENT_ID")
        asknews_secret = os.getenv("ASKNEWS_SECRET")
        if asknews_client_id and asknews_secret:
            self.data_mcps["asknews"] = AskNewsMCP(
                client_id=asknews_client_id,
                client_secret=asknews_secret,
            )
            self.ag_logger.info("AskNews MCP enabled for agentic retrieval.")
        else:
            self.ag_logger.info("ASKNEWS_CLIENT_ID or ASKNEWS_SECRET not found. AskNews will be disabled.")
        
        # Initialize Agents
        # Simple LLM calls: Agentic Retrieval, Analyst, Schema Agent
        self.retrieval = AgenticRetrieval(self.backend_simple, self.data_mcps, max_rounds=3, logger=self.ag_logger)
        self.analyst = AnalystAgent(self.backend_simple, logger=self.ag_logger)
        self.schema_agent = SchemaAgent(self.backend_simple, logger=self.ag_logger)
        
        # Supervisor
        self.supervisor = SupervisorAgent(self.backend_supervisor, logger=self.ag_logger)
        
        # Community (Researchers)
        # 1. GPT-5.1
        # 2. o3-mini-high
        # 3. Gemini 3 Pro
        self.researchers = [
            ResearcherAgent(self.backend_c1, logger=self.ag_logger, agent_id=1),
            ResearcherAgent(self.backend_c2, logger=self.ag_logger, agent_id=2),
            ResearcherAgent(self.backend_c3, logger=self.ag_logger, agent_id=3)
        ]
        self.community = Community(self.researchers, logger=self.ag_logger)
        self.consensus = MeanConsensus()
        
        # Workflow
        self.workflow = IterativeResearchWorkflow(
            retrieval=self.retrieval,
            analyst_agent=self.analyst,
            supervisor=self.supervisor,
            schema_agent=self.schema_agent,
            community=self.community,
            consensus=self.consensus,
            max_loop_rounds=3,
            logger=self.ag_logger
        )

    async def run_research(self, question: MetaculusQuestion) -> str:
        """
        Runs the iterative research workflow to gather insights.
        """
        logger.info(f"Starting AGForecast research for: {question.question_text}")
        
        # Construct a comprehensive query
        query = f"""
        Question: {question.question_text}
        
        Resolution Criteria:
        {question.resolution_criteria}
        
        Fine Print:
        {question.fine_print}
        
        Background:
        {question.background_info}
        """
        
        try:
            # Run research-only workflow
            research_context = await self.workflow.run_research_only(query)
            logger.info(f"Research completed for {question.page_url}")
            return research_context
        except Exception as e:
            logger.error(f"Error during research for {question.page_url}: {e}")
            return f"Error during research: {str(e)}"

    async def _run_forecast_on_binary(
        self, question: BinaryQuestion, research: str
    ) -> ReasonedPrediction[float]:
        prompt = clean_indents(
            f"""
            You are a professional forecaster.
            
            Question: {question.question_text}
            
            Research Context:
            {research}
            
            Today is {datetime.now().strftime("%Y-%m-%d")}.
            
            Provide a forecast probability (0-100%) and reasoning.
            
            Structure your response as:
            Reasoning: ...
            Probability: XX%
            """
        )
        # Use the backend directly or via ForecastBot's mechanism. 
        # Here we use ForecastBot's get_llm for consistency with the base class if configured,
        # or we could use self.backend. Let's use self.backend for consistency with AGForecast.
        
        # Actually, ForecastBot expects us to return ReasonedPrediction.
        # Let's use the standard ForecastBot flow for the final step to leverage structure_output
        
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        binary_prediction: BinaryPrediction = await structure_output(
            reasoning, BinaryPrediction, model=self.get_llm("parser", "llm")
        )
        decimal_pred = max(0.01, min(0.99, binary_prediction.prediction_in_decimal))
        
        return ReasonedPrediction(prediction_value=decimal_pred, reasoning=reasoning)

    async def _run_forecast_on_multiple_choice(
        self, question: MultipleChoiceQuestion, research: str
    ) -> ReasonedPrediction[PredictedOptionList]:
        prompt = clean_indents(
            f"""
            You are a professional forecaster.
            
            Question: {question.question_text}
            Options: {question.options}
            
            Research Context:
            {research}
            
            Today is {datetime.now().strftime("%Y-%m-%d")}.
            
            Provide probabilities for each option.
            """
        )
        parsing_instructions = clean_indents(
            f"""
            Make sure that all option names are one of the following:
            {question.options}
            """
        )
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        predicted_option_list: PredictedOptionList = await structure_output(
            text_to_structure=reasoning,
            output_type=PredictedOptionList,
            model=self.get_llm("parser", "llm"),
            additional_instructions=parsing_instructions,
        )
        return ReasonedPrediction(
            prediction_value=predicted_option_list, reasoning=reasoning
        )

    async def _run_forecast_on_numeric(
        self, question: NumericQuestion, research: str
    ) -> ReasonedPrediction[NumericDistribution]:
        prompt = clean_indents(
            f"""
            You are a professional forecaster.
            
            Question: {question.question_text}
            
            Research Context:
            {research}
            
            Today is {datetime.now().strftime("%Y-%m-%d")}.
            
            Provide a numeric distribution (percentiles).
            """
        )
        reasoning = await self.get_llm("default", "llm").invoke(prompt)
        percentile_list: list[Percentile] = await structure_output(
            reasoning, list[Percentile], model=self.get_llm("parser", "llm")
        )
        prediction = NumericDistribution.from_question(percentile_list, question)
        return ReasonedPrediction(prediction_value=prediction, reasoning=reasoning)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Suppress LiteLLM logging
    litellm_logger = logging.getLogger("LiteLLM")
    litellm_logger.setLevel(logging.WARNING)
    litellm_logger.propagate = False

    parser = argparse.ArgumentParser(
        description="Run the AGForecast bot"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["tournament", "metaculus_cup", "test_questions"],
        default="tournament",
        help="Specify the run mode (default: tournament)",
    )
    args = parser.parse_args()
    run_mode: Literal["tournament", "metaculus_cup", "test_questions"] = args.mode
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment variables.")

    # Initialize AGForecastBot
    bot = AGForecastBot(
        openrouter_api_key=openrouter_key,
        research_reports_per_question=1,
        predictions_per_research_report=1, # One prediction per research report
        use_research_summary_to_forecast=False,
        publish_reports_to_metaculus=True,
        folder_to_save_reports_to="logs/reports",
        skip_previously_forecasted_questions=True,
        llms={
            "default": GeneralLlm(
                model="openrouter/anthropic/claude-sonnet-4.5",
                temperature=0.3,
                api_key=openrouter_key
            ),
            "parser": GeneralLlm(
                model="openrouter/anthropic/claude-sonnet-4.5",
                api_key=openrouter_key
            )
        }
    )

    if run_mode == "tournament":
        seasonal_tournament_reports = asyncio.run(
            bot.forecast_on_tournament(
                MetaculusApi.CURRENT_AI_COMPETITION_ID, return_exceptions=True
            )
        )
        minibench_reports = asyncio.run(
            bot.forecast_on_tournament(
                MetaculusApi.CURRENT_MINIBENCH_ID, return_exceptions=True
            )
        )
        forecast_reports = seasonal_tournament_reports + minibench_reports
    elif run_mode == "metaculus_cup":
        bot.skip_previously_forecasted_questions = False
        forecast_reports = asyncio.run(
            bot.forecast_on_tournament(
                MetaculusApi.CURRENT_METACULUS_CUP_ID, return_exceptions=True
            )
        )
    elif run_mode == "test_questions":
        EXAMPLE_QUESTIONS = [
            "https://www.metaculus.com/questions/578/human-extinction-by-2100/",
        ]
        bot.skip_previously_forecasted_questions = False
        questions = [
            MetaculusApi.get_question_by_url(question_url)
            for question_url in EXAMPLE_QUESTIONS
        ]
        forecast_reports = asyncio.run(
            bot.forecast_questions(questions, return_exceptions=True)
        )
    
    bot.log_report_summary(forecast_reports)
