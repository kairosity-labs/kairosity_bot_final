import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any

class ForecastLogger:
    """Logger for forecasting bot with unique file per execution."""
    
    def __init__(self, base_dir: str = "logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create unique run directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.base_dir / f"run_{timestamp}"
        self.run_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.retrieval_dir = self.run_dir / "retrieval"
        self.retrieval_dir.mkdir(exist_ok=True)
        
        self.consensus_dir = self.run_dir / "consensus"
        self.consensus_dir.mkdir(exist_ok=True)
        
        self.code_dir = self.run_dir / "code"
        self.code_dir.mkdir(exist_ok=True)
        
        # Log files
        self.log_file = self.base_dir / f"forecast_{timestamp}.log"
        self.events_file = self.run_dir / "events.jsonl"
        
        # Setup logging
        self.logger = logging.getLogger("ForecastBot")
        self.logger.setLevel(logging.INFO)
        
        # File handler (human readable)
        fh = logging.FileHandler(self.log_file)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(ch)

    def log_event(self, source: str, event_type: str, input_data: Any = None, output_data: Any = None):
        """Log a structured event for the report generator."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "event_type": event_type,
            "input": input_data,
            "output": output_data
        }
        with open(self.events_file, 'a') as f:
            f.write(json.dumps(event) + "\n")

    def info(self, msg: str):
        self.logger.info(msg)
    
    def error(self, msg: str):
        """Log error message."""
        self.logger.error(msg)
    
    def section(self, title: str):
        """Log a major section header."""
        self.logger.info(f"\n{'='*80}\n  {title}\n{'='*80}")
    
    def subsection(self, title: str):
        """Log a subsection header."""
        separator = "-" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"  {title}")
        self.logger.info(separator)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def researcher(self, researcher_num: int, message: str):
        """Log researcher-specific message."""
        self.logger.info(f"[Researcher #{researcher_num}] {message}")
    
    def save_retrieval_data(self, query: str, retrieved_data: list, summary: str):
        """Save retrieval data to structured folder."""
        data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "retrieved_data": retrieved_data,
            "summary": summary,
            "sources": [item.get("source", "unknown") for item in retrieved_data]
        }
        
        file_path = self.retrieval_dir / "retrieval_data.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.info(f"Saved retrieval data to {file_path}")
    
    def save_query_data(self, round_num: int, query_num: int, query: str, source: str, response: dict):
        """Save individual query API call data."""
        data = {
            "round": round_num,
            "query_number": query_num,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "source": source,
            "response": response
        }
        
        file_path = self.retrieval_dir / f"round_{round_num}_query_{query_num}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def save_researcher_code(self, researcher_id: int, code: str, prediction: dict, analysis: str, followup_queries: list = None):
        """Save researcher's code and prediction."""
        data = {
            "researcher_id": researcher_id,
            "timestamp": datetime.now().isoformat(),
            "code": code,
            "prediction": prediction,
            "analysis": analysis,
            "followup_queries": followup_queries or []
        }
        
        file_path = self.code_dir / f"researcher_{researcher_id}_code.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Also save just the code as a .py file for easy viewing
        code_file = self.code_dir / f"researcher_{researcher_id}_model.py"
        with open(code_file, 'w') as f:
            f.write(code)
    
    def save_consensus_data(self, query: str, individual_predictions: list, aggregated_prediction: dict):
        """Save consensus aggregation data."""
        data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "individual_predictions": individual_predictions,
            "aggregated_prediction": aggregated_prediction,
            "num_researchers": len(individual_predictions)
        }
        
        file_path = self.consensus_dir / "consensus_data.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.info(f"Saved consensus data to {file_path}")
    
    def get_log_path(self) -> str:
        """Get the path to the current log file."""
        return str(self.log_file)
    
    def get_run_dir(self) -> str:
        """Get the path to the run directory."""
        return str(self.run_dir)

