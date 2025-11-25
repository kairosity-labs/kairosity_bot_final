// Build workflow hierarchy with refined grouping logic
export function buildWorkflowHierarchy(events) {
    if (!events || events.length === 0) return [];

    const stages = [];

    // Stage 1: Research & Iteration
    const researchStage = {
        id: 'research',
        name: 'Research & Iteration',
        type: 'research',
        rounds: [],
        startTime: null,
        endTime: null
    };

    // Stage 2: Community Forecasting
    const communityStage = {
        id: 'community',
        name: 'Community Forecasting',
        type: 'community',
        researchers: [],
        startTime: null,
        endTime: null
    };

    // Stage 3: Final Output
    const consensusStage = {
        id: 'consensus',
        name: 'Final Output',
        type: 'consensus',
        events: [],
        startTime: null,
        endTime: null
    };

    let currentRetrievalRound = null;
    let currentAnalysisRound = null;

    events.forEach((event, index) => {
        const source = event.source;
        const eventType = event.event_type;
        const roundNum = event.input?.round || 1; // Default to 1 if missing

        // Research Stage Logic
        if (source === 'AgenticRetrieval' || source === 'AnalystAgent' || source === 'SupervisorAgent') {
            if (!researchStage.startTime) researchStage.startTime = event.timestamp;
            researchStage.endTime = event.timestamp;

            // Determine Round Type
            if (source === 'AgenticRetrieval') {
                // Start or continue Retrieval Round
                if (!currentRetrievalRound || currentRetrievalRound.number !== roundNum) {
                    currentRetrievalRound = {
                        id: `retrieval-${roundNum}`,
                        type: 'retrieval',
                        number: roundNum,
                        name: `Retrieval Round ${roundNum}`,
                        events: [],
                        startTime: event.timestamp,
                        endTime: event.timestamp
                    };
                    researchStage.rounds.push(currentRetrievalRound);
                    currentAnalysisRound = null; // Reset analysis round
                }
                currentRetrievalRound.events.push({ ...event, _index: index });
                currentRetrievalRound.endTime = event.timestamp;
            }
            else if (source === 'AnalystAgent' || source === 'SupervisorAgent') {
                // Start or continue Analysis Round
                // Analysis rounds usually follow retrieval rounds of the same number
                if (!currentAnalysisRound || currentAnalysisRound.number !== roundNum) {
                    currentAnalysisRound = {
                        id: `analysis-${roundNum}`,
                        type: 'analysis',
                        number: roundNum,
                        name: `Analysis Round ${roundNum}`,
                        events: [],
                        startTime: event.timestamp,
                        endTime: event.timestamp
                    };
                    researchStage.rounds.push(currentAnalysisRound);
                    currentRetrievalRound = null; // Reset retrieval round
                }
                currentAnalysisRound.events.push({ ...event, _index: index });
                currentAnalysisRound.endTime = event.timestamp;
            }
        }
        // Community Stage Logic
        else if (source.includes('Researcher') || source === 'Community') {
            if (!communityStage.startTime) communityStage.startTime = event.timestamp;
            communityStage.endTime = event.timestamp;

            let researcher = communityStage.researchers.find(r => r.name === source);
            if (!researcher) {
                researcher = {
                    name: source,
                    events: []
                };
                communityStage.researchers.push(researcher);
            }
            researcher.events.push({ ...event, _index: index });
        }
        // Consensus Stage Logic
        else {
            if (!consensusStage.startTime) consensusStage.startTime = event.timestamp;
            consensusStage.endTime = event.timestamp;
            consensusStage.events.push({ ...event, _index: index });
        }
    });

    // Sort community researchers' events
    communityStage.researchers.forEach(researcher => {
        researcher.events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    });

    // Sort consensus events
    consensusStage.events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    // Add stages if populated
    if (researchStage.rounds.length > 0) stages.push(researchStage);
    if (communityStage.researchers.length > 0) stages.push(communityStage);
    if (consensusStage.events.length > 0) stages.push(consensusStage);

    return stages;
}

// Build Graph Data (Nodes & Edges) from Events with Strict Phase Logic
// Build Graph Data (Nodes & Edges) from Events with Explicit Parent IDs (V5)
export function buildGraphData(events) {
    const nodes = [];
    const edges = [];

    events.forEach((event, index) => {
        const nodeId = index.toString();
        const type = event.event_type;
        const source = event.source;

        let label = type.replace('_', ' ');
        if (source.includes('Researcher')) label = `${source.split(' ')[0]} ${label}`;
        if (type === 'reasoning') label = `Reasoning (R${event.input?.round || '?'})`;

        // Create Node
        nodes.push({
            id: nodeId,
            type: 'custom',
            data: {
                label: label,
                type: type,
                source: source,
                timestamp: event.timestamp,
                event: event
            },
            position: { x: 0, y: 0 }
        });

        // Create Edges from Explicit Parent IDs
        if (event.parent_ids && Array.isArray(event.parent_ids)) {
            event.parent_ids.forEach(parentId => {
                const pId = parentId.toString();

                // Prevent self-loops or invalid edges just in case
                if (pId !== nodeId) {
                    edges.push({
                        id: `e${pId}-${nodeId}`,
                        source: pId,
                        target: nodeId,
                        type: 'smoothstep',
                        animated: true
                    });
                }
            });
        }
    });

    return { nodes, edges };
}
