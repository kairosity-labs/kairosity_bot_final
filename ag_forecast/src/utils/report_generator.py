import json
from pathlib import Path
from typing import List, Dict, Any

class ReportGenerator:
    def __init__(self, run_dir: str):
        self.run_dir = Path(run_dir)
        self.events_file = self.run_dir / "events.jsonl"
        self.report_file = self.run_dir / "report.md"

    def generate(self):
        """Generate a markdown report from the events log."""
        if not self.events_file.exists():
            print(f"No events file found at {self.events_file}")
            return

        events = []
        with open(self.events_file, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))

        report_content = self._build_report(events)
        
        with open(self.report_file, 'w') as f:
            f.write(report_content)
        
        print(f"Report generated at: {self.report_file}")

    def _build_report(self, events: List[Dict[str, Any]]) -> str:
        md = "# Forecasting Execution Report\n\n"
        
        # 1. Executive Summary
        md += "## Executive Summary\n"
        summary_event = next((e for e in events if e["event_type"] == "summary"), None)
        if summary_event:
            md += f"**Initial Retrieval Summary**:\n{summary_event['output']}\n\n"
        
        # 2. Chronological Trace
        md += "## Execution Trace\n"
        
        for event in events:
            timestamp = event["timestamp"].split("T")[1][:8]
            source = event["source"]
            e_type = event["event_type"]
            
            if e_type == "reasoning":
                md += f"### [{timestamp}] {source}: Reasoning\n"
                md += f"**Round**: {event['input']['round']}\n"
                md += f"**Reasoning**: {event['output']['reasoning']}\n\n"
            
            elif e_type == "search_result":
                md += f"### [{timestamp}] {source}: Search\n"
                md += f"**Query**: {event['input']['query']}\n"
                md += f"**Source**: {event['input']['source']}\n"
                md += f"**Results**:\n"
                for item in event['output']:
                    md += f"- {item.get('content', '')}\n\n"
                md += "\n"
            
            elif e_type == "analysis":
                md += f"### [{timestamp}] {source}: Analysis\n"
                md += f"**Query**: {event['input']['query']}\n"
                md += f"**Analysis**: {event['output']['analysis']}\n\n"
            
            elif e_type == "review":
                md += f"### [{timestamp}] {source}: Supervisor Review\n"
                md += f"**Critique**: {event['output']['critique']}\n"
                md += f"**Decision**: {'Sufficient' if event['output']['is_sufficient'] else 'Need more info'}\n"
                if not event['output']['is_sufficient']:
                    md += "**Sub-queries**:\n"
                    for q in event['output']['sub_queries']:
                        md += f"- {q['query']} ({q['rationale']})\n"
                md += "\n"
            
            elif e_type == "schema_definition":
                md += f"### [{timestamp}] {source}: Schema Definition\n"
                md += f"**Type**: {event['output']['schema_type']}\n"
                md += f"**Options**: {event['output']['options']}\n\n"
            
            elif e_type == "prediction":
                md += f"### [{timestamp}] {source}: Prediction\n"
                md += f"**Prediction**: {event['output']['prediction']}\n"
                md += f"**Analysis**: {event['output']['analysis']}\n"
                if "code" in event['output']:
                    md += f"**Code**:\n```python\n{event['output']['code']}\n```\n"
                md += "\n"

            elif e_type == "final_forecast":
                md += "## Final Forecast\n"
                md += f"**Consensus Prediction**: {event['output']['prediction']}\n\n"

        return md

