import uuid
import openai
import seaborn as sns
import random
import pandas as pd
import numpy as np
import asyncio
import aiohttp
import networkx as nx
import re
from pyvis.network import Network
from prompts import get_SYS_PROMPT, get_USER_PROMPT
from logger import log_gpt_request
from graph_json_utils import make_response_content_json
import ast
import config

palette = "hls"


def load_documents(file_path):
    documents = []
    with open(file_path, 'r', encoding='utf-8') as file:
        documents.append(file.read())

    return documents


def split_documents(documents, chunk_sentence_size=5, chunk_sentence_overlap=1):
    chunks = []
    for document in documents:
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', document)

        for i in range(0, len(sentences), chunk_sentence_size - chunk_sentence_overlap):
            chunk = ' '.join(sentences[i:i + chunk_sentence_size])
            chunks.append(chunk)
    return chunks


def documents2Dataframe(documents):
    rows = []
    for chunk in documents:
        row = {
            "text": chunk,  # Use chunk directly instead of chunk.page_content
            # No metadata is present, so omit this part or add required metadata.
            "chunk_id": uuid.uuid4().hex,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df


def graph2Df(nodes_list) -> pd.DataFrame:
    ## Remove all NaN entities
    graph_dataframe = pd.DataFrame(nodes_list).replace(" ", np.nan)
    graph_dataframe = graph_dataframe.dropna(subset=["node_1", "node_2"])
    graph_dataframe["node_1"] = graph_dataframe["node_1"].apply(lambda x: x.lower())
    graph_dataframe["node_2"] = graph_dataframe["node_2"].apply(lambda x: x.lower())

    return graph_dataframe


async def df2Graph_ver2_LKE(dataframe, model, user_id):
    async with aiohttp.ClientSession() as session:
        openai.aiosession.set(session)
        tasks = []
        for i, (_, row) in enumerate(dataframe.iterrows()):
            task = graphPrompt_LKE_V1(row.text, i, model, user_id, {"chunk_id": row.chunk_id})
            tasks.append(task)

        graph_data = await asyncio.gather(*tasks)

    graph_data = [item for sublist in graph_data for item in sublist if item is not None]
    return graph_data


async def graphPrompt_LKE_V1(context: str, orig_chunk_count, model, user_id, metadata):  # Keep metadata just in case
    if model == None:
        model = "gpt-3.5-turbo"

    messages = [
        {"role": "system", "content": get_SYS_PROMPT()},
        {"role": "user", "content": get_USER_PROMPT(context)},
    ]

    response = await openai.ChatCompletion.acreate(model=model, messages=messages, temperature=0, max_tokens=1000)
    response_content = response.choices[0].message['content']

    # Extract token count
    input_tokens = response['usage']['prompt_tokens']  # Weight by attempt count
    output_tokens = response['usage']['completion_tokens']

    log_gpt_request(user_id, model, input_tokens, output_tokens)

    return make_response_content_json(response_content, metadata)


def colors2Community(communities) -> pd.DataFrame:
    ## Define a color palette
    p = sns.color_palette(palette, len(communities)).as_hex()
    random.shuffle(p)
    rows = []
    group = 0
    for community in communities:
        color = p.pop()
        group += 1
        for node in community:
            rows += [{"node": node, "color": color, "group": group}]
    df_colors = pd.DataFrame(rows)
    return df_colors


def create_graph_html(dfg1, graph_output_directory):
    G = nx.Graph()

    nodes = pd.concat([dfg1['node_1'], dfg1['node_2']], axis=0).unique()

    ## Add nodes to the graph
    for node in nodes:
        G.add_node(
            str(node)
        )

    ## Add edges to the graph
    for index, row in dfg1.iterrows():
        G.add_edge(
            str(row["node_1"]),
            str(row["node_2"]),
            title=row["edge"],
            weight=row['count'] / 4
        )
    communities_generator = nx.community.girvan_newman(G)
    top_level_communities = next(communities_generator)
    next_level_communities = next(communities_generator)
    communities = sorted(map(sorted, next_level_communities))

    ## Now add these colors to communities and make another dataframe

    colors = colors2Community(communities)

    for index, row in colors.iterrows():
        G.nodes[row['node']]['group'] = row['group']
        G.nodes[row['node']]['color'] = row['color']
        G.nodes[row['node']]['size'] = G.degree[row['node']]

    net = Network(
        notebook=False,
        cdn_resources="remote",
        height="900px",
        width="100%",
        select_menu=True,
        filter_menu=False,
    )

    net.from_nx(G)
    net.force_atlas_2based(central_gravity=0.015, gravity=-31)
    net.show_buttons(filter_=["physics"])

    net.show(graph_output_directory, notebook=False)


def get_G(dfg1):
    # Create graph
    nodes = pd.concat([dfg1['node_1'], dfg1['node_2']], axis=0).unique()

    G = nx.DiGraph()

    # Add nodes to the graph
    for node in nodes:
        G.add_node(str(node))

    # Add edges to the graph
    for index, row in dfg1.iterrows():
        G.add_edge(str(row["node_1"]), str(row["node_2"]), title=row["edge"], weight=row['count'] / 4)

    # Community detection
    communities_generator = nx.community.girvan_newman(G.to_undirected())
    top_level_communities = next(communities_generator)
    next_level_communities = next(communities_generator)
    communities = sorted(map(sorted, next_level_communities))

    colors = colors2Community(communities)

    for index, row in colors.iterrows():
        G.nodes[row['node']]['group'] = row['group']
        G.nodes[row['node']]['color'] = row['color']
        G.nodes[row['node']]['size'] = G.degree(row['node'])

    return G


def get_root_nodes(G):
    # Select Root node from the entire graph
    degree_dict = dict(G.degree())
    sorted_degree = sorted(degree_dict.items(), key=lambda item: item[1], reverse=True)
    root_node = sorted_degree[0][0]

    return root_node



def get_seed_nodes(pre_preprocessed_dfg1, datafrom='cleaned_text', verbose=False):
    node_1_list = pre_preprocessed_dfg1['node_1'].tolist()
    node_2_list = pre_preprocessed_dfg1['node_2'].tolist()
    all_nodes = list(set(node_1_list + node_2_list))

    if datafrom == 'cleaned_text':
        # Load and preprocess user-provided seed vocabulary CSV (domain term filter).
        # If file does not exist, skip seed-based pruning (empty seed -> safe no-op).
        clean_text_path = config.DATA_DIR / 'cleaned_text.csv'
        if not clean_text_path.exists():
            print(f"[get_seed_nodes] seed vocabulary not found at {clean_text_path}; "
                  f"skipping seed-based pruning. Provide your own 'Clean Text' CSV to enable it.")
            return [], all_nodes
        seed_vocab = pd.read_csv(clean_text_path)
        clean_text = seed_vocab['Clean Text'].fillna("").astype(str)
        # Combine all values in the DataFrame into a single long string
        text_string = ' '.join(clean_text.str.lower().str.strip().tolist())
        seed_nodes = []
        not_seed_nodes = []
        for node in all_nodes:
            node = node.lower().strip()  # Convert to lowercase and remove leading/trailing whitespace
            if node in text_string:
                seed_nodes.append(node)
                if verbose:
                    print(f"seed node: {node}")
            else:
                not_seed_nodes.append(node)
                if verbose:
                    print(f"not seed node: {node}")

    elif datafrom == 'answer':
        # Load and preprocess user-provided seed vocabulary CSV (answer column).
        # If file does not exist, skip seed-based pruning (empty seed -> safe no-op).
        answer_path = config.DATA_DIR / 'answers.csv'
        if not answer_path.exists():
            print(f"[get_seed_nodes] seed vocabulary not found at {answer_path}; "
                  f"skipping seed-based pruning. Provide your own 'answer' CSV to enable it.")
            return [], all_nodes
        seed_vocab = pd.read_csv(answer_path).astype(str)
        # DataFrame의 모든 값을 하나의 긴 문자열로 결합
        seed_vocab['answer'] = seed_vocab['answer'].apply(ast.literal_eval)  # Convert string to list
        seed_nodes = []
        not_seed_nodes = []
        for node in all_nodes:
            node = node.lower().strip()  # Convert to lowercase and remove whitespace
            if any(node in answer for answer in seed_vocab['answer']):
                seed_nodes.append(node)
                if verbose:
                    print(f"seed node: {node}")
            else:
                not_seed_nodes.append(node)
                if verbose:
                    print(f"not seed node: {node}")

    else:
        seed_nodes, not_seed_nodes = None, []

    return seed_nodes, not_seed_nodes


def G_to_dfg1(G, original_dfg1):
    data = {
        'node_1': [],
        'node_2': [],
        'edge': [],
        'chunk_id': [],
        'count': []
    }

    for u, v, attr in G.edges(data=True):
        original_rows = original_dfg1[
            (original_dfg1['node_1'] == u) & (original_dfg1['node_2'] == v) & (original_dfg1['edge'] == attr['title'])]

        if not original_rows.empty:
            original_row = original_rows.iloc[0]
            data['node_1'].append(u)
            data['node_2'].append(v)
            data['edge'].append(attr['title'])
            data['chunk_id'].append(original_row['chunk_id'])
            data['count'].append(original_row['count'])
        else:
            print(f"No matching row found for edge: ({u}, {v}, {attr['title']})")

    new_dfg1 = pd.DataFrame(data)
    return new_dfg1
