import json
import sys
from datetime import datetime

def load_events(filepath):
    events = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        sys.exit(1)
    return events

def parse_timestamp(ts_str):
    # Adjust format if needed based on actual log format
    # Example: "2025-11-25 02:32:30,191" or ISO format
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
    except ValueError:
        try:
             return datetime.fromisoformat(ts_str)
        except:
            return None

def validate_constraints(events):
    print(f"Validating {len(events)} events...")
    
    nodes = []
    edges = []
    
    # Trackers
    last_reasoning_node = None
    last_analysis_node = None
    last_supervisor_node = None
    
    orphans = []
    causality_violations = []
    
    for i, event in enumerate(events):
        event_type = event.get('event_type')
        timestamp = parse_timestamp(event.get('timestamp'))
        
        node = {
            'id': i,
            'type': event_type,
            'timestamp': timestamp,
            'event': event
        }
        nodes.append(node)
        
        # --- Logic ---
        
        if event_type == 'reasoning':
            last_reasoning_node = node
            # Connect from previous step (Supervisor or Analysis)
            if last_supervisor_node:
                if last_supervisor_node['timestamp'] and timestamp and last_supervisor_node['timestamp'] > timestamp:
                    causality_violations.append((last_supervisor_node['id'], i, "Supervisor -> Reasoning"))
                last_supervisor_node = None
            elif last_analysis_node:
                 if last_analysis_node['timestamp'] and timestamp and last_analysis_node['timestamp'] > timestamp:
                    causality_violations.append((last_analysis_node['id'], i, "Analysis -> Reasoning"))

        elif event_type == 'search_result':
            # MUST have a parent
            parent = None
            
            # 1. Try strict query match
            query = event.get('input', {}).get('query')
            if last_reasoning_node:
                # Check if query is in last reasoning output
                reasoning_queries = [q['query'] for q in last_reasoning_node['event'].get('output', {}).get('search_queries', [])]
                if query in reasoning_queries:
                    parent = last_reasoning_node
                else:
                    # 2. Fallback: Time-based (Reasoning must be before Search)
                    if last_reasoning_node['timestamp'] and timestamp and last_reasoning_node['timestamp'] <= timestamp:
                         parent = last_reasoning_node
                         # print(f"Warning: Fuzzy match for search result {i} to reasoning {parent['id']}")
            
            if parent:
                if parent['timestamp'] and timestamp and parent['timestamp'] > timestamp:
                     causality_violations.append((parent['id'], i, "Reasoning -> Search"))
            else:
                orphans.append(i)

        elif event_type in ['analysis', 'summary']:
            last_analysis_node = node
            # Logic for connecting search results (omitted for brevity, focusing on orphans)
            
        elif event_type == 'review':
            last_supervisor_node = node

    # Report
    print("\n--- Validation Results ---")
    if orphans:
        print(f"FAILED: Found {len(orphans)} orphan search results!")
        for o_id in orphans:
            print(f"  - Node {o_id} (Search Result): No parent found.")
    else:
        print("SUCCESS: No orphan search results found.")
        
    if causality_violations:
        print(f"FAILED: Found {len(causality_violations)} causality violations (Future -> Past)!")
        for u, v, desc in causality_violations:
            print(f"  - Edge {u} -> {v} ({desc}) violates causality.")
    else:
        print("SUCCESS: No causality violations found.")

if __name__ == "__main__":
    # Use the path found in previous step
    events = load_events('/Users/atharvapandey/Kairosity/kairosity_bot_final/logs/run_20251125_023217/events.jsonl')
    validate_constraints(events)
