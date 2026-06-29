import pandas as pd
import re

def chunkFinder(chunks, dfg1):
    merged = pd.merge(dfg1, chunks, on='chunk_id')

    def find_sentence_indices(row):
        chunk = row['text'].lower()
        node_1 = row['node_1'].lower().split()
        node_2 = row['node_2'].lower().split()

        sentences = re.split(r'(?<=[.!?])\s+', chunk)

        def contains_all_words(sentence, words):
            return all(word in sentence for word in words)

        indices = [i for i, sentence in enumerate(sentences) if
                   contains_all_words(sentence, node_1) and contains_all_words(sentence, node_2)]

        if indices:
            return indices
        else:
            node_1_indices = [i for i, sentence in enumerate(sentences) if contains_all_words(sentence, node_1)]
            node_2_indices = [i for i, sentence in enumerate(sentences) if contains_all_words(sentence, node_2)]

            if node_1_indices and node_2_indices:
                start_index = min(node_1_indices[0], node_2_indices[0])
                end_index = max(node_1_indices[-1], node_2_indices[-1])
                return list(range(start_index, end_index + 1))
            else:
                return list(range(len(sentences)))

    merged['sentence_indices'] = merged.apply(find_sentence_indices, axis=1)

    def extract_sentences(row):
        sentences = re.split(r'(?<=[.!?])\s+', row['text'])
        indices = row['sentence_indices']
        return ' '.join([sentences[i] for i in indices])

    merged['original_text'] = merged.apply(extract_sentences, axis=1)
    dfg1['original_text'] = merged['original_text']

    return dfg1