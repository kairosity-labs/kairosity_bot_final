
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Literal, Dict, Any, List, Set

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from main import AGForecastBot, GeneralLlm
from forecasting_tools import (
    BinaryQuestion,
    MultipleChoiceQuestion,
    NumericQuestion,
    MetaculusQuestion
)
from forecasting_tools import structure_output, clean_indents

# Retrieve API Key
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    # Try to load from .env if not present
    from dotenv import load_dotenv
    load_dotenv()
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        raise ValueError("OPENROUTER_API_KEY must be set in environment variables.")

# Global Bot Instance and Task Tracking
bot: AGForecastBot = None
running_tasks: Set[asyncio.Task] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    logging.info("Initializing AGForecastBot...")
    bot = AGForecastBot(
        openrouter_api_key=openrouter_key,
        research_reports_per_question=1,
        predictions_per_research_report=1,
        use_research_summary_to_forecast=False,
        publish_reports_to_metaculus=False, # Don't publish for API calls
        folder_to_save_reports_to="logs/reports",
        skip_previously_forecasted_questions=False,
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
    logging.info("AGForecastBot initialized.")
    yield
    logging.info("Shutting down...")
    
    # Cancel all running tasks
    if running_tasks:
        logging.info(f"Cancelling {len(running_tasks)} active tasks...")
        for task in running_tasks:
            task.cancel()
        
        await asyncio.gather(*running_tasks, return_exceptions=True)
        logging.info("All tasks cancelled.")

app = FastAPI(lifespan=lifespan)

# --- Pydantic Models ---

class ForecastRequest(BaseModel):
    question_text: str
    resolution_criteria: str
    background_info: str = ""
    fine_print: str = ""

class QuestionClassification(BaseModel):
    classification: Literal["binary", "multiple_choice", "numeric"]
    options: List[str] = Field(default=[], description="List of options for multiple choice questions.")
    upper_bound: float | None = Field(default=None, description="Upper bound for numeric questions.")
    lower_bound: float | None = Field(default=None, description="Lower bound for numeric questions.")
    open_upper_bound: bool = Field(default=False)
    open_lower_bound: bool = Field(default=False)
    zero_point: float | None = Field(default=None)

class ForecastResponse(BaseModel):
    prediction: Any
    report: str
    classification: QuestionClassification

# --- Helper Functions ---

async def classify_question(request: ForecastRequest) -> QuestionClassification:
    """
    Classifies the question text and extracts metadata using the bot's LLM.
    """
    prompt = clean_indents(
        f"""
        You are an expert at classifying forecasting questions.
        
        Analyze the following question and determines its type and properties.
        
        Question: {request.question_text}
        
        Resolution Criteria:
        {request.resolution_criteria}
        
        Classify into one of: 'binary', 'multiple_choice', 'numeric'.
        
        - If 'multiple_choice', you MUST extract the list of strings for 'options'.
        - If 'numeric', you MUST extract 'upper_bound' and 'lower_bound'.
        - 'binary' means a simple Yes/No probability.
        """
    )
    
    llm = bot.get_llm("default", "llm")
    parser = bot.get_llm("parser", "llm")
    
    # Generate the raw classification text
    raw_response = await llm.invoke(prompt)
    
    # Parse the response
    classification: QuestionClassification = await structure_output(
        raw_response, QuestionClassification, model=parser
    )
    return classification

async def run_forecast_logic(request: ForecastRequest):
    # 1. Classify
    classification = await classify_question(request)
    
    # 2. Instantiate Question Object
    question: MetaculusQuestion = None
    
    if classification.classification == "binary":
        question = BinaryQuestion(
            question_text=request.question_text,
            resolution_criteria=request.resolution_criteria,
            background_info=request.background_info,
            fine_print=request.fine_print
        )
    elif classification.classification == "multiple_choice":
        if not classification.options:
            raise HTTPException(status_code=400, detail="Options could not be extracted for multiple choice question.")
        question = MultipleChoiceQuestion(
            question_text=request.question_text,
            options=classification.options,
            resolution_criteria=request.resolution_criteria,
            background_info=request.background_info,
            fine_print=request.fine_print
        )
    elif classification.classification == "numeric":
        if classification.upper_bound is None or classification.lower_bound is None:
             raise HTTPException(status_code=400, detail="Bounds could not be extracted for numeric question.")
        question = NumericQuestion(
            question_text=request.question_text,
            upper_bound=classification.upper_bound,
            lower_bound=classification.lower_bound,
            open_upper_bound=classification.open_upper_bound,
            open_lower_bound=classification.open_lower_bound,
            zero_point=classification.zero_point,
            resolution_criteria=request.resolution_criteria,
            background_info=request.background_info,
            fine_print=request.fine_print
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown classification: {classification.classification}")

    # 3. Forecast Workflow
    # Initialize Notepad manually as we are not using the standard loop
    notepad = await bot._initialize_notepad(question)
    async with bot._note_pad_lock:
        bot._note_pads.append(notepad)
        
    try:
        # Research
        research_context = await bot.run_research(question)
        
        # Forecast
        prediction_obj, metadata = await {
            "binary": bot._run_forecast_on_binary,
            "multiple_choice": bot._run_forecast_on_multiple_choice,
            "numeric": bot._run_forecast_on_numeric
        }[classification.classification](question, research_context)
        
        # Note: bot._run_forecast_on_binary returns just the prediction_obj, 
        # while others return (prediction_obj, metadata). We need to handle this.
        # Wait, checking main.py...
        # _run_forecast_on_binary returns ReasonedPrediction
        # _run_forecast_on_multiple_choice returns ReasonedPrediction, metadata (tuple)
        
        # Let's fix the unpacking
        forecast_result = await {
             "binary": bot._run_forecast_on_binary,
             "multiple_choice": bot._run_forecast_on_multiple_choice,
             "numeric": bot._run_forecast_on_numeric
        }[classification.classification](question, research_context)
        
        if isinstance(forecast_result, tuple):
             prediction_obj, metadata = forecast_result
        else:
             prediction_obj = forecast_result
             metadata = {"community_results": [], "consensus_result": {}} # Default empty

        # Generate Report
        report = await bot._generate_report(
            question=question,
            research_context=research_context,
            researcher_outputs=metadata.get("community_results", []),
            consensus_output=metadata.get("consensus_result", {}),
            supervisor_critique="",
        )
        
        return ForecastResponse(
            prediction=prediction_obj.prediction_value,
            report=report,
            classification=classification
        )

    finally:
        await bot._remove_notepad(question)


# --- Endpoints ---

@app.post("/forecast", response_model=ForecastResponse)
async def forecast_endpoint(request: ForecastRequest):
    loop = asyncio.get_running_loop()
    # Create a task for the logic so we can track it
    task = loop.create_task(run_forecast_logic(request))
    running_tasks.add(task)
    try:
        return await task
    except asyncio.CancelledError:
        logging.info("Forecast request cancelled.")
        raise HTTPException(status_code=503, detail="Service shutting down or request cancelled.")
    except Exception as e:
        logging.error(f"Error processing forecast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        running_tasks.discard(task)
