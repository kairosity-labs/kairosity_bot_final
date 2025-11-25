import React, { useCallback, useEffect } from 'react';
import ReactFlow, {
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import CustomNode from './CustomNode';

const nodeTypes = { custom: CustomNode };

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    const nodeWidth = 180;
    const nodeHeight = 60;

    dagreGraph.setGraph({ rankdir: direction });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    nodes.forEach((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        node.targetPosition = 'top';
        node.sourcePosition = 'bottom';

        // We are shifting the dagre node position (anchor=center center) to the top left
        // so it matches the React Flow node anchor point (top left).
        node.position = {
            x: nodeWithPosition.x - nodeWidth / 2,
            y: nodeWithPosition.y - nodeHeight / 2,
        };

        return node;
    });

    return { nodes, edges };
};

const GraphView = ({ data, onNodeClick }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    useEffect(() => {
        if (data && data.nodes.length > 0) {
            const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
                data.nodes,
                data.edges
            );
            setNodes(layoutedNodes);
            setEdges(layoutedEdges);
        }
    }, [data, setNodes, setEdges]);

    const handleNodeClick = useCallback((event, node) => {
        // React Flow's onNodeClick provides (event, node)
        // We need to ensure we're passing the correct data up
        if (node && node.data && node.data.event) {
            onNodeClick(node.data.event);
        }
    }, [onNodeClick]);

    return (
        <div className="w-full h-full bg-[var(--bg-secondary)]">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={handleNodeClick}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-right"
                // Add these props to improve interactivity
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={true}
            >
                <Controls className="!bg-[var(--bg-card)] !border-[var(--border-subtle)] !fill-[var(--text-primary)]" />
                <Background color="#2d3748" gap={16} />
                <MiniMap
                    nodeColor={() => '#4a5568'}
                    maskColor="rgba(15, 20, 25, 0.7)"
                    className="!bg-[var(--bg-card)] !border-[var(--border-subtle)]"
                />
            </ReactFlow>
        </div>
    );
};

export default GraphView;
