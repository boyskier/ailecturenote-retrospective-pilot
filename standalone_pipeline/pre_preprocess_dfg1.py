import os
import pandas as pd
from dotenv import load_dotenv
from UMLS_api import unify_graph_nodes
import config

load_dotenv(config.ENV_FILE)
umls_apikey = os.getenv("UMLS_API_KEY")


async def pre_preprocess_dfg1(dfg1):
    # Process synonyms with UMLS
    dfg1 = await unify_graph_nodes(dfg1, umls_apikey)
    return dfg1
