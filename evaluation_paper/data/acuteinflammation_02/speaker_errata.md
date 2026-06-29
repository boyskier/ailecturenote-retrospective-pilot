# acuteinflammation_02 — Speaker errata (실언 기록)

정책: [../../ANNOTATION_GUIDE.md](../../ANNOTATION_GUIDE.md) 0번 절.
**실언(speaker가 테이프에서 실제로 틀리게 말함)은 reference에 verbatim으로 남기고, 여기에 별도 표시한다.**
의학적으로 정정된 내용을 reference에 끼워넣지 않는다. AI/STT 점수에서도 system 오류로 매기지 않는다
(reference 대비 flip이 아니라 source 자체의 오류이므로).

---

## ERR-01 — acute phase protein 구조적 모호성

- **위치**: Systemic effects 설명부 (fever → IL-1/TNF-α → prostaglandin E2 설명 직후).
- **발화(녹음, reference verbatim)**:
  > 그 다음에 acute phase protein들이 있는데 이거는 이제 liver에서 **CRP나 fibrinogen 생성을 증가시키게** 됩니다.
- **녹음자 정정**:
  > CRP, fibrinogen이 acute phase protein의 **예시(instance)**다. 올바른 표현은 "liver에서 CRP, fibrinogen **같은** acute phase protein의 생성이 증가한다"여야 함. 발화된 구조("APP이 CRP/fibrinogen 생성을 증가시킨다")는 APP와 CRP/fibrinogen이 별개 개체인 것처럼 읽혀 인과 방향 혼동 소지가 있음.
- **정정 사유**: 의학적으로 cytokine(IL-6 등) → liver → APP(CRP, fibrinogen 등) 생성 증가. APP가 CRP/fibrinogen을 *유도하는* 것이 아니라, CRP/fibrinogen이 APP *자체*다.

### 4개 조건 출력 (이 문장)
| 조건 | 출력 | 비고 |
| --- | --- | --- |
| reference | "acute phase protein들이 있는데 이거는 liver에서 **CRP나 fibrinogen 생성을 증가시키게** 됩니다" | 발화 원본 (모호) |
| whisper1 | (한글 음차로 유사 재현) | 화자 발화 그대로 |
| ai_lecturenote | "acute phase protein은 간에서 **CRP나 fibrinogen 생성을 증가시킵니다**" | 화자 발화 구조 그대로 재현 |
| gpt4o | (유사 재현) | |
| gpt4o_prompted | (유사 재현) | |

### 점수 처리 규정
- **reference.txt**: 수정 금지 (verbatim 유지).
- **semantic_review.csv** (이 문장 row): ai_lecturenote = **Faithful**,
  notes = "원천 발화 구조적 모호성(ERR-01), AI가 만든 drift 아님. 4개 조건 모두 화자 발화 구조 재현."
- **polarity_review.csv**: polarity flip row 아님 (reference 대비 flip 아님).

### 논문 함의 (Discussion/Limitations 소재)
발화 원문 자체에 구조적 모호성("APP이 CRP를 생성한다" vs "CRP가 APP의 일종이다")이 있을 때,
충실한 전사 시스템은 이 모호성을 그대로 재현한다. **전사 충실도 ≠ 개념 명확성**. 사람 편집 레이어가
없으면 청취자도, AI도 구조 모호성을 교정하지 못함.
