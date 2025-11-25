import json
import sys

def load_events(filepath):
    events = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events

def build_graph(events):
    nodes = []
    edges = []
    
    # Trackers
    last_main_node_id = None
    current_search_node_ids = []
    
    for i, event in enumerate(events):
        event_type = event.get('event_type')
        source = event.get('source')
        node_id = i
        
        nodes.append({
            'id': node_id,
            'type': event_type,
            'source': source,
            'timestamp': event.get('timestamp')
        })
        
        # Logic
        if event_type == 'search_result':
            # Fan-out: Connect from last main node (Reasoning)
            if last_main_node_id is not None:
                edges.append((last_main_node_id, node_id))
            else:
                print(f"WARNING: Orphan SearchResult at index {i}")
            
            current_search_node_ids.append(node_id)
            
        elif event_type in ['reasoning', 'analysis', 'review', 'prediction', 'summary']:
            # Fan-in: Connect from previous search results OR previous main node
            if current_search_node_ids:
                for s_id in current_search_node_ids:
                    edges.append((s_id, node_id))
                current_search_node_ids = [] # Reset after consuming
            elif last_main_node_id is not None:
                edges.append((last_main_node_id, node_id))
            
            last_main_node_id = node_id
            
    return nodes, edges

def validate_graph(nodes, edges):
    print(f"Total Nodes: {len(nodes)}")
    print(f"Total Edges: {len(edges)}")
    
    # Build adjacency
    adj = {n['id']: [] for n in nodes}
    in_degree = {n['id']: 0 for n in nodes}
    
    for u, v in edges:
        adj[u].append(v)
        in_degree[v] += 1
        
    # Check for orphans (except start)
    orphans = [n for n in nodes if in_degree[n['id']] == 0 and n['id'] != 0]
    if orphans:
        print(f"\nPotential Orphans (In-degree 0, excluding start):")
        for o in orphans:
            print(f"  ID {o['id']}: {o['type']} ({o['source']})")
            
    # Check for disconnected components (simple BFS from 0)
    visited = set()
    queue = [0]
    while queue:
        curr = queue.pop(0)
        visited.add(curr)
        for neighbor in adj[curr]:
            if neighbor not in visited:
                queue.append(neighbor)
                
    unreachable = [n for n in nodes if n['id'] not in visited]
    if unreachable:
        print(f"\nUnreachable Nodes (from start):")
        for u in unreachable:
            print(f"  ID {u['id']}: {u['type']} ({u['source']})")
    else:
        print("\nGraph is fully connected from start node.")

    # Print a snippet of the flow
    print("\nGraph Flow Snippet (first 20 edges):")
    for u, v in edges[:20]:
        u_node = nodes[u]
        v_node = nodes[v]
        print(f"  {u_node['type']}({u}) -> {v_node['type']}({v})")

if __name__ == "__main__":
    events = load_events('/Users/atharvapandey/Kairosity/kairosity_bot_final/logs/run_20251125_023217/events.jsonl')
    nodes, edges = build_graph(events)
    validate_graph(nodes, edges)
