import aiohttp
import asyncio
from collections import Counter

async def get_cui(apikey, search_string, session):
    base_uri = 'https://uts-ws.nlm.nih.gov'
    version = 'current'
    query = {
        'string': search_string,
        'apiKey': apikey,
        'pageNumber': 1
    }
    async with session.get(f'{base_uri}/search/{version}', params=query) as response:
        response_json = await response.json()
        results = response_json['result']['results']
        return results[0]['ui'] if results else None

async def get_word2cui_dict(apikey, words):
    word2cui_dict = {}
    async with aiohttp.ClientSession() as session:
        tasks = []
        for word in words:
            if word not in word2cui_dict:
                tasks.append(asyncio.create_task(get_cui(apikey, word, session)))

        results = await asyncio.gather(*tasks)
        for word, cui in zip(words, results):
            word2cui_dict[word] = cui

    return word2cui_dict

def get_cui2word_dict_from_word2cui_dict(word2cui_dict):
    cui2word_dict = {}
    for word, cui in word2cui_dict.items():
        if cui:
            if cui not in cui2word_dict:
                cui2word_dict[cui] = [word]
            else:
                cui2word_dict[cui].append(word)
    return cui2word_dict

async def unify_graph_nodes(dfg1, apikey):
    # Extract all nodes as a list
    all_nodes = list(set(dfg1['node_1'].tolist() + dfg1['node_2'].tolist()))

    # Look up CUI
    word2cui_dict = await get_word2cui_dict(apikey, all_nodes)

    # Create synonym groups
    cui2word_dict = get_cui2word_dict_from_word2cui_dict(word2cui_dict)

    # Select the most frequent word in each CUI group
    word_frequency = Counter(dfg1['node_1'].tolist() + dfg1['node_2'].tolist())
    cui2rep_word = {cui: max(words, key=lambda w: word_frequency[w]) for cui, words in cui2word_dict.items() if words}

    # Standardize node names
    dfg1['node_1'] = dfg1['node_1'].apply(lambda word: cui2rep_word.get(word2cui_dict[word], word))
    dfg1['node_2'] = dfg1['node_2'].apply(lambda word: cui2rep_word.get(word2cui_dict[word], word))

    return dfg1


