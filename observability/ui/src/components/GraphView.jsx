import React, { useMemo, useCallback } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

const nodeTypes = {}; // Default nodes for now

const GraphView = ({ events, onNodeClick }) => {
    // Transform events into nodes and edges
    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        const nodes = [];
        const edges = [];
        let yOffset = 0;
        const xOffset = 250;

        // Simple vertical layout for now
        events.forEach((event, index) => {
            const id = `node-${index}`;
            const type = event.event_type || 'unknown';
            const source = event.source || 'System';

            let label = `${source}: ${type}`;
            let color = '#27272a'; // Default gray

            if (type === 'reasoning') color = '#3b82f6'; // Blue
            if (type === 'search_result') color = '#10b981'; // Green
            if (type === 'summary') color = '#8b5cf6'; // Purple
            if (type === 'error') color = '#ef4444'; // Red

            nodes.push({
                id,
                position: { x: xOffset, y: yOffset },
                data: { label, event },
                style: {
                    border: `1px solid ${color}`,
                    borderLeft: `4px solid ${color}`,
                    padding: '10px',
                    width: 200,
                    fontSize: '12px',
                    background: '#18181b',
                    color: '#e4e4e7',
                    borderRadius: '8px'
                },
            });

            if (index > 0) {
                edges.push({
                    id: `edge-${index - 1}-${index}`,
                    source: `node-${index - 1}`,
                    target: id,
                    type: 'smoothstep',
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#52525b' },
                    style: { stroke: '#52525b' }
                });
            }

            yOffset += 100;
        });

        return { nodes, edges };
    }, [events]);

    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    // Update nodes when events change
    React.useEffect(() => {
        setNodes(initialNodes);
        setEdges(initialEdges);
    }, [initialNodes, initialEdges, setNodes, setEdges]);

    const onNodeClickCallback = useCallback((_, node) => {
        onNodeClick(node.data.event);
    }, [onNodeClick]);

    return (
        <div className="w-full h-full">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClickCallback}
                fitView
                attributionPosition="bottom-right"
            >
                <Background color="#27272a" gap={16} />
                <Controls className="bg-surface border-gray-800 fill-gray-400" />
                <MiniMap
                    nodeStrokeColor={(n) => {
                        if (n.style?.background) return n.style.background;
                        return '#eee';
                    }}
                    nodeColor={(n) => {
                        if (n.style?.background) return n.style.background;
                        return '#fff';
                    }}
                    maskColor="rgba(0, 0, 0, 0.7)"
                    className="bg-surface border border-gray-800"
                />
            </ReactFlow>
        </div>
    );
};

export default GraphView;
