from chunkFinder import chunkFinder
from graph_utils import colors2Community
from pyvis.network import Network
import networkx as nx
import pandas as pd


def create_graph_html_with_text(dfg1, script_path, graph_output_directory):
    G = nx.Graph()

    nodes = pd.concat([dfg1['node_1'], dfg1['node_2']], axis=0).unique()

    for node in nodes:
        G.add_node(str(node))

    for index, row in dfg1.iterrows():
        G.add_edge(
            str(row["node_1"]),
            str(row["node_2"]),
            title=row["edge"],  # Only show edge info when hovering over the edge
            weight=row['count'] / 4
        )
        G.edges[str(row["node_1"]), str(row["node_2"])]['original_text'] = row['original_text']  # Add original_text

    communities_generator = nx.community.girvan_newman(G)
    top_level_communities = next(communities_generator)
    next_level_communities = next(communities_generator)
    communities = sorted(map(sorted, next_level_communities))

    colors = colors2Community(communities)

    for index, row in colors.iterrows():
        G.nodes[row['node']]['group'] = row['group']
        G.nodes[row['node']]['color'] = row['color']
        G.nodes[row['node']]['size'] = G.degree[row['node']]

    net = Network(
        notebook=False,
        cdn_resources="remote",
        height="100%",
        width="100%",
        select_menu=True,
        filter_menu=False,
    )

    net.from_nx(G)
    net.force_atlas_2based(central_gravity=0.015, gravity=-31)

    # Load full text
    with open(script_path, 'r', encoding='utf-8') as file:
        full_text = file.read()

    # Generate the HTML content
    graph_html = net.generate_html()
    split_view_html = r'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Knowledge Graph with Text</title>
        <style>
            body {{
                display: flex;
                margin: 0;
                height: 100vh;
                overflow: hidden;
            }}
            #graph {{
                flex: 1;
                border-right: 1px solid #ddd;
                height: 100%;
            }}
            #text {{
                flex: 1;
                padding: 10px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }}
            #text h2 {{
                margin-top: 0;
            }}
            #originalText {{
                flex: 1;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
            .highlight {{
                background-color: yellow;
            }}
        </style>
    </head>
    <body>
        <div id="graph">{graph_html}</div>
        <div id="text">
            <h2>Full Text</h2>
            <div id="originalText">{full_text}</div>
        </div>

        <script type="text/javascript">
            {network_data}

            window.onload = function() {{
                var container = document.getElementById("graph");
                var data = {{
                    nodes: nodes,
                    edges: edges
                }};
                var options = {{
                    nodes: {{
                        shape: 'dot',
                        size: 16
                    }},
                    edges: {{
                        width: 2
                    }},
                    physics: {{
                        enabled: true
                    }}
                }};
                var network = new vis.Network(container, data, options);

                var originalTextElement = document.getElementById("originalText");
                // Keep a pristine copy of the text so re-highlighting never corrupts it.
                var fullText = originalTextElement.textContent;

                function escapeHtml(s) {{
                    return s.replace(/&/g, '&amp;')
                            .replace(/</g, '&lt;')
                            .replace(/>/g, '&gt;');
                }}

                function escapeRegExp(s) {{
                    return s.replace(/[.*+?^${{}}()|[\]\\]/g, '\\$&');
                }}

                function renderHighlight(start, end) {{
                    originalTextElement.innerHTML =
                        escapeHtml(fullText.substring(0, start)) +
                        '<span class="highlight">' + escapeHtml(fullText.substring(start, end)) + '</span>' +
                        escapeHtml(fullText.substring(end));
                }}

                network.on("click", function (params) {{
                    // Reset to the pristine, un-highlighted text on every click.
                    originalTextElement.innerHTML = escapeHtml(fullText);

                    if (params.edges.length === 0) return;

                    var edge = edges.get(params.edges[0]);
                    if (!edge || !edge.original_text) return;

                    var snippet = edge.original_text.trim();
                    if (!snippet) return;

                    // original_text was rebuilt by joining sentences with single spaces,
                    // while the displayed text keeps its original newlines / spacing.
                    // Match whitespace-tolerantly so every edge can be located.
                    var pattern = snippet.split(/\s+/).map(escapeRegExp).join('\\s+');
                    var match;
                    try {{
                        match = new RegExp(pattern).exec(fullText);
                    }} catch (e) {{
                        match = null;
                    }}

                    if (match) {{
                        renderHighlight(match.index, match.index + match[0].length);
                        var firstHighlight = document.querySelector('.highlight');
                        if (firstHighlight) {{
                            firstHighlight.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        }}
                    }}
                }});
            }};
        </script>
    </body>
    </html>
    '''.format(graph_html=graph_html, full_text=full_text, network_data="")

    with open(graph_output_directory, 'w', encoding='utf-8') as file:
        file.write(split_view_html)
