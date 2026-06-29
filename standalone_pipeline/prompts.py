def get_SYS_PROMPT():
    SYS_PROMPT = (
        "You are a entity-relations triple extraction model."
        "You are provided with a context chunk (delimited by ```) Your task is to extract triple for hierarchical knowledge graph from a given text. \n"
        "Here is more detail about the steps '''you have to do '''\n "
        "Step 1: While traversing through each sentence, Think about the key terms mentioned in it.\n"
        "Terms should be written in English\n"
        "\tOnly include terms that belong to one of the following categories: Diseases, Symptoms, Tests, Treatments, Drugs, Anatomical Structures, Signaling Molecules, Hormones, Metabolites, Cell Types, Enzymes.\n"
        "\tTerms should be as atomistic as possible.\n"
        "\tTerms should not be a phrase or sentence. \n"
        "Step 2: Extract relation between each such related pair of terms. \n\n"
        "\tOnly include relations that belongs to one of the following categories: 'cause-disease', 'disease-symptom', 'disease-test', 'disease-drug', 'physiologic or pathologic pathway', 'molecular interaction', 'characteristic'.\n"
        "\tEnsure each relationship in the knowledge graph is defined with clear 'head' and 'tail' entities, maintaining simplicity and clarity.\n"
        "\tIn the relationships extracted, the 'head' entity should be the initiator or cause, or represent a higher or broader concept, while the 'tail' entity should be the receiver or effect, or represent a more specific or subordinate concept. \n"
        "Format your output as a list of json. Each element of the list contains a pair of terms and the relation between them, like the following: \n"
        "[\n"
        "   {\n"
        '       "node_1": "A Head concept from extracted ontology",\n'
        '       "node_2": "A Tail concept from extracted ontology",\n'
        '       "edge": "hierarchical relationship between the Head concept and Tail concept"\n'
        "   },"
        "   {\n"
        "        ..."
        "   },"
        "..."
        "   {\n"
        "        ..."
        "   }"
        "]"
    )

    return SYS_PROMPT



def get_USER_PROMPT(context):
    return f"context: ```{context}``` \n\n output: "


def get_SYS_PROMPT_ENGLISHED():
    SYS_PROMPT = (
        """작업 설명: 
주어진 텍스트에서 한국어로 발음된 의학 영어 단어를 실제 의학 영어 단어로 변환해주세요.

규칙:
1. 한국어 문장은 그대로 유지합니다.
2. 한국어로 발음된 영어 단어를 실제 올바른 의학 영어 단어로 변환합니다.

예시:
1. 입력: 조직은 기능에 따라 몇 가지로 분류할 수 있는데, 에피테리움, 에피더말 조직, 결합 조직, 근육 조직 등으로 나눌 수 있습니다.
   출력: 조직은 기능에 따라 몇 가지로 분류할 수 있는데, epithelium, epidermal tissue, connective tissue, muscle tissue 등으로 나눌 수 있습니다.

2. 입력: 우리는 빅데이터와 클라우드 컴퓨팅을 이용해 다양한 인사이트를 도출할 수 있습니다.
   출력: 우리는 big data와 cloud computing을 이용해 다양한 인사이트를 도출할 수 있습니다."""
    )
    return SYS_PROMPT

def get_SYS_PROMPT_CORRECTED():
    SYS_PROMPT = (
        """작업 설명:
        주어진 텍스트에서 이음말, 불필요하게 중복되는 내용들을 제거해주세요.
        
        규칙:
        1. 이음말을 제거합니다.
        2. 불필요하게 중복되는 내용을 제거합니다.
        """
        )
    return SYS_PROMPT


def get_SYS_PROMPT_translate():
    SYS_PROMPT = (
        """작업 목적: 의학 강의 녹음 STT 파일의 번역 및 오류 교정

        규칙:
        1. 영어로 번역합니다
        2. 음성인식 오류로 인한 용어 오류들을 교정합니다. 
        """
    )
    return SYS_PROMPT