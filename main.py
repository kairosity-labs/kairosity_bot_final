import argparse
import asyncio
import logging
import os
from datetime import datetime
from typing import Literal, List, Dict, Any

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
    BinaryPrediction,
    PredictedOptionList,
    PredictedOption,
    ReasonedPrediction,
    clean_indents,
    structure_output,
)

from forecasting_tools.data_models.numeric_report import Percentile

# AGForecast Imports
from ag_forecast.src.backends.openrouter_backend import OpenRouterBackend
from ag_forecast.src.data_mcps.google_search_mcp import GoogleSearchMCP
from ag_forecast.src.data_mcps.google_scrape_mcp import GoogleScrapeMCP
from ag_forecast.src.data_mcps.parallel_mcp import ParallelMCP
from ag_forecast.src.data_mcps.perplexity_search_mcp import PerplexitySearchMCP
from ag_forecast.src.data_mcps.perplexity_sonar_mcp import PerplexitySonarMCP
from ag_forecast.src.data_mcps.asknews_mcp import AskNewsMCP
from ag_forecast.src.data_mcps.openrouter_gpt4o_mcp import OpenRouterGPT4OMCP
from ag_forecast.src.data_mcps.openroute_perplexity_mcp import OpenRouterPerplexityMCP
from ag_forecast.src.data_mcps.duckduckgo_mcp import DuckDuckGoMCP
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.workflows.researcher_agent import ResearcherAgent
from ag_forecast.src.workflows.analyst_agent import AnalystAgent
from ag_forecast.src.workflows.supervisor_agent import SupervisorAgent
from ag_forecast.src.workflows.reporter_agent import ReporterAgent
from ag_forecast.src.workflows.iterative_research import IterativeResearchWorkflow
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import MeanConsensus
from ag_forecast.src.consensus.AgenticConsensus import AgenticConsensus
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
        # self.backend_simple = OpenRouterBackend(api_key=openrouter_api_key, model_name="anthropic/claude-sonnet-4.5")
        self.backend_simple = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-5.1")
        self.backend_supervisor = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-5.1")
        
        # Community Backends
        self.backend_c1 = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-5.1")
        self.backend_c2 = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/o3-mini-high")
        # self.backend_c3 = OpenRouterBackend(api_key=openrouter_api_key, model_name="anthropic/claude-sonnet-4.5")
        self.backend_c3 = OpenRouterBackend(api_key=openrouter_api_key, model_name="openai/gpt-5.1")
        
        # Data MCPs
        self.data_mcps = {
            "parallel": ParallelMCP(),
            "perplexity_search": PerplexitySearchMCP(),
            "perplexity_sonar": PerplexitySonarMCP(),
            "duckduckgo": DuckDuckGoMCP()
        }

        # asknews_client_id = os.getenv("ASKNEWS_CLIENT_ID")
        # asknews_secret = os.getenv("ASKNEWS_SECRET")
        # if asknews_client_id and asknews_secret:
        #     self.data_mcps["asknews"] = AskNewsMCP(
        #         client_id=asknews_client_id,
        #         client_secret=asknews_secret,
        #     )
        #     self.ag_logger.info("AskNews MCP enabled for agentic retrieval.")
        # else:
        #     self.ag_logger.info("ASKNEWS_CLIENT_ID or ASKNEWS_SECRET not found. AskNews will be disabled.")
        
        # Initialize Agents
        # Simple LLM calls: Agentic Retrieval, Analyst, Schema Agent
        self.retrieval = AgenticRetrieval(self.backend_simple, self.data_mcps, max_rounds=3, max_queries=10, max_tokens=32768, logger=self.ag_logger)
        self.analyst = AnalystAgent(self.backend_simple, logger=self.ag_logger, max_tokens=32768)
        self.schema_agent = SchemaAgent(self.backend_simple, logger=self.ag_logger)
        
        # Supervisor
        self.supervisor = SupervisorAgent(self.backend_supervisor, max_tokens=32768, logger=self.ag_logger)
        
        # Community (Researchers)
        # 1. GPT-5.1 (o1 reasoning model - needs higher max_tokens)
        # 2. o3-mini-high (o3 reasoning model - needs higher max_tokens)
        # 3. Claude Sonnet 4.5
        self.researchers = [
            ResearcherAgent(self.backend_c1, logger=self.ag_logger, agent_id=1, max_tokens=32768),
            ResearcherAgent(self.backend_c2, logger=self.ag_logger, agent_id=2, max_tokens=32768),
            ResearcherAgent(self.backend_c3, logger=self.ag_logger, agent_id=3, max_tokens=32768)
        ]
        self.community = Community(self.researchers, logger=self.ag_logger)
        self.consensus = AgenticConsensus(self.backend_simple, max_tokens=32768, logger=self.ag_logger)
        
        # Reporter
        self.reporter = ReporterAgent(self.backend_simple, max_tokens=32768, logger=self.ag_logger)
        
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
            research_context, parent_ids = await self.workflow.run_research_only(query)
            
            # Store parent_ids in notepad for use in forecasting
            notepad = await self._get_notepad(question)
            notepad.note_entries["parent_ids"] = parent_ids
            
            logger.info(f"Research completed for {question.page_url}")

            return research_context
        except Exception as e:
            logger.error(f"Error during research for {question.page_url}: {e}")
            return f"Error during research: {str(e)}"

    async def _summarize_report(self, report: str) -> str:
        """
        Summarizes the detailed report for the Metaculus comment.
        """
        prompt = [
            {"role": "system", "content": "You are a helpful assistant that summarizes forecasting reports."},
            {"role": "user", "content": f"Please summarize the following forecasting report into a concise comment suitable for Metaculus. Focus on the key reasoning and the final conclusion. Keep it under 200 words.\n\nReport:\n{report}"}
        ]
        summary = await self.backend_simple.generate(prompt)
        return summary
    
    async def generate_report(
        self,
        question: MetaculusQuestion,
        research_context: str,
        researcher_outputs: List[Dict[str, Any]],
        consensus_output: Dict[str, Any],
        supervisor_critique: str
    ) -> str:
        from datetime import datetime
        
        report = await self.reporter.run(
            question=question.question_text,
            research_context=research_context,
            researcher_outputs=researcher_outputs,
            consensus_output=consensus_output,
            supervisor_critique=supervisor_critique
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"report_{timestamp}_{question.id}.md"
        report_path = f"reports/{safe_filename}"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Report saved to {report_path}")
        return report

    async def _generate_report(
        self,
        question,  # Can be str or question object
        research_context: str,
        researcher_outputs: List[Dict[str, Any]],
        consensus_output: Dict[str, Any],
        supervisor_critique: str,
        current_date: str = None
    ) -> str:
        """
        Generate a forecasting report using ReporterAgent.
        
        Args:
            question: The forecasting question (str or question object)
            research_context: Research context/findings
            researcher_outputs: List of researcher output dicts
            consensus_output: Consensus aggregation output dict
            supervisor_critique: Supervisor's critique text
            current_date: Current date string (generated if not provided)
            
        Returns:
            Markdown formatted report string
        """
        from datetime import datetime
        
        # Handle both string and question object
        question_text = question.question_text if hasattr(question, 'question_text') else str(question)
        
        # Use provided current_date or generate new one
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Call ReporterAgent with actual parameters
        report = await self.reporter.run(
            question=question_text,
            research_context=research_context,
            researcher_outputs=researcher_outputs,
            consensus_output=consensus_output,
            supervisor_critique=supervisor_critique,
            current_date=current_date
        )
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"report_{timestamp}.md"
        report_path = f"logs/reports/{safe_filename}"
        
        import os
        os.makedirs("logs/reports", exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Report saved to {report_path}")
        
        return report


    async def _run_forecast_on_binary(
        self, question: BinaryQuestion, research: str
    ) -> ReasonedPrediction[float]:
        # 1. Define Schema (Binary is simple, but we follow the pattern)
        # For binary, we just need a probability.
        
        # 2. Run Community
        # We need to adapt the community run to work with the pre-fetched research.
        # The Community.run method expects 'global_context' and 'schema'.
        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # We can reuse the schema agent or just define a simple schema for binary
        schema = {
            "schema_type": "Binary (Probability)",
            "options": ["yes", "no"],
            "description": "Define a function predict() -> {'yes': float, 'no': float} where 'yes' is the probability of the event occurring."
        }
        
        # Retrieve parent_ids from notepad
        notepad = await self._get_notepad(question)
        parent_ids = notepad.note_entries.get("parent_ids", [])
        
        community_results = await self.community.run(question.question_text, research, current_date, schema, parent_ids=parent_ids)
        
        # 3. Aggregate using AgenticConsensus (intelligent weighted consensus)
        if not community_results:
            logger.warning("No valid predictions from community. Falling back to legacy single-LLM forecast.")
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
            reasoning = await self.get_llm("default", "llm").invoke(prompt)
            binary_prediction: BinaryPrediction = await structure_output(
                reasoning, BinaryPrediction, model=self.get_llm("parser", "llm")
            )
            decimal_pred = max(0.01, min(0.99, binary_prediction.prediction_in_decimal))
            return ReasonedPrediction(prediction_value=decimal_pred, reasoning=reasoning)

        # Use AgenticConsensus with full researcher outputs for intelligent weighting
        if isinstance(self.consensus, AgenticConsensus):
            # Extract researcher node IDs for graph linking
            researcher_node_ids = [res.get("last_node_id") for res in community_results if res.get("last_node_id")]
            consensus_result = await self.consensus.aggregate_async(
                community_results, question.question_text, schema, current_date,
                parent_ids=researcher_node_ids
            )
            aggregated_prediction = consensus_result["prediction"]
        else:
            # Fallback for statistical consensus (MeanConsensus, etc.)
            predictions = [res["prediction"] for res in community_results if "prediction" in res]
            aggregated_prediction = self.consensus.aggregate(predictions)
        
        # Extract probability
        prob = aggregated_prediction.get("yes", 0.5)
        decimal_pred = max(0.01, min(0.99, prob))
        
        # 4. Generate Summary for Comment
        # We'll construct a report string from the individual forecasts to summarize
        full_report = f"Aggregated Prediction: {decimal_pred:.2%}\n\n"
        for res in community_results:
            full_report += f"Agent {res.get('agent_id', '?')} Analysis:\n{res.get('analysis', 'No analysis')}\nPrediction: {res.get('prediction')}\n\n"
            
        summary = await self._summarize_report(full_report)
        
        return ReasonedPrediction(prediction_value=decimal_pred, reasoning=summary)

    async def _run_forecast_on_multiple_choice(
        self, question: MultipleChoiceQuestion, research: str
    ) -> ReasonedPrediction[PredictedOptionList]:
        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Schema for Multiple Choice
        options_str = ", ".join(question.options)
        schema = {
            "schema_type": "Multiple Choice",
            "options": question.options,
            "description": f"Define a function predict() -> Dict[str, float] where keys are exactly one of: [{options_str}]. Values must sum to 1."
        }
        
        # Retrieve parent_ids from notepad
        notepad = await self._get_notepad(question)
        parent_ids = notepad.note_entries.get("parent_ids", [])
        
        community_results = await self.community.run(question.question_text, research, current_date, schema, parent_ids=parent_ids)
        
        # Aggregate using AgenticConsensus (intelligent weighted consensus)
        if not community_results:
             logger.warning("No valid predictions from community. Falling back to legacy single-LLM forecast.")
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

        # Use AgenticConsensus with full researcher outputs for intelligent weighting
        if isinstance(self.consensus, AgenticConsensus):
            # Extract researcher node IDs for graph linking
            researcher_node_ids = [res.get("last_node_id") for res in community_results if res.get("last_node_id")]
            consensus_result = await self.consensus.aggregate_async(
                community_results, question.question_text, schema, current_date,
                parent_ids=researcher_node_ids
            )
            aggregated_prediction = consensus_result["prediction"]
        else:
            # Fallback for statistical consensus
            predictions = [res["prediction"] for res in community_results if "prediction" in res]
            aggregated_prediction = self.consensus.aggregate(predictions)
        
        # Format for ForecastBot
        predicted_options = []
        for option, prob in aggregated_prediction.items():
            if option in question.options:
                predicted_options.append((option, prob))
        
        # Normalize if needed (MeanConsensus should handle it but good to be safe)
        total_prob = sum(p for _, p in predicted_options)
        if total_prob > 0:
            predicted_options = [(o, p/total_prob) for o, p in predicted_options]
            
        predicted_options_objects = []
        for option, prob in predicted_options:
             predicted_options_objects.append(PredictedOption(option_name=option, probability=prob))
            
        prediction_list = PredictedOptionList(predicted_options=predicted_options_objects)
        
        # Summary
        full_report = f"Aggregated Prediction: {aggregated_prediction}\n\n"
        for res in community_results:
            full_report += f"Agent {res.get('agent_id', '?')} Analysis:\n{res.get('analysis', 'No analysis')}\nPrediction: {res.get('prediction')}\n\n"
            
        summary = await self._summarize_report(full_report)
        
        return ReasonedPrediction(
            prediction_value=prediction_list, reasoning=summary
        ), {
            "community_results": community_results,
            "consensus_result": consensus_result,
        }

    async def _run_forecast_on_numeric(
        self, question: NumericQuestion, research: str
    ) -> ReasonedPrediction[NumericDistribution]:
        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Schema for Numeric
        schema = {
            "schema_type": "Numeric",
            "description": "Define a function predict() -> Dict[str, float] with keys 'p10', 'p50', 'p90' representing the 10th, 50th, and 90th percentiles."
        }
        
        # Retrieve parent_ids from notepad
        notepad = await self._get_notepad(question)
        parent_ids = notepad.note_entries.get("parent_ids", [])
        
        community_results = await self.community.run(question.question_text, research, current_date, schema, parent_ids=parent_ids)
        
        # Aggregate using AgenticConsensus (intelligent weighted consensus)
        if not community_results:
             logger.warning("No valid predictions from community. Falling back to legacy single-LLM forecast.")
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

        # Use AgenticConsensus with full researcher outputs for intelligent weighting
        if isinstance(self.consensus, AgenticConsensus):
            # Extract researcher node IDs for graph linking
            researcher_node_ids = [res.get("last_node_id") for res in community_results if res.get("last_node_id")]
            consensus_result = await self.consensus.aggregate_async(
                community_results, question.question_text, schema, current_date,
                parent_ids=researcher_node_ids
            )
            aggregated_prediction = consensus_result["prediction"]
        else:
            # Fallback for statistical consensus
            predictions = [res["prediction"] for res in community_results if "prediction" in res]
            aggregated_prediction = self.consensus.aggregate(predictions)
        
        # Convert to Percentile list
        percentiles = []
        for key, val in aggregated_prediction.items():
            if key.startswith('p'):
                try:
                    p_val = int(key[1:])
                    percentiles.append(Percentile(value=val, percentile=p_val/100.0))
                except:
                    pass
        
        # Ensure we have enough data for a distribution, otherwise fallback
        if not percentiles:
             # Fallback if community fails to return valid percentiles
             logger.warning("Community returned invalid percentiles. Falling back to legacy.")
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
             
        prediction = NumericDistribution.from_question(percentiles, question)
        
        # Summary
        full_report = f"Aggregated Prediction: {aggregated_prediction}\n\n"
        for res in community_results:
            full_report += f"Agent {res.get('agent_id', '?')} Analysis:\n{res.get('analysis', 'No analysis')}\nPrediction: {res.get('prediction')}\n\n"
            
        summary = await self._summarize_report(full_report)
        
        return ReasonedPrediction(prediction_value=prediction, reasoning=summary)


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
        choices=["tournament", "metaculus_cup", "test_questions", "local_test"],
        default="tournament",
        help="Specify the run mode (default: tournament)",
    )
    args = parser.parse_args()
    run_mode: Literal["tournament", "metaculus_cup", "test_questions", "local_test"] = args.mode
    
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
            "https://www.metaculus.com/questions/40959/top-netflix-views-in-christmas-week-2025/"
        ]
        bot.skip_previously_forecasted_questions = False
        questions = [
            MetaculusApi.get_question_by_url(question_url)
            for question_url in EXAMPLE_QUESTIONS
        ]
        forecast_reports = asyncio.run(
            bot.forecast_questions(questions, return_exceptions=True)
        )
    elif run_mode == "local_test":
        # Local test mode without Metaculus API
        logger.info("!!FORECAST")
        
        question_text = "What will the Fed decision in January 2026 be?"
        question = MultipleChoiceQuestion(
            question_text=question_text,
            options = ["Fed maintains rate", "Cut 25bps", "Cut >25bps", "Hike 25bps", "Hike >25bps"],
            background_info = """The Federal Open Market Committee (FOMC) sets U.S. monetary policy, including the target range for the federal funds rate. The January 2026 FOMC meeting is scheduled for Jan 27–28, 2026, and the Committee typically releases its policy statement at 2:00 p.m. ET on the second day.

This question is about the size of the rate *hike* or *cut decided at that January 2026 meeting, measured in basis points (bps), where 25 bps = 0.25 percentage points. In the associated Kalshi event, the outcomes are bucketed into Fed maintains rate, Cut 25bps, Cut >25bps, Hike 25bps, Hike >25bps with outcomes verified from the Federal Reserve.""",
            resolution_criteria="""This question resolves to exactly one of the following outcomes based on the Federal Reserve System’s documented decision for the specified <meeting> (January 28, 2026), as of the contract’s Expiration Date/Expiration Time:

- "Fed maintains rate" if the FOMC makes **no change** to the target federal funds rate range.
- "Cut 25bps" if the FOMC **cuts** (reduces) the target range by **exactly 25 basis points (0.25%)**.
- "Cut >25bps" if the FOMC **cuts** the target range by **more than 25 basis points**.
- "Hike 25bps" if the FOMC **hikes** (raises) the target range by **exactly 25 basis points (0.25%)**.
- "Hike >25bps" if the FOMC **hikes** the target range by **more than 25 basis points**.

Contingency: If the Federal Reserve cancels the target meeting, then "Fed maintains rate" is the winning outcome and all other outcomes are not.""",
            fine_print = """Mutual exclusivity: only one outcome/bucket can be the winner.

Trading/expiration mechanics per FEDDECISION: Last Trading Time is 1:55 PM ET on the market’s specified Last Trading Date. Expiration Time is 2:05 PM ET, and Expiration Date is the sooner of (i) the first 2:05 PM ET following the release of a decision for <meeting> or (ii) three months after <date> (as defined by the iteration). The Expiration Value is the value of the Underlying as documented by the Federal Reserve System at Expiration time.""",
        )
        
        async def run_local():
            # Initialize Notepad manually for local test
            notepad = await bot._initialize_notepad(question)
            async with bot._note_pad_lock:
                bot._note_pads.append(notepad)
            
            try:
                # 1. Research
                research = await bot.run_research(question)
                print("\n\n[LOCAL TEST] Research Completed:\n", research[:500], "...\n")
                
                # 2. Forecast
                prediction, metadata = await bot._run_forecast_on_multiple_choice(question, research)
                print("\n\n[LOCAL TEST] Prediction Generated:")
                print(f"Prediction: {prediction.prediction_value}")
                print("Reasoning:", prediction.reasoning[:200], "...")

                # generate report
                report = await bot._generate_report(
                    question=question,
                    research_context=research,
                    researcher_outputs=metadata["community_results"],
                    consensus_output=metadata["consensus_result"],
                    supervisor_critique="",
                    current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                print("\n\n[LOCAL TEST] Report Generated:")
                print(report[:500], "...")
            finally:
                await bot._remove_notepad(question)
            
            return [] # No reports to log

        forecast_reports = asyncio.run(run_local())
    
    bot.log_report_summary(forecast_reports)
