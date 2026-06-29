import os
import asyncio
import numpy as np
import config
from graph_utils import (load_documents, split_documents, documents2Dataframe, df2Graph_ver2_LKE, graph2Df,
                         create_graph_html, get_G, get_root_nodes, get_seed_nodes, G_to_dfg1)
from translate import apply_translate_to_df
from pre_preprocess_dfg1 import pre_preprocess_dfg1
from KGpruning import preprocess_graph, remove_cycles, remove_redundant_relations
from chunkFinder import chunkFinder
from visualize_with_page import create_graph_html_with_text


def make_knowledge_graph_from_script(script_path, model, user_id, chunk_sentence_size=10,
                                     chunk_sentence_overlap=2):
    filename = os.path.basename(script_path)
    file_name, file_extension = os.path.splitext(filename)

    # Load the script
    documents = load_documents(script_path)
    pages = split_documents(documents, chunk_sentence_size, chunk_sentence_overlap)
    pages_df = documents2Dataframe(pages)

    # translate
    translated_pages_df = asyncio.run(apply_translate_to_df(pages_df, user_id))  # Receive modified DataFrame

    # Run the LLM
    graph_data_from_LLM = asyncio.run(df2Graph_ver2_LKE(translated_pages_df, model, user_id))
    dfg1 = graph2Df(graph_data_from_LLM)

    # dfg1 cleaning process
    dfg1.replace("", np.nan, inplace=True)
    dfg1.dropna(subset=["node_1", "node_2", 'edge'], inplace=True)
    dfg1['count'] = 4

    # pruning the graph
    G = get_G(dfg1)
    dfg1 = asyncio.run(pre_preprocess_dfg1(dfg1))

    output_file_path_before_pruning = config.product_path(
        'knowledge_graph',
        f'{file_name}_{model}_graph_before_pruning.html',
    )
    create_graph_html(dfg1, output_file_path_before_pruning)

    root_node = get_root_nodes(G)
    seed_nodes, _ = get_seed_nodes(dfg1, datafrom='cleaned_text', verbose=False)
    G = preprocess_graph(G, seed_nodes, root_node)
    G = remove_cycles(G)
    G = remove_redundant_relations(G)
    # Omit multiple inheritance
    dfg1 = G_to_dfg1(G, dfg1)
    dfg1.to_csv(config.product_path('knowledge_graph', f'{file_name}_dfg1.csv'), index=False)

    # Save graph as HTML
    output_file_path = config.product_path('knowledge_graph', f'{file_name}_{model}_graph.html')
    create_graph_html(dfg1, output_file_path)

    output_file_path_with_text = config.product_path(
        'knowledge_graph',
        f'{file_name}_{model}_graph_with_text.html',
    )
    dfg1_with_indices = chunkFinder(pages_df, dfg1)
    create_graph_html_with_text(dfg1_with_indices, script_path, output_file_path_with_text)

    return output_file_path_with_text
