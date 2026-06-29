"""Claude-drafted annotations for the pilot lectures that already have a reference.

This script encodes two things Claude produced on 2026-06-26 after reading all
four conditions of the lectures:

  1. The *mechanical* domain-term curation (pruning + English-variant merging +
     Korean-phonetic variants + polarity tags). ``main()`` writes these into
     ``domain_terms.csv``.

        *** Run it ONCE, then hand-verify domain_terms.csv. Do NOT re-run after
            you start editing it, or your edits are lost. ***

  2. The ``POLARITY_ITEMS`` and ``SEMANTIC`` seed dictionaries (draft polarity
     verdicts + semantic-drift labels). These are NOT authoritative and are no
     longer written to any CSV; they survive only as the non-authoritative
     ``claude_hint`` seeds that ``build_review_worksheets.py`` drops next to each
     row of the exhaustive ``polarity_review.csv`` / ``semantic_review.csv``
     worksheets the human annotator actually fills in.

The headline English-script-preservation metric does NOT depend on any judgement
here (it needs only canonical_english + keep); the seed labels only ever surface
as hints beside the human's own verdict.

    python analysis/curate_annotations.py    # (re)write domain_terms.csv drafts
"""
from __future__ import annotations

import csv

import config
import term_dictionary as td

# ---------------------------------------------------------------------------
# 1) DOMAIN TERMS — generic candidates to drop (keep=0)
# ---------------------------------------------------------------------------
DROP = {
    "diuretics_01": {
        "side effect", "site", "cell", "fluid", "loss", "pump", "volume",
        "segment", "removal", "recycling", "potency", "selective",
        "positive charge", "site of action", "iv", "elderly", "black patient",
        "urine", "fluid manegement", "frosemide", "iv frosemide",
        "k+ sparing diuretics", "potassium-sparing diuretics",
        "chloride co-transporter", "thick ascending limb of loop of henle",
    },
    "acuteinflammation_02": {
        "killing", "fluid", "vessel", "dominant", "flow", "protein", "receptor",
        "direct", "collateral", "contraction", "engulf", "enzyme", "injured",
        "release", "set point", "site", "tissue", "mediate", "mediation",
        "tnf-", "leukocute", "neuthrophil", "pahgocytosis",
        "margination and rolling", "leukocyte activation and killing",
        "leukocyte recruitment cascade", "lt-b4", "protein rich",
    },
    "anthrax_01": {
        # generic English words the speaker used but are not anthrax domain terms
        "factor", "form", "function", "clinical", "overview", "scientific name",
        "typical", "public", "protective", "toxic", "organism", "cm",
        "types of anthrax", "clinical manifestations", "supportive care",
        "occupational safety measures", "exposure source", "developed country",
        "infected animal", "vaccinated animals", "butchery", "leatherwork",
        "gram",
        # redundant composite phrasings (plasmid + pXO1 already counted separately)
        "plasmid pxo1", "pxo1 plasmid",
    },
}

# canonical_english (lowercased) -> "pipe|separated|korean phonetic renderings"
# harvested from the raw whisper-1 / gpt-4o outputs of each lecture.
PHONETIC = {
    "diuretics_01": {
        "diuretics": "다이유렉스|다이오레틱스|다이오렉스|다이오레릭스|다이레릭스|다이어렉스|다이예렉스",
        "loop diuretics": "루프 다이오릭스|룩 다이오릭스|루프 다이오레릭스|루타이오레릭스|룹 다이오렉스",
        "thiazide diuretics": "사이아자이드 다이오레릭스|싸이아자이드 다이오레릭스|사이아자이드 다이얼릭스",
        "thiazide": "사이아자이드|싸이아자이드|다이아자이드",
        "potassium sparing diuretics": "포타슘 스페어링 다이오릭스|포타이션 스페어링 다이오릭스|포타슘 스페어링 다이레릭스",
        "nephron": "레프론|네프론|메프론",
        "kidney": "키드니|히데니|히드니",
        "reabsorption": "리옵솔션|리옵설선|리흡솔션|리흡설션",
        "proximal convoluted tubule": "프로치멀 건볼루티 튜블|프로스티머 컨볼루티 튜브|폭시멀 커뮬리티 튜브",
        "loop of henle": "루프 오프 헨리|루프 오브 핸리|루프 헨리",
        "distal convoluted tubule": "디지털 건볼루티 튜브|디스탈 컨볼루티 튜브|디스컨볼루티 튜브",
        "collecting duct": "콜렉팅 덕트",
        "thick ascending limb": "히거 샌딩 림|핵 어센딩 림|리커센딩 림",
        "carbonic anhydrase inhibitor": "카르보닉 아나이드레이즈 이니비터|카보닉 아날로이드 레이스 인이비터|카르보닉 아나이드레이즈 이니비터",
        "carbonic anhydrase": "카르보닉 아나이드레이즈|카보닉 아날로이드 레이스",
        "acetazolamide": "아세타졸라마이드",
        "na/h exchanger": "나트륨 펄톤 익체인저|나트륨 폴톤 익체인저|나트륨 프로톤 익스체인저",
        "bicarbonate": "바이칼보네이트|바이카보네이트",
        "glaucoma": "글라오코마|글라우코마",
        "aqueous humor": "아쿠스 휴마|아쿠에스 휴마",
        "altitude sickness": "엘티티드 시그니스|엘티툴 시그니스|엘티틸 시그니스|엘티티드 시그니즈",
        "metabolic alkalosis": "메타볼릭 알칼로시스|메타블리 알칼로시스",
        "metabolic acidosis": "메타볼릭 아시도시스|메타볼릭 에시도시스",
        "hypokalemia": "하이포칼리미아|하이포칼레미아",
        "hyperkalemia": "하이퍼칼리미아|하이퍼칼레미아",
        "hypercalcemia": "하이퍼칼세미아|하이퍼칼슘미아|하이퍼칼슘이야",
        "hypocalcemia": "하이포칼세미아|하이포칼슘미아",
        "hyponatremia": "하이포나트레미아|하이포나트리미아|하이퍼나트림이야",
        "hypomagnesemia": "하이포마그네시미아|하이포마그네심이야",
        "hyperuricemia": "하이퍼유라이세미아",
        "uric acid": "유릭애씨드|유린애씨드|유링애씨드|유린에시드",
        "sulfonamide allergy": "설포나마이드 알러지",
        "sulfa allergy": "설파 알러지|설포 알러지",
        "loop diuretics ": "",
        "furosemide": "프로세마이드|플로세마이드|프로세마이드",
        "bumetanide": "뷰메타나이드|뷰 메타나이드",
        "torsemide": "토르세마이드|톨세마이드",
        "ethacrynic acid": "에타크리닉 애시드|에사클리닉 애씨드|에스타클린의 에시드",
        "spironolactone": "스피로놀락톤|스피로놀 락톤|스피로노락톤",
        "eplerenone": "에필레프론|에필레피론",
        "amiloride": "아밀리오라이드",
        "triamterene": "트라이언트레인|트라이엄트레인",
        "hydrochlorothiazide": "하이드로클로르 사이아자이드|하이드로클로로사이아자이드|하이드로클로르타이아자이드",
        "chlorothalidone": "클로르 살리돈|클로르 싸리돈",
        "metolazone": "메톨라존|에톨라존",
        "indapamide": "인다파마이드|인타파마이드",
        "potassium": "포타슘",
        "chloride": "클로라이드",
        "lumen": "루멘",
        "tubular lumen": "튜블러 루멘",
        "paracellular": "파라셀룰러|파라셀률",
        "countercurrent multiplier": "카운터 커런트 멀티플라이어|카운터컬러 워티플라이어|카운터 컬러드 멀티플라이어",
        "medullary interstitium": "메듈러리 인터스티움|메딜럴 인터스티슘|메듈러리 인터스티심",
        "medulla": "메듈라|메딜라|메듈러",
        "water reabsorption": "워터 리옵솔션|보타 리흡솔션",
        "acute pulmonary edema": "어큐트 풀머널 이데마|아큐트 프루머너리 이데마|어큐트 풀머널리 데마",
        "venodilation": "비노다이레이션|비누 다이레이션",
        "diruesis": "다이오레시스|다이레리스|다이오레이스",
        "congestive heart failure": "컨제스티브 하트 페일리어|컨지스티브 하트 페일리어|컨제스티브 허트 페일리어",
        "iv saline": "아이비 셀라인|아이브이 셀라인",
        "nephrotic syndrome": "네프로틱신드롬|네프로틱 신드롬",
        "ckd edema": "ckd 이뇨제|ckd 이데마",
        "glomerular filtration rate": "글로멜로르 필트레이션 레이트|구멜로로 필트레이션 레이트|메듈러 필트레이션 레이트",
        "aldosterone": "알도스테론|알도스테롤",
        "proton": "프로톤|펄톤",
        "ototoxicity": "오토톡시디|오토톡시티",
        "gout": "가오트|가우트",
        "hyperglycemia": "하이퍼글라이세미아",
        "hyperlipidemia": "하이퍼리피디미아|하이퍼 리피디미아",
        "hypertension": "하이퍼텐션",
        "resistant hypertension": "리지스턴트 하이퍼텐션",
        "early distal convoluted tubule": "얼리디스컨볼루티 튜블|얼리 디스탈 컨볼루티 튜브리",
        "late distal convoluted tubule": "레이트 디스탈 컴포넌티 튜블|레이트 디지털 컨볼루티 튜브",
        "chloride cotransporter": "클로라이드코 트랜스포터|클로라이드 코트렌스포터|클로라이드 코트랜스포터",
        "enac": "이낙|이넥|인액|이맥",
        "enac blocker": "이낙 블로커|이낙 블러커",
        "mineralocorticoid receptor": "미네랄로 콜티코이드 리셉터|미네랄드 콜티크 오일 리셉터|미네랄로 콜티코이드 리세터",
        "sodium-potassium atpase": "나트륨 포타슘 에이티페이스",
        "primary hyperaldosteronism": "프라이머리 하이퍼 알도스테롤니즘|프라이머리 하이퍼알도스테론리즘",
        "hyperaldosteronism": "하이퍼 알도스테롤니즘|하이퍼알도스테론리즘|하이퍼알데르스테롤리즘",
        "aldosterone antagonist": "알도스테롤 안타고니스트|알도스테론 안타고니스트",
        "mortality benefit": "몰탈리티 베네피시|모탈리티 베네핏|몰탈리티 베네피시트",
        "cirrhosis ascites": "씨로시스 에사이티스|시루시스 에사이티스|시로시스 에사이티스|시로시스 아사이티스",
        "ace inhibitor": "에이스인이비터|에이스 인이비터|에이시니비터",
        "arb": "아르브|얼브|아르부타",
        "anti-androgenic effect": "안티 안드로제닉 이펙트|안티안드로제닉 이펙트",
        "gynecomastia": "가이나코멘스티아|가이나코메스티아",
        "libido": "리비도|리비드",
        "diabetes insipidus": "다이아베릭 인스피터스|다이아벳 인스피터스|다이아베리 인시피더스",
        "nephrogenic diabetes insipidus": "네프로제닉 다이아베릭 인스피터스|네프로제닉 다이아벳 인스피터스",
        "tubular flow": "튜블러플로우|튜빌러 플로우|튜브럴 플로우",
        "mild edema": "마일드 이데마|마일드이데마",
        "calcium oxalate": "칼슘 옥살레이트",
        "osmotic gradient": "오스모틱 그래디언트|오스모틱 그레디언트",
        "lithium": "리튬",
    },
    "acuteinflammation_02": {
        "leukocyte": "루코사이트|르코사이트",
        "inflammation": "인플라메이션",
        "acute inflammation": "아큐트 인플라메이션|어큐트 인플라메이션",
        "chronic inflammation": "크로닉 인플라메이션",
        "injury": "인저리|인절리",
        "infection": "인펙션",
        "vascular": "베스큘러|베스킬러",
        "cellular response": "셀룰러 리스폰스",
        "pathogen": "패소젠",
        "vascular permeability": "베스킬러 퍼미어빌리티|베스큘러 퍼미어빌리티",
        "vascular change": "베스킬러 체인지|베스큘러 체인지",
        "endothelium": "엔도셀리움|엔도셀렘",
        "endothelial cell": "엔드셀리얼 셀|엔도셀리얼 셀",
        "endothelial cell contraction": "엔드셀리얼 셀 컨트랙션",
        "chemotaxis": "케모텍시스",
        "cytokine": "사이토카인|사이트카인",
        "histamine": "히스타민",
        "neutrophil": "뉴트로필|유트로필",
        "macrophage": "마크로파이지|마크로파지|마이크로파이지",
        "margination": "마지네이션|마지네이션",
        "rolling": "롤링",
        "adhesion": "어데이션|어디이션|어데이션",
        "transmigration": "트랜스마이그레이션",
        "diapedesis": "다이아페디시스|다이아베티스",
        "selectin": "셀렉틴",
        "integrin": "인테그린",
        "chemokine": "케모카인|케부카인",
        "chemoattractant": "케모어트랙턴트|케모어트랙턴",
        "chemotactic gradient": "케모세틱 그래디언트|케모타틱 그레이디언트",
        "exudate": "엑스데이트",
        "transudate": "트렌스데이트",
        "stasis": "스테시스|스테이시스",
        "vasodilation": "베소 다일레이션|베소다일레이션",
        "vasoconstriction": "베소 컨스트릭션|베소건스트릭션|베소컨스트릭션",
        "transient vasoconstriction": "트랜지언트 베소 컨스트릭션",
        "blood flow": "블루트 플로우|블러드 플로우",
        "blood viscosity": "플루이드 비스커시티|블러드 비스커시티",
        "red blood cell": "레드블럭 셀|레드 블러드 셀",
        "prostaglandin": "프로스타그란딩|프로스타글란딘",
        "leukotriene": "루코트린|루코트린",
        "leukotriene b4": "루코트린 b4",
        "thromboxane": "스럼복사|스론복스안",
        "fever": "피버",
        "phagocytosis": "파고사이토시스|파고사이트시스",
        "opsonin": "옵소닌",
        "phagosome": "파고솜",
        "lysosome": "라이소솜",
        "phagolysosome": "파고라이소솜|파고 라이소솜",
        "superoxide": "수포록사이드|슈퍼옥사이드",
        "myeloperoxidase": "마일로포록시데이스|마일로 퍼옥시데이스",
        "lysozyme": "라이소자임",
        "defensin": "디펜진|디펜신",
        "major basic protein": "메이저 베이직 프로틴",
        "sepsis": "섹시스|셉시스",
        "hypotension": "하이포텐션",
        "vasoactive amines": "베소 액티브 아민|베소액티브 아민",
        "arachidonic acid": "아라키토닉 액시|아라키도닉 액시드",
        "cox pathway": "콕스 패스웨이|콕스페이스웨이",
        "lox pathway": "록스 패스웨이|록스페이스웨이",
        "nsaid": "앤세즈|엔세즈",
        "complement system": "컴플리멘트 시스템",
        "anaphylatoxin": "아나필락톡신|아라필락톡신",
        "membrane attack complex": "멘브린 어택 컴플렉스|멤브레 아택 컴플렉스",
        "kinin": "키닌",
        "bradykinin": "베디키딘|베디키닌",
        "hypothalamus": "하이퍼살라무스",
        "acute phase protein": "어큐트 페이스 프로틴",
        "liver": "리버",
        "fibrinogen": "파이브리노젠",
        "leukocytosis": "루코사이토시스",
        "bone marrow": "본메로|본매료",
        "left shift": "레프트 쉬프트",
        "blood smear": "블롯스미러|블루스미어",
        "resolution": "레솔루션",
        "fibrosis": "파이브로시스",
        "scarring": "스커링|스컬링",
        "connective tissue": "커넥티브 티슈",
        "persistent stimulus": "퍼시스텐트 스티밀러스|퍼시스턴 스티뮬러스",
        "lymphocyte": "림포사이트",
        "granuloma": "그랜드로마|그랜드로마",
        "homophilic binding": "호모필릭 바인딩",
        "basement membrane": "베이스먼드 멤브레인|베이스먼트 멤브레인",
        "collagenase": "콜라겐 에이스|콜라게네이즈",
        "phagocytosis ": "",
        "tissue regeneration": "티슈 리제너레이션",
        "tissue damage": "티슈 데미지",
        "actin polymerization": "액틴 폴리머레이션",
        "low affinity": "로어 피니티|로우 어피니티",
        "high affinity": "하이어 피니티|하이 어피니티",
    },
    "anthrax_01": {
        "anthrax": "엔트락스|앤트렉스|앤스렉스|안트랙스|엔스렉스|안쓰렉스",
        "bacillus anthracis": "바실러스 앤트라시스|바실러스 앤트라시스",
        "gram positive": "그람 퍼지티브|그람 포지티브",
        "rod-shaped": "로드쉽트|로드쉐이프|로드쉐이프트|로드 쉐입",
        "obligate aerobe": "오블리게이트 에어로브|오블리게이트 에어롭",
        "organism": "오게니즘|오가니즘",
        "spore": "스포어|스포",
        "dormant spore": "돌먼스포어|돌먼 스포어",
        "koch": "코어|코흐",
        "public health": "퍼블릭헬스|퍼블릭 헬스",
        "bioterror": "바이오테러|바이오 테러",
        "exotoxin": "엑소턱센|엑소턱신|엑소톡신|턱센|턱슨",
        "pathogenesis": "패서제닉|패소제네시스",
        "protective antigen": "프로텍티브 안티젠|프로텍티브 안티비전|프로텍티브 안티지엔",
        "edema factor": "에드마펙터|에데마 팩터|에드마 팩터|아드맨 팩터",
        "lethal factor": "리소드 팩터|리스펙터|리소 팩터|레설 팩터",
        "host cell receptor": "호스트셀 리셉터|호스트 셀 리셉터",
        "calmodulin-dependent adenylyl cyclase":
            "칼보돌린 디펜던트 아데네르 사이클레이즈|칼고돌린 디펜던트 아데네일 사이클레이즈",
        "fluid accumulation": "플루이드 어클로네이션|플루이드 어클루데이션|플루이드 어큐뮬레이션",
        "tissue edema": "티슈 아데마|티슈 이데마|티슈 에데마",
        "immune cell": "이뮨셀|이뮤니티 셀|이문 셀",
        "chemotaxis": "케마텍세스|케모택시스|케모텍시스",
        "zinc dependent metalloprotease": "징크 디펜던트 메탈로 프로테이즈|징크 디펜던트 메탈로프로테이즈",
        "macrophage injury": "매크로파지 인절|매크로파지 인절여|마크로파지 인저리",
        "apoptosis": "아포토시스|어포토시스",
        "cell death": "셀데스|셀세스|셀 데스",
        "phagocytosis": "파고사이토시스|파고사이트 시스|파고사이트시스",
        "immune recognition": "이뮨리코너데이션|이면 리코넥션|이뮨 리코그니션",
        "polyglutamate capsule": "폴리글루타믹 캡슐|폴리 글루타믹 캡슐",
        "capsule": "캡슐",
        "cutaneous anthrax": "크테이너스 안트랙스|쿠테이너스 앤스렉스|코테이너스 앤트렉스|크테니스 안쓰렉스|크티너스",
        "inhalation anthrax": "애널레이션 안트랙스|에널레이션 앤트랙스|인헬레이션 앤트렉스|애널레이지 안쓰렉스|에널레이션 앤스렉스",
        "gastrointestinal anthrax": "갸스트로인테스테놀 안트랙스|게스트로 인테스티널 앤스렉스|가스트로 인테스티노 앤트렉스",
        "mortality": "몰탈리티|모탈리티",
        "aerosol-like spore": "에어로졸라이 스포어|에어로졸 라이크 스포어",
        "intestinal perforation": "인테스테널 퍼포레이션|인테스티널 퍼포레이션",
        "sepsis": "세피스|세프시스|섹시스|셉시스|쎕시스",
        "incubation period": "인큐베이션 피리어드|인큐베이션 피드",
        "painless": "페인레스",
        "lesion": "레션|레전",
        "black necrotic eschar": "블랙 네크로틱 에스칼|블랙 네크로틱 에스카",
        "eschar": "에스칼|애스카",
        "flu": "플루",
        "clinical deterioration": "클리니컬 데토리오레이션|클리니컬 데터리오레이션",
        "dyspnea": "다이셉니아|다이셈리아|디스프니아",
        "chest pain": "체스트 페인",
        "productive cough": "프로덕티브 컵|프로덕티브 코프",
        "hemoptysis": "해머티스|해마프테시스|히몹티시스",
        "radiographic hallmark": "레드 그래픽 허머크|레디오브라픽 허머크|라디오그래픽 홀마크",
        "meningitis": "메넨기|매넹기|메닌자이티스",
        "gi tract": "지아이 트랙|쥐아이 트랙",
        "nausea": "너우샤|너우셔|노지아",
        "vomiting": "버미팅|보미팅",
        "oropharyngeal diseases": "오로팔란지어 디지스|오로페란지어 디지스",
        "toxic effect": "턱색 이펙트|턱숙이 이펙트|톡식 이펙트",
        "shock": "쇼크",
        "blood agar": "블로드 알가|블로드 아가|블러드 아가",
        "culturing": "컬처링",
        "pcr testing": "피셜 테스팅|피씨알 테스팅",
        "immunohistochemistry": "이뮤노 히스토케미스트리|이뮤노 히스토 케미스트리",
        "electron microscopy": "일렉트런 마이크로스코피|일렉트론 마이크로스코피",
        "penicillin": "페네스든|페네슬린|페니실린",
        "doxycycline": "덕세사이클레인|덕세사이클린|독시사이클린",
        "antitoxin therapy": "안티턱슨 트라피|안티탁신 테라피|앤티톡스 엔트로피|안티톡신 테라피",
        "vaccination": "백스네이션|백신에이션|백시네이션",
        "sterilization": "스테롤레이제이션|세럴레이제이션|스테렐라이제이션",
        "decontamination": "디컨테미네이션|디컨템에이션",
        "post-exposure prophylaxis": "포스 익스포저 프로팔렉사세스|포스 익스포셔 프로팔럭사시스|포스트 익스포져 프로팔렉스",
        "antibiotics": "안티바이오틱스",
        "public health response": "퍼블릭 헬스 리스펀스",
    },
}

# canonical_english (lowercased) -> "pipe|separated english variant surface forms".
# Folds abbreviation/synonym spellings of the SAME entity into one term so the
# English-script-preservation metric credits any English rendering (e.g. an output
# that writes "LTB4" where the reference wrote "leukotriene B4"). This is the
# correct layer for canonical normalization — the reference text stays verbatim.
# Variants are chosen NON-NESTING (no variant is a Latin-letter substring of
# another) so count_english_occurrences cannot double count. NOTE: count_english's
# boundary guard is [A-Za-z] only, so "NKCC" already matches inside "NKCC2" via the
# digit boundary — hence NKCC needs no explicit variant; the NKCC2 row is absorbed.
VARIANTS = {
    "diuretics_01": {
        "carbonic anhydrase inhibitor": "CA inhibitor",
        "enac": "epithelial Na channel",
        "potassium sparing diuretics": "potassium-sparing diuretics|K+ sparing diuretics",
    },
    "acuteinflammation_02": {
        "leukotriene b4": "LTB4|LT-B4",
        "major basic protein": "MBP",
        "prostaglandin e2": "PGE2",
    },
    # anthrax: fold the three toxin abbreviations (PA/EF/LF) into their full forms
    # and the hyphenated pXO spellings the outputs use into the reference's pXO1/pXO2.
    # All variants are non-nesting (PA/EF/LF are whitespace/punctuation bounded in the
    # transcripts; pXO-1 is not a Latin-letter substring of pXO1 — the hyphen breaks it).
    "anthrax_01": {
        "protective antigen": "PA",
        "edema factor": "EF",
        "lethal factor": "LF",
        "pxo1": "pXO-1",
        "pxo2": "pXO-2",
    },
}

# canonical_english (lowercased) of rows folded into another term -> forced keep=0
# (their occurrences are counted under the parent term's surface forms instead).
ABSORB = {
    "diuretics_01": {"ca inhibitor", "epithelial na channel", "nkcc2"},
    "acuteinflammation_02": {"ltb4", "lt-b4", "mbp", "pge2"},
    "anthrax_01": {"pa", "ef", "lf"},
}

# canonical_english (lowercased) -> (polarity_group, polarity_value)
POLARITY_TAGS = {
    "diuretics_01": {
        "hypokalemia": ("potassium_serum", "low"),
        "hyperkalemia": ("potassium_serum", "high"),
        "hypocalcemia": ("calcium_serum", "low"),
        "hypercalcemia": ("calcium_serum", "high"),
        "hyponatremia": ("sodium_serum", "low"),
        "hypomagnesemia": ("magnesium_serum", "low"),
        "metabolic acidosis": ("acid_base", "acidosis"),
        "metabolic alkalosis": ("acid_base", "alkalosis"),
    },
    "acuteinflammation_02": {
        "hypotension": ("blood_pressure", "low"),
        "vasodilation": ("vessel_tone", "dilation"),
        "vasoconstriction": ("vessel_tone", "constriction"),
    },
    # anthrax has essentially no hypo/hyper antonym pairs — the medically critical
    # axis here is numeric/entity substitution (mortality %, incubation days, toxin
    # identity), handled in SEMANTIC. No polarity-tagged terms.
    "anthrax_01": {},
}

# A few coarse categories (optional; only used for grouping in the detail table).
def _category(canonical: str) -> str:
    c = canonical.lower()
    drugs = ("furosemide", "bumetanide", "torsemide", "ethacrynic", "spironolactone",
             "eplerenone", "amiloride", "triamterene", "hydrochlorothiazide",
             "chlorothalidone", "metholazone", "indapamide", "acetazolamide",
             "nsaid", "lithium")
    if any(d in c for d in drugs):
        return "drug"
    if c.startswith(("hypo", "hyper")) or "alkalosis" in c or "acidosis" in c:
        return "electrolyte/acid-base"
    return ""


def curate_domain_terms(lecture_id: str) -> None:
    path = td.domain_terms_path(lecture_id)
    drop = DROP.get(lecture_id, set())
    absorb = ABSORB.get(lecture_id, set())
    phon = PHONETIC.get(lecture_id, {})
    pol_tags = POLARITY_TAGS.get(lecture_id, {})
    variants = VARIANTS.get(lecture_id, {})

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        canon = (row.get("canonical_english") or "").strip()
        key = canon.lower()
        if key in drop or key in absorb:
            row["keep"] = "0"
            continue
        row["keep"] = "1"
        if key in variants:
            row["english_variants"] = variants[key]
        if key in phon and phon[key]:
            row["korean_phonetic"] = phon[key]
        if key in pol_tags:
            row["polarity_group"], row["polarity_value"] = pol_tags[key]
        cat = _category(canon)
        if cat:
            row["category"] = cat

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=td.FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in td.FIELDNAMES})


# ---------------------------------------------------------------------------
# 2) POLARITY ITEMS (Claude's draft verdicts — VERIFY before using)
#    verdict per condition: correct / wrong / omitted / "" (unjudged)
# ---------------------------------------------------------------------------
POLARITY_ITEMS = {
    "diuretics_01": [
        # item_id, group, reference_phrase, correct_value, w1, ai, g4o, g4op, why
        ("dur_pol01", "potassium_serum",
         "Carbonic anhydrase inhibitor side effect is hypokalemia",
         "low (hypokalemia)", "correct", "correct", "wrong", "correct",
         "raw gpt-4o rendered it as hyperkalemia (하이퍼칼리미아) — opposite K+ direction"),
        ("dur_pol02", "potassium_serum",
         "Loop diuretics side effect is hypokalemia",
         "low (hypokalemia)", "wrong", "correct", "wrong", "wrong",
         "whisper-1, raw and prompted gpt-4o all said hyperkalemia; only AI_LectureNote corrected it to hypokalemia"),
        ("dur_pol03", "potassium_serum",
         "Potassium-sparing diuretics side effect is hyperkalemia (the exception)",
         "high (hyperkalemia)", "correct", "correct", "correct", "correct",
         "control: when the term truly is hyper, all conditions kept it correct"),
        ("dur_pol04", "calcium_serum",
         "Loop diuretics cause hypocalcemia (calcium loss)",
         "low (hypocalcemia)", "wrong", "correct", "wrong", "wrong",
         "raw ASR conditions said hypercalcemia for loop; AI_LectureNote corrected to hypocalcemia"),
        ("dur_pol05", "calcium_serum",
         "Thiazide causes hypercalcemia",
         "high (hypercalcemia)", "correct", "correct", "correct", "correct",
         "control: hyper direction preserved by all"),
        ("dur_pol06", "sodium_serum",
         "Thiazide side effect is hyponatremia",
         "low (hyponatremia)", "wrong", "correct", "wrong", "wrong",
         "raw ASR said hypernatremia (하이퍼나트리미아); AI_LectureNote corrected to hyponatremia"),
        ("dur_pol07", "treatment_line",
         "Thiazide is first-line for hypertension",
         "first-line (1차)", "wrong", "wrong", "correct", "correct",
         "whisper-1 misheard 1차 as 2차 and AI_LectureNote INHERITED that error; raw/prompted gpt-4o kept 1차"),
    ],
    "acuteinflammation_02": [
        ("acu_pol01", "blood_pressure",
         "Sepsis from cytokine storm causes hypotension",
         "low (hypotension)", "wrong", "wrong", "wrong", "",
         "ALL conditions flipped hypotension to hypertension (하이퍼텐션/고혈압) — sepsis causes low BP, a critical reversal"),
    ],
    # anthrax: no hypo/hyper polarity pairs (see POLARITY_TAGS note); the medical
    # error surface here is substitution/omission, captured in SEMANTIC instead.
    "anthrax_01": [],
}


# ---------------------------------------------------------------------------
# 3) SEMANTIC CLAIMS (Claude's draft drift labels — VERIFY before using)
#    label in: Faithful / Minor rewrite / Omission / Addition / Substitution /
#              Polarity error / Relation error / Unclear
# ---------------------------------------------------------------------------
SEMANTIC = {
    "diuretics_01": [
        # claim_id, reference_claim, ai_output, label, error_type, why
        ("dur_s01",
         "thiazide는 hypertension의 1차 치료제로 사용되고 특히 elderly나 black patient에게 사용된다",
         "thiazide는 hypertension의 2차 치료제로 사용되며 특히 aldosterone blockade 환자에게 사용된다",
         "Substitution", "first-line→second-line; patient group changed", "1",
         "reverses the clinical recommendation (thiazide IS first-line) and invents the wrong patient population"),
        ("dur_s02",
         "ototoxicity는 IV로 고용량을 주입하면 더 위험해진다",
         "ototoxicity는 ibuprofen을 고용량으로 투여하면 더 위험해진다",
         "Addition", "hallucinated drug", "1",
         "invents 'ibuprofen', a drug never mentioned; ototoxicity here is from high-dose IV loop diuretic"),
        ("dur_s03",
         "potassium sparing diuretics가 아닌 다른 모든 diuretics와 똑같이 hypokalemia가 발생한다",
         "칼륨 보존제 diuretics를 사용할 때와 마찬가지로 hypokalemia가 발생한다",
         "Relation error", "negation dropped", "1",
         "drops '아닌' (not), reversing which drug class causes hypokalemia"),
        ("dur_s04",
         "bicarbonate가 소변으로 손실되는 작용기전 때문에 altitude sickness나 metabolic alkalosis 교정에 사용한다",
         "bicarbonate는 소변으로 칼륨이 손실되는 것을 막아주어 탈수증후군이나 대사성 alkalosis를 치료하는 데 사용된다",
         "Relation error", "mechanism garbled; altitude sickness→dehydration", "1",
         "mangles the bicarbonate-loss mechanism and substitutes altitude sickness with dehydration"),
        ("dur_s05",
         "loop diuretics는 Na-K-2Cl cotransporter(NKCC)를 차단한다",
         "loop diuretics는 나트륨, 칼륨, 염소 이온을 신장에서 배설하도록 돕는다",
         "Omission", "mechanism simplified away", "1",
         "drops the specific NKCC transporter mechanism, leaving only a vague description"),
        ("dur_s06",
         "spironolactone, eplerenone은 mineralocorticoid receptor를 차단한다",
         "spironolactone, eplerenone은 mineralocorticoid receptor를 차단하여 ENaC와 Na-K ATPase 전사를 억제한다",
         "Faithful", "", "",
         "mechanism preserved accurately"),
        ("dur_s07",
         "potassium sparing diuretics는 late distal convoluted tubule과 collecting duct에 작용한다",
         "potassium-sparing diuretics는 late distal convoluted tubule과 collecting duct에 작용한다",
         "Faithful", "", "",
         "site of action preserved"),
    ],
    "acuteinflammation_02": [
        ("acu_s01",
         "과도한 cytokine release로 systemic vasodilation이 일어나 hypotension 그리고 DIC까지 갈 수 있다",
         "사이토카인의 과도한 방출로 시스템적인 혈관확장, 고혈압, 그리고 DIC와 같이 위험한 상황으로 이어질 수 있다",
         "Polarity error", "hypotension→hypertension", "1",
         "sepsis causes hypotension (low BP); AI_LectureNote says 고혈압 (hypertension), a critical reversal"),
        ("acu_s02",
         "chronic inflammation으로 전환되면 lymphocyte나 macrophage 중심으로 염증이 진행된다",
         "만성 inflammation으로 전환되면 lipocytes나 macrophages를 중심으로 염증이 진행된다",
         "Substitution", "lymphocyte→lipocyte", "1",
         "lymphocyte (immune cell) replaced by lipocyte (fat cell) — wrong cell lineage"),
        ("acu_s03",
         "arachidonic acid는 COX pathway를 거치면 prostaglandin과 thromboxane을 만든다",
         "arachidonic acid는 COX pathway를 거치면 prostaglandin 그리고 thromboxane은 안되게 된다",
         "Relation error", "negated thromboxane synthesis", "1",
         "states thromboxane is NOT produced, reversing the COX pathway output"),
        ("acu_s04",
         "oxygen-independent killing은 lysozyme, defensin, MBP(major basic protein)를 사용한다",
         "oxygen-independent killing은 lysozyme, defensin, MVP를 사용한다",
         "Substitution", "MBP→MVP", "",
         "wrong acronym (MBP, major basic protein, became MVP)"),
        ("acu_s05",
         "rolling 다음 단계인 firm adhesion에서 단단한 결합이 일어난다",
         "rolling 다음 단계인 Form Addition에서 단단한 결합이 일어난다",
         "Substitution", "firm adhesion→Form Addition", "",
         "the concept name 'firm adhesion' is garbled to 'Form Addition' (inherited from the ASR)"),
        ("acu_s06",
         "phagosome과 lysosome이 합쳐져 phagolysosome을 형성하고 그 내부에서 killing이 일어난다",
         "phagosome과 lysosome이 결합하여 phagolysosome을 형성하고 이 내부에서 killing이 이루어진다",
         "Faithful", "", "",
         "phagolysosome formation preserved accurately"),
    ],
    "anthrax_01": [
        ("ant_s01",
         "Edema factor, 그러니까 부종을 만들어내는 Edema factor 같은 경우에는 Calmodulin-dependent adenylyl Cyclase를 주요하게 이용하고요",
         "Adenine Factor, 즉 부정을 유발하는 Adenine Factor는 calmodulin dependent adenyl cyclase를 중요하게 활용합니다",
         "Substitution", "edema factor→'Adenine Factor' (inherited STT error); 부종→'부정'", "1",
         "a core anthrax toxin component (edema factor) is replaced by the nonexistent 'Adenine Factor'; the pipeline confidently keeps the ASR mishearing in English AND mistranslates the Korean gloss 부종(edema)→부정 — post-processing does not fix the upstream substitution"),
        ("ant_s02",
         "그리고 이제 부종을 만드는 이름처럼 이제 Fluid Accumulation 또는 Tissue Edema를 일으키게 됩니다",
         "이로 인해 fluid accumulation이나 tissue adenoma와 같은 부정적인 영향을 미치게 됩니다",
         "Substitution", "tissue edema→tissue adenoma (inherited STT error)", "1",
         "edema (swelling) becomes adenoma (a benign tumor) — clinically unrelated; inherited from whisper-1 and not corrected"),
        ("ant_s03",
         "그래서 이걸 통해서 Immune Cell의 function을 고장나게 하거나 아니면 Chemotaxis를 일어나게 해서 여러가지 면역 억제를 또 일으키기도 합니다",
         "이를 통해 면역세포의 기능을 손상시키거나 chemotaxis를 유발하여 면역 억제를 일으키기도 합니다",
         "Faithful", "SOURCE error ERR-01 — NOT AI drift", "",
         "speaker's own content slip (says chemotaxis is induced; should be disrupted — see data/anthrax_01/speaker_errata.md ERR-01). AI faithfully reproduces the spoken wording and even restores 'chemotaxis' to English. Fidelity, not a system error; do not score AI wrong here"),
        ("ant_s04",
         "그래서 치료를 하지 않으면 Intestinal Perforation 그러니까 천공이 일어나거나 아니면 Sepsis가 일어날 수 있다라고 이야기를 할 수 있겠습니다",
         "그래서 치료를 하지 않으면 장 폭발이나 출혈이 발생할 수 있습니다",
         "Substitution", "Sepsis→출혈(hemorrhage); Intestinal Perforation→'장 폭발'", "1",
         "the GI-anthrax complication 'Sepsis' is replaced by '출혈'(hemorrhage), a different complication; the English term is dropped and perforation is rendered as the odd '장 폭발'(intestinal explosion)"),
        ("ant_s05",
         "그리고 Inhalation Anthrax 같은 경우에는 이제 Incubation Period가 좀 더 깁니다. 이제 이틀에서 43일 정도까지 가구요",
         "그리고 Anthrax 같은 경우에는 이제 incubation period가 좀 더 깁니다. 이제 이틀에서 43일 정도까지 가구요",
         "Omission", "drops 'Inhalation' type label; chunk left un-post-processed (raw 가구요/되구요)", "1",
         "the entire inhalation-anthrax clinical-course paragraph passes through essentially raw — colloquial fillers (가구요/되구요/할수록) are retained and the type qualifier 'Inhalation' is dropped to a bare 'Anthrax', so incubation 2–43 d reads as generic anthrax. Evidence the post-processing was applied unevenly across chunks"),
        ("ant_s06",
         "그래서 오래가는 만큼 이 Koch의 연구에서 가장 집중적으로 파헤쳐졌던 그러한 박테리아이기도 하구요",
         "이러한 특성으로 탄저균은 많은 연구의 대상이 되었고, 중요한 박테리아 중 하나로 인식되고 있습니다",
         "Omission", "drops named entity 'Koch' and the 'most intensively studied' framing", "",
         "the historical figure Koch is dropped to a vague '많은 연구의 대상'; a factual/attribution detail is lost (not clinically dangerous)"),
        ("ant_s07",
         "그래서 이 캡슐은 polyglutamate capsule로 이루어져 있고",
         "이 캡슐은 polyglutamic acid capsule로 이루어져 있으며",
         "Minor rewrite", "polyglutamate→polyglutamic acid (chemically equivalent)", "",
         "poly-γ-glutamate and polyglutamic acid denote the same capsule polymer; acceptable normalization, English preserved"),
        ("ant_s08",
         "이 치료를 하지 않을 때는 사망률이 굉장히 높습니다. 그래서 90%에서 95%까지 이어지게 되구요",
         "이 형태의 사망률은 치료를 받지 않을 경우 90%에서 95%까지 높습니다",
         "Faithful", "", "",
         "inhalation-anthrax untreated mortality 90–95% preserved exactly — key quantitative fact retained (positive control)"),
        ("ant_s09",
         "첫번째는 Cutaneous Anthrax 두번째는 Inhalation Anthrax 그리고 마지막으로는 Gastrointestinal Anthrax 이렇게 세개로 나눠지게 됩니다",
         "첫 번째는 Cutaneous Anthrax, 두 번째는 Inhalation Anthrax 그리고 마지막으로는 Gastrointestinal Anthrax으로 나누어집니다",
         "Faithful", "restores whisper 'Annihilation Anthrax'→Inhalation", "",
         "AI restores all three type names in English where raw whisper-1 misheard the second as 'Annihilation Anthrax' — post-processing fixing an upstream substitution (positive control)"),
    ],
}


def main():
    for lecture_id in ("diuretics_01", "acuteinflammation_02", "anthrax_01"):
        print(f"[{lecture_id}] curating domain_terms")
        curate_domain_terms(lecture_id)
    print("Done. Hand-verify domain_terms.csv (see ANNOTATION_GUIDE.md).")


if __name__ == "__main__":
    main()
