// GraphRAG Visualization JavaScript

// Global state
let currentGraphData = { nodes: [], links: [] };
let simulation = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeGraph();
    loadGraphStats();
});

// Submit query
async function submitQuery() {
    const queryInput = document.getElementById('query-input');
    const query = queryInput.value.trim();
    
    if (!query) {
        alert('Please enter a question');
        return;
    }
    
    const searchBtn = document.getElementById('search-btn');
    const searchIcon = document.getElementById('search-icon');
    const searchText = document.getElementById('search-text');
    
    // Show loading state
    searchBtn.classList.add('loading');
    searchBtn.disabled = true;
    searchIcon.innerHTML = '<span class="spinner"></span>';
    searchText.textContent = 'Searching...';
    
    try {
        const maxDepth = parseInt(document.getElementById('max-depth').value);
        const topK = parseInt(document.getElementById('top-k').value);
        
        const response = await fetch('/api/query/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                max_depth: maxDepth,
                top_k: topK
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update UI with results
        displayAnswer(data.answer);
        displaySources(data.sources);
        displayContextNodes(data.context_nodes);
        visualizeGraph(data.context_nodes, data.relationships);
        
    } catch (error) {
        console.error('Query error:', error);
        displayAnswer(`Error: ${error.message}`);
    } finally {
        // Reset button state
        searchBtn.classList.remove('loading');
        searchBtn.disabled = false;
        searchIcon.textContent = '🔍';
        searchText.textContent = 'Search';
    }
}

// Display answer
function displayAnswer(answer) {
    const answerBox = document.getElementById('answer-text');
    answerBox.innerHTML = `<p>${answer}</p>`;
    answerBox.classList.add('fade-in');
}

// Display sources
function displaySources(sources) {
    const sourcesSection = document.getElementById('sources-section');
    const sourcesList = document.getElementById('sources-list');
    
    if (sources && sources.length > 0) {
        sourcesList.innerHTML = sources
            .map(source => `<span class="source-tag">${source}</span>`)
            .join('');
        sourcesSection.style.display = 'block';
    } else {
        sourcesSection.style.display = 'none';
    }
}

// Display context nodes
function displayContextNodes(nodes) {
    const contextContainer = document.getElementById('context-nodes');
    
    if (!nodes || nodes.length === 0) {
        contextContainer.innerHTML = '<p class="placeholder">No context nodes found</p>';
        return;
    }
    
    contextContainer.innerHTML = nodes.map(node => createNodeCardHTML(node)).join('');
}

// Create node card HTML
function createNodeCardHTML(node) {
    const label = node.labels && node.labels.length > 0 ? node.labels[0] : 'Node';
    const properties = node.properties || {};
    const title = properties.name || properties.title || properties.id || 'Unknown';
    const score = node.score ? node.score.toFixed(2) : null;
    
    let propertiesHTML = '';
    for (const [key, value] of Object.entries(properties)) {
        if (['id', 'name', 'title', 'embedding', 'text'].includes(key) || !value) continue;
        
        const displayValue = typeof value === 'string' && value.length > 100 
            ? value.substring(0, 100) + '...' 
            : value;
        
        propertiesHTML += `
            <div class="property">
                <strong>${key}:</strong> ${displayValue}
            </div>
        `;
    }
    
    const textContent = properties.text ? `
        <div class="node-text">
            <details>
                <summary>View text content</summary>
                <p>${properties.text}</p>
            </details>
        </div>
    ` : '';
    
    return `
        <div class="node-card" data-node-id="${node.id}">
            <div class="node-header">
                <span class="node-label ${label.toLowerCase()}">${label}</span>
                ${score ? `<span class="node-score">${score}</span>` : ''}
            </div>
            <div class="node-body">
                <h4>${title}</h4>
                <div class="node-properties">
                    ${propertiesHTML}
                </div>
                ${textContent}
            </div>
        </div>
    `;
}

// Initialize graph visualization
function initializeGraph() {
    const svg = d3.select('#graph-svg');
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg.attr('width', width).attr('height', height);
    
    // Add zoom behavior
    const g = svg.append('g');
    
    svg.call(d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        }));
    
    // Create arrow markers for directed edges
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 25)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
        .attr('fill', '#999')
        .style('stroke', 'none');
}

// Visualize graph
function visualizeGraph(nodes, relationships) {
    if (!nodes || nodes.length === 0) {
        return;
    }
    
    const svg = d3.select('#graph-svg');
    const g = svg.select('g');
    g.selectAll('*').remove();
    
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Transform data
    const graphData = {
        nodes: nodes.map(n => ({
            id: n.id,
            label: n.labels && n.labels.length > 0 ? n.labels[0] : 'Node',
            name: n.properties?.name || n.properties?.title || n.id,
            score: n.score || 0,
            ...n
        })),
        links: relationships.map(r => ({
            source: r.source,
            target: r.target,
            type: r.type,
            ...r
        }))
    };
    
    currentGraphData = graphData;
    
    // Color scale based on relevance score
    const colorScale = d3.scaleLinear()
        .domain([0, 0.5, 1])
        .range(['#9E9E9E', '#2196F3', '#4CAF50']);
    
    // Create force simulation
    simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links)
            .id(d => d.id)
            .distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));
    
    // Create links
    const link = g.append('g')
        .selectAll('line')
        .data(graphData.links)
        .enter()
        .append('line')
        .attr('class', 'link')
        .attr('marker-end', 'url(#arrowhead)');
    
    // Create link labels
    const linkLabel = g.append('g')
        .selectAll('text')
        .data(graphData.links)
        .enter()
        .append('text')
        .attr('class', 'link-label')
        .attr('text-anchor', 'middle')
        .text(d => d.type);
    
    // Create nodes
    const node = g.append('g')
        .selectAll('g')
        .data(graphData.nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));
    
    node.append('circle')
        .attr('r', d => 15 + (d.score || 0) * 10)
        .attr('fill', d => colorScale(d.score || 0));
    
    node.append('text')
        .attr('dy', 25)
        .text(d => {
            const name = d.name || '';
            return name.length > 15 ? name.substring(0, 15) + '...' : name;
        });
    
    // Add hover tooltip
    node.append('title')
        .text(d => `${d.label}: ${d.name}\nRelevance: ${(d.score || 0).toFixed(2)}`);
    
    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        linkLabel
            .attr('x', d => (d.source.x + d.target.x) / 2)
            .attr('y', d => (d.source.y + d.target.y) / 2);
        
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
    
    // Drag functions
    function dragStarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragEnded(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Load graph statistics
async function loadGraphStats() {
    try {
        const response = await fetch('/api/graph/stats');
        if (!response.ok) {
            throw new Error('Failed to load stats');
        }
        
        const stats = await response.json();
        displayGraphStats(stats);
        
    } catch (error) {
        console.error('Stats error:', error);
        document.getElementById('stats-content').innerHTML = 
            '<div class="stat-loading">Failed to load statistics</div>';
    }
}

// Display graph statistics
function displayGraphStats(stats) {
    const statsContainer = document.getElementById('stats-content');
    
    const html = `
        <div class="stat-item">
            <div class="stat-value">${stats.total_nodes}</div>
            <div class="stat-label">Nodes</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">${stats.total_relationships}</div>
            <div class="stat-label">Relationships</div>
        </div>
    `;
    
    statsContainer.innerHTML = html;
}

// Handle window resize
window.addEventListener('resize', () => {
    if (currentGraphData.nodes.length > 0) {
        visualizeGraph(currentGraphData.nodes, currentGraphData.links);
    }
});
