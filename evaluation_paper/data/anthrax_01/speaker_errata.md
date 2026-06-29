# anthrax_01 — Speaker errata (실언 기록)

정책: [../../ANNOTATION_GUIDE.md](../../ANNOTATION_GUIDE.md) 0번 절.
**실언(speaker가 테이프에서 실제로 틀리게 말함)은 reference에 verbatim으로 남기고, 여기에 별도 표시한다.**
의학적으로 정정된 내용을 reference에 끼워넣지 않는다. AI/STT 점수에서도 system 오류로 매기지 않는다
(reference 대비 flip이 아니라 source 자체의 오류이므로).

---

## ERR-01 — chemotaxis 인과방향

- **위치**: Edema factor 설명부 (Calmodulin-dependent adenylyl cyclase → fluid accumulation / tissue edema 직후).
- **발화(녹음, reference verbatim)**:
  > 그래서 이걸 통해서 Immune Cell의 function을 고장나게 하거나 아니면 **Chemotaxis를 일어나게 해서** 여러가지 면역 억제를 또 일으키기도 합니다.
- **녹음자 정정**:
  > chemotaxis의 **교란을 일으킨다**는 것이 더 올바른 표현. Chemotaxis 자체에 '교란'의 의미가 포함된 것으로 착각했음. (Edema/Lethal factor는 호중구 등 면역세포의 chemotaxis를 *방해/저해*하여 면역을 억제한다 — chemotaxis를 *유발*하는 것이 아니다.)
- **정정 사유**: 의학적으로 toxin은 chemotaxis를 disrupt/impair → 면역억제. "일어나게(induce)"는 인과방향이 반대.

### 4개 조건 출력 (이 문장)
| 조건 | 출력 | 비고 |
| --- | --- | --- |
| reference | "Chemotaxis를 **일어나게 해서** … 면역 억제" | 실언 원본 |
| whisper1 | "Chemotaxis를 **일어나게 해서** … 면역 억제" | 화자 발화 그대로 |
| ai_lecturenote | "chemotaxis를 **유발하여** … 면역 억제" | 화자 발화 그대로 + 영어 표기 복원 |
| gpt4o | "케마텍세스를 **일어나게 해서** … 면역 억제" | 음차 |
| gpt4o_prompted | "케마텍세스를 **일으나게 해서** … 면역 억제" | 음차 |

### 점수 처리 규정
- **reference.txt**: 수정 금지 (verbatim "일어나게 해서" 유지).
- **semantic_review.csv** (이 문장 row): ai_lecturenote = **Faithful**,
  notes = "원천 실언(ERR-01), AI가 만든 drift 아님. 4개 조건 모두 화자 발화 재현."
- **polarity_review.csv**: polarity flip row 아님 (reference 대비 flip 아님).

### 논문 함의 (Discussion/Limitations 소재)
충실한 전사·노트 시스템은 화자의 **내용 오류까지 그대로 재현**한다 — 전사 충실도(fidelity)로는
바람직하지만, **의학적 사실검증은 하지 못한다**. 이 정정은 사람(강의자)의 편집 레이어가 잡아낸 것으로,
도구는 제공하지 못하는 부분. "transcription fidelity ≠ content correctness"의 경계를 깔끔히 보여주는 사례.
