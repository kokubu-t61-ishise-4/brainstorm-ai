"""BrainSpark - AIブレインストーミングアシスタント"""
import streamlit as st
from groq import Groq
import json
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="BrainSpark",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .idea-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .score-high { color: #28a745; font-weight: bold; }
    .score-mid { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; font-weight: bold; }
    .question-box {
        background: #e8f4f8;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #17a2b8;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# フレームワーク定義
FRAMEWORKS = {
    "SCAMPER": {
        "description": "7つの視点で既存アイデアを変化させる",
        "prompts": [
            ("S - Substitute（代用）", "何か別のもので代用できないか？素材、人、場所、プロセスを変えたら？"),
            ("C - Combine（組み合わせ）", "他のアイデア、機能、製品と組み合わせられないか？"),
            ("A - Adapt（適応）", "他の分野や用途に適応できないか？過去の成功事例を応用できないか？"),
            ("M - Modify（修正）", "形、色、大きさ、機能を変更したら？強調・拡張したら？"),
            ("P - Put to other uses（転用）", "別の使い方はできないか？他の市場で使えないか？"),
            ("E - Eliminate（削除）", "何かを取り除いたら？シンプルにしたら？"),
            ("R - Reverse/Rearrange（逆転・再配置）", "順序を変えたら？逆にしたら？役割を入れ替えたら？"),
        ]
    },
    "6W2H": {
        "description": "8つの質問で企画を網羅的に整理",
        "prompts": [
            ("What（何を）", "具体的に何をするのか？"),
            ("Why（なぜ）", "なぜそれをやるのか？目的・背景は？"),
            ("Who（誰が）", "誰が実行するのか？担当者は？"),
            ("Whom（誰に）", "誰に向けてか？ターゲットは？"),
            ("When（いつ）", "いつ実行するか？スケジュールは？"),
            ("Where（どこで）", "どこで実施するか？チャネルは？"),
            ("How（どうやって）", "どのような方法で行うか？"),
            ("How much（いくらで）", "予算は？コストは？"),
        ]
    },
    "オズボーンのチェックリスト": {
        "description": "9つの質問でアイデアを拡張",
        "prompts": [
            ("転用", "他に使い道はないか？"),
            ("応用", "他からアイデアを借りられないか？"),
            ("変更", "色、形、音、意味を変えたら？"),
            ("拡大", "大きく、長く、強く、多くしたら？"),
            ("縮小", "小さく、短く、軽く、少なくしたら？"),
            ("代用", "他の素材、人、方法で代用したら？"),
            ("再配置", "要素を並べ替えたら？レイアウトを変えたら？"),
            ("逆転", "上下、前後、役割を逆にしたら？"),
            ("結合", "組み合わせたら？混ぜたら？"),
        ]
    },
    "自由発想": {
        "description": "フレームワークなしで自由にアイデア出し",
        "prompts": [
            ("自由発想", "制約なく自由にアイデアを考える"),
        ]
    }
}

# 評価軸定義
EVALUATION_CRITERIA = [
    ("実現可能性", "技術的・リソース的に実現できるか"),
    ("コスト効率", "費用対効果は高いか"),
    ("インパクト", "効果・影響は大きいか"),
    ("新規性", "新しさ・独自性はあるか"),
]


def init_groq():
    """Groq APIの初期化"""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        return client
    except Exception as e:
        st.error(f"APIキーの設定エラー: {e}")
        return None


def call_llm(client, prompt: str) -> str:
    """LLMを呼び出す"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"エラーが発生しました: {e}"


def analyze_theme_and_ask_questions(client, theme: str) -> dict:
    """テーマを分析し、追加質問が必要か判断する"""
    prompt = f"""
あなたはアイデアソンのファシリテーターです。
以下のテーマについて、最高精度のアイデアを出すために追加情報が必要かどうか判断してください。

テーマ: {theme}

以下のJSON形式で回答してください：
{{
    "needs_clarification": true または false,
    "questions": [
        {{"id": "target", "question": "ターゲット層は誰ですか？", "options": ["10-20代", "30-40代", "50代以上", "全年齢"]}},
        {{"id": "budget", "question": "予算規模は？", "options": ["〜10万円", "10-50万円", "50-100万円", "100万円以上", "未定"]}},
        ...
    ],
    "reason": "追加質問が必要な理由（または不要な理由）"
}}

追加質問のルール：
- テーマが具体的で十分な情報がある場合は needs_clarification: false
- 漠然としたテーマの場合は needs_clarification: true
- 質問は最大4つまで
- 各質問には3-5個の選択肢を用意
- 選択肢の最後に「その他」は不要（自由入力欄は別途用意される）

よくある質問の例：
- ターゲット層（年齢、職業、属性など）
- 予算規模
- 実施時期・期限
- 制約条件（技術的、法的、リソースなど）
- 目的・ゴール
- 既存の取り組み・競合状況
"""

    try:
        response = call_llm(client, prompt)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response[json_start:json_end])
    except:
        pass
    return {"needs_clarification": False, "questions": [], "reason": "分析できませんでした"}


def generate_ideas_with_context(client, theme: str, framework: str, additional_info: dict, num_ideas: int = 5) -> str:
    """追加情報を含めてアイデアを生成"""
    framework_info = FRAMEWORKS[framework]

    # 追加情報をテキスト化
    context_text = ""
    if additional_info:
        context_lines = []
        for key, value in additional_info.items():
            if value:
                context_lines.append(f"- {key}: {value}")
        if context_lines:
            context_text = "\n追加情報:\n" + "\n".join(context_lines)

    if framework == "自由発想":
        prompt = f"""
あなたはアイデアソンのファシリテーターです。
以下のテーマと追加情報に基づいて、創造的で実用的なアイデアを{num_ideas}個生成してください。

テーマ: {theme}
{context_text}

各アイデアは以下の形式で出力してください：
1. [アイデアのタイトル]: [具体的な説明（50-100字程度）]

追加情報を十分に考慮し、ターゲットや制約に合った、実現可能かつ斬新なアイデアを出してください。
"""
    else:
        viewpoints = "\n".join([f"- {name}: {desc}" for name, desc in framework_info["prompts"]])
        prompt = f"""
あなたはアイデアソンのファシリテーターです。
「{framework}」フレームワークを使って、以下のテーマについてアイデアを生成してください。

テーマ: {theme}
{context_text}

フレームワークの視点:
{viewpoints}

各視点から1つずつ、合計{len(framework_info["prompts"])}個のアイデアを出してください。
形式:
【視点名】[アイデアのタイトル]: [具体的な説明（50-100字程度）]

追加情報を十分に考慮し、ターゲットや制約に合った、実現可能かつ創造的なアイデアを出してください。
"""

    return call_llm(client, prompt)


def deepen_idea(client, idea: str, theme: str, additional_info: dict = None) -> str:
    """アイデアを深掘り"""
    context_text = ""
    if additional_info:
        context_lines = []
        for key, value in additional_info.items():
            if value:
                context_lines.append(f"- {key}: {value}")
        if context_lines:
            context_text = "\n追加情報:\n" + "\n".join(context_lines)

    prompt = f"""
以下のアイデアを深掘りして、より具体的な企画案に発展させてください。

テーマ: {theme}
アイデア: {idea}
{context_text}

以下の観点で詳細化してください：
1. 具体的な実施内容（3-5ステップ）
2. 必要なリソース
3. 期待される効果
4. 想定されるリスクと対策
5. 成功のポイント

簡潔に、箇条書きで回答してください。
"""
    return call_llm(client, prompt)


def combine_ideas(client, idea1: str, idea2: str, theme: str) -> str:
    """2つのアイデアを組み合わせ"""
    prompt = f"""
以下の2つのアイデアを組み合わせて、新しいアイデアを3つ生成してください。

テーマ: {theme}
アイデア1: {idea1}
アイデア2: {idea2}

単純な足し算ではなく、相乗効果が生まれるような創造的な組み合わせを考えてください。
各アイデアは「タイトル: 説明」の形式で出力してください。
"""
    return call_llm(client, prompt)


def ai_evaluate_idea(client, idea: str, theme: str) -> dict:
    """AIでアイデアを評価"""
    prompt = f"""
以下のアイデアを評価してください。

テーマ: {theme}
アイデア: {idea}

以下の4つの観点で、それぞれ1〜5点で評価し、理由も簡潔に述べてください。
必ず以下のJSON形式で回答してください：

{{
    "実現可能性": {{"score": 4, "reason": "理由"}},
    "コスト効率": {{"score": 3, "reason": "理由"}},
    "インパクト": {{"score": 5, "reason": "理由"}},
    "新規性": {{"score": 4, "reason": "理由"}}
}}
"""

    try:
        response = call_llm(client, prompt)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response[json_start:json_end])
    except:
        pass
    return None


# セッション状態の初期化
if "ideas" not in st.session_state:
    st.session_state.ideas = []
if "evaluations" not in st.session_state:
    st.session_state.evaluations = {}
if "theme" not in st.session_state:
    st.session_state.theme = ""
if "deepened" not in st.session_state:
    st.session_state.deepened = {}
if "combined" not in st.session_state:
    st.session_state.combined = []
if "clarification_questions" not in st.session_state:
    st.session_state.clarification_questions = None
if "additional_info" not in st.session_state:
    st.session_state.additional_info = {}
if "waiting_for_answers" not in st.session_state:
    st.session_state.waiting_for_answers = False
if "skip_questions" not in st.session_state:
    st.session_state.skip_questions = False

# API初期化
client = init_groq()

# サイドバー
with st.sidebar:
    st.markdown("### ⚡ BrainSpark")
    st.markdown("---")

    # フレームワーク選択
    st.markdown("#### 🎯 フレームワーク")
    selected_framework = st.selectbox(
        "思考法を選択",
        list(FRAMEWORKS.keys()),
        help="アイデア発想の切り口を選びます"
    )
    st.caption(FRAMEWORKS[selected_framework]["description"])

    st.markdown("---")

    # 追加情報表示
    if st.session_state.additional_info:
        st.markdown("#### 📋 設定済み情報")
        for key, value in st.session_state.additional_info.items():
            if value:
                st.caption(f"• {key}: {value}")
        st.markdown("---")

    # 統計表示
    if st.session_state.ideas:
        st.markdown("#### 📊 セッション統計")
        st.metric("生成アイデア数", len(st.session_state.ideas))
        evaluated_count = len(st.session_state.evaluations)
        st.metric("評価済み", f"{evaluated_count}/{len(st.session_state.ideas)}")

        if st.session_state.evaluations:
            avg_scores = []
            for eval_data in st.session_state.evaluations.values():
                if eval_data:
                    total = sum(v["score"] for v in eval_data.values())
                    avg_scores.append(total)
            if avg_scores:
                st.metric("平均スコア", f"{sum(avg_scores)/len(avg_scores):.1f}/20")

    st.markdown("---")

    # エクスポート
    if st.session_state.ideas:
        st.markdown("#### 💾 エクスポート")
        export_data = {
            "テーマ": st.session_state.theme,
            "追加情報": st.session_state.additional_info,
            "生成日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "アイデア": st.session_state.ideas,
            "評価": st.session_state.evaluations,
        }
        st.download_button(
            "JSONでダウンロード",
            json.dumps(export_data, ensure_ascii=False, indent=2),
            "ideas.json",
            "application/json",
            use_container_width=True
        )

        # テキスト形式
        text_export = f"テーマ: {st.session_state.theme}\n"
        if st.session_state.additional_info:
            text_export += "追加情報:\n"
            for key, value in st.session_state.additional_info.items():
                if value:
                    text_export += f"  - {key}: {value}\n"
        text_export += f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        text_export += "【アイデア一覧】\n"
        for i, idea in enumerate(st.session_state.ideas, 1):
            text_export += f"{i}. {idea}\n"
            if idea in st.session_state.evaluations:
                eval_data = st.session_state.evaluations[idea]
                total = sum(v["score"] for v in eval_data.values())
                text_export += f"   → 評価スコア: {total}/20\n"

        st.download_button(
            "テキストでダウンロード",
            text_export,
            "ideas.txt",
            "text/plain",
            use_container_width=True
        )

    st.markdown("---")
    if st.button("🗑️ リセット", use_container_width=True):
        st.session_state.ideas = []
        st.session_state.evaluations = {}
        st.session_state.theme = ""
        st.session_state.deepened = {}
        st.session_state.combined = []
        st.session_state.clarification_questions = None
        st.session_state.additional_info = {}
        st.session_state.waiting_for_answers = False
        st.session_state.skip_questions = False
        st.rerun()

# メインコンテンツ
st.markdown('<p class="main-header">⚡ BrainSpark</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AIと一緒にブレインストーミング。最高精度のアイデアを生み出すために、必要な情報をヒアリングします</p>', unsafe_allow_html=True)

if not client:
    st.warning("Groq APIキーを設定してください（.streamlit/secrets.toml）")
    st.stop()

# テーマ入力
col1, col2 = st.columns([3, 1])
with col1:
    theme = st.text_input(
        "🎯 テーマを入力",
        placeholder="例: 新しいお茶の商品企画、社内コミュニケーション改善、夏のイベント企画...",
        value=st.session_state.theme
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("✨ アイデアを生成", type="primary", use_container_width=True)

# テーマ分析と追加質問
if analyze_btn and theme:
    st.session_state.theme = theme
    st.session_state.skip_questions = False

    with st.spinner("テーマを分析中..."):
        analysis = analyze_theme_and_ask_questions(client, theme)

        if analysis.get("needs_clarification") and analysis.get("questions"):
            st.session_state.clarification_questions = analysis
            st.session_state.waiting_for_answers = True
        else:
            # 追加質問不要 → 直接アイデア生成
            st.session_state.waiting_for_answers = False
            st.session_state.clarification_questions = None

            with st.spinner(f"「{selected_framework}」でアイデアを生成中..."):
                result = generate_ideas_with_context(client, theme, selected_framework, st.session_state.additional_info)

                lines = [line.strip() for line in result.split("\n") if line.strip()]
                new_ideas = []
                for line in lines:
                    if any(c.isalnum() for c in line) and len(line) > 10:
                        clean = line.lstrip("0123456789.-）)】・ ")
                        if clean and clean not in st.session_state.ideas:
                            new_ideas.append(clean)

                st.session_state.ideas.extend(new_ideas[:10])
    st.rerun()

# 追加質問の表示と回答収集
if st.session_state.waiting_for_answers and st.session_state.clarification_questions:
    questions = st.session_state.clarification_questions.get("questions", [])
    reason = st.session_state.clarification_questions.get("reason", "")

    st.markdown('<div class="question-box">', unsafe_allow_html=True)
    st.markdown("### 💬 より良いアイデアを出すために教えてください")
    if reason:
        st.caption(reason)
    st.markdown('</div>', unsafe_allow_html=True)

    answers = {}
    for q in questions:
        q_id = q.get("id", q.get("question", ""))
        question_text = q.get("question", "")
        options = q.get("options", [])

        if options:
            selected = st.selectbox(
                question_text,
                ["選択してください"] + options + ["その他（自由入力）"],
                key=f"q_{q_id}"
            )

            if selected == "その他（自由入力）":
                custom_answer = st.text_input(f"{question_text}（自由入力）", key=f"custom_{q_id}")
                answers[question_text] = custom_answer
            elif selected != "選択してください":
                answers[question_text] = selected
        else:
            answers[question_text] = st.text_input(question_text, key=f"q_{q_id}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 この情報でアイデアを生成", type="primary", use_container_width=True):
            st.session_state.additional_info = answers
            st.session_state.waiting_for_answers = False

            with st.spinner(f"「{selected_framework}」でアイデアを生成中..."):
                result = generate_ideas_with_context(client, st.session_state.theme, selected_framework, answers)

                lines = [line.strip() for line in result.split("\n") if line.strip()]
                new_ideas = []
                for line in lines:
                    if any(c.isalnum() for c in line) and len(line) > 10:
                        clean = line.lstrip("0123456789.-）)】・ ")
                        if clean and clean not in st.session_state.ideas:
                            new_ideas.append(clean)

                st.session_state.ideas.extend(new_ideas[:10])
            st.rerun()

    with col2:
        if st.button("⏭️ スキップして生成", use_container_width=True):
            st.session_state.waiting_for_answers = False
            st.session_state.skip_questions = True

            with st.spinner(f"「{selected_framework}」でアイデアを生成中..."):
                result = generate_ideas_with_context(client, st.session_state.theme, selected_framework, {})

                lines = [line.strip() for line in result.split("\n") if line.strip()]
                new_ideas = []
                for line in lines:
                    if any(c.isalnum() for c in line) and len(line) > 10:
                        clean = line.lstrip("0123456789.-）)】・ ")
                        if clean and clean not in st.session_state.ideas:
                            new_ideas.append(clean)

                st.session_state.ideas.extend(new_ideas[:10])
            st.rerun()

# タブ表示
if st.session_state.ideas and not st.session_state.waiting_for_answers:
    tab1, tab2, tab3 = st.tabs(["📝 アイデア一覧", "⭐ 評価", "🔀 組み合わせ"])

    with tab1:
        st.markdown("### 生成されたアイデア")

        for i, idea in enumerate(st.session_state.ideas):
            with st.container():
                col1, col2, col3 = st.columns([6, 1, 1])

                with col1:
                    if idea in st.session_state.evaluations:
                        eval_data = st.session_state.evaluations[idea]
                        total = sum(v["score"] for v in eval_data.values())
                        score_class = "score-high" if total >= 15 else "score-mid" if total >= 10 else "score-low"
                        st.markdown(f'<span class="{score_class}">[{total}/20点]</span> {idea}', unsafe_allow_html=True)
                    else:
                        st.markdown(f"💡 {idea}")

                with col2:
                    if st.button("深掘り", key=f"deep_{i}"):
                        with st.spinner("深掘り中..."):
                            result = deepen_idea(client, idea, st.session_state.theme, st.session_state.additional_info)
                            st.session_state.deepened[idea] = result

                with col3:
                    if st.button("削除", key=f"del_{i}"):
                        st.session_state.ideas.remove(idea)
                        if idea in st.session_state.evaluations:
                            del st.session_state.evaluations[idea]
                        st.rerun()

                if idea in st.session_state.deepened:
                    with st.expander("📖 深掘り結果", expanded=True):
                        st.markdown(st.session_state.deepened[idea])

                st.markdown("---")

    with tab2:
        st.markdown("### アイデア評価")
        st.caption("各アイデアを4つの観点で評価します（AI自動評価 or 手動評価）")

        if st.button("🤖 すべてAIで評価", type="secondary"):
            progress = st.progress(0)
            for i, idea in enumerate(st.session_state.ideas):
                if idea not in st.session_state.evaluations:
                    result = ai_evaluate_idea(client, idea, st.session_state.theme)
                    if result:
                        st.session_state.evaluations[idea] = result
                progress.progress((i + 1) / len(st.session_state.ideas))
            st.rerun()

        st.markdown("---")

        for i, idea in enumerate(st.session_state.ideas):
            with st.expander(f"💡 {idea[:50]}...", expanded=False):

                col1, col2 = st.columns([1, 1])

                with col1:
                    st.markdown("**手動評価**")
                    scores = {}
                    for criterion, desc in EVALUATION_CRITERIA:
                        scores[criterion] = st.slider(
                            f"{criterion}",
                            1, 5,
                            st.session_state.evaluations.get(idea, {}).get(criterion, {}).get("score", 3),
                            key=f"slider_{i}_{criterion}",
                            help=desc
                        )

                    if st.button("評価を保存", key=f"save_eval_{i}"):
                        st.session_state.evaluations[idea] = {
                            criterion: {"score": scores[criterion], "reason": "手動評価"}
                            for criterion in scores
                        }
                        st.success("保存しました")

                with col2:
                    st.markdown("**AI評価**")
                    if st.button("AIで評価", key=f"ai_eval_{i}"):
                        with st.spinner("評価中..."):
                            result = ai_evaluate_idea(client, idea, st.session_state.theme)
                            if result:
                                st.session_state.evaluations[idea] = result
                                st.rerun()

                    if idea in st.session_state.evaluations:
                        eval_data = st.session_state.evaluations[idea]
                        total = 0
                        for criterion, data in eval_data.items():
                            score = data["score"]
                            total += score
                            stars = "★" * score + "☆" * (5 - score)
                            st.markdown(f"**{criterion}**: {stars}")
                            if data.get("reason") and data["reason"] != "手動評価":
                                st.caption(data["reason"])

                        score_class = "score-high" if total >= 15 else "score-mid" if total >= 10 else "score-low"
                        st.markdown(f'**総合**: <span class="{score_class}">{total}/20点</span>', unsafe_allow_html=True)

        if st.session_state.evaluations:
            st.markdown("---")
            st.markdown("### 🏆 評価ランキング")

            ranked = []
            for idea, eval_data in st.session_state.evaluations.items():
                total = sum(v["score"] for v in eval_data.values())
                ranked.append((idea, total))

            ranked.sort(key=lambda x: x[1], reverse=True)

            for rank, (idea, score) in enumerate(ranked[:5], 1):
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                st.markdown(f"{medal} **{score}点** - {idea[:60]}...")

    with tab3:
        st.markdown("### アイデアの組み合わせ")
        st.caption("2つのアイデアを選んで、新しいアイデアを生成します")

        if len(st.session_state.ideas) >= 2:
            col1, col2 = st.columns(2)

            with col1:
                idea1 = st.selectbox("アイデア1", st.session_state.ideas, key="combine1")
            with col2:
                remaining = [i for i in st.session_state.ideas if i != idea1]
                idea2 = st.selectbox("アイデア2", remaining, key="combine2")

            if st.button("🔀 組み合わせる", type="primary"):
                with st.spinner("新しいアイデアを生成中..."):
                    result = combine_ideas(client, idea1, idea2, st.session_state.theme)
                    st.session_state.combined.append({
                        "idea1": idea1,
                        "idea2": idea2,
                        "result": result
                    })

            for combo in st.session_state.combined:
                with st.expander(f"🔀 {combo['idea1'][:20]}... × {combo['idea2'][:20]}..."):
                    st.markdown(combo["result"])

                    if st.button("このアイデアを追加", key=f"add_combo_{id(combo)}"):
                        lines = [l.strip() for l in combo["result"].split("\n") if l.strip() and len(l) > 10]
                        for line in lines[:3]:
                            clean = line.lstrip("0123456789.-）)】・ ")
                            if clean not in st.session_state.ideas:
                                st.session_state.ideas.append(clean)
                        st.rerun()
        else:
            st.info("組み合わせるには2つ以上のアイデアが必要です")

elif not st.session_state.waiting_for_answers:
    # 初期表示
    st.markdown("---")
    st.markdown("### 🚀 使い方")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1. テーマを入力")
        st.markdown("ブレインストーミングしたいテーマを入力します")

    with col2:
        st.markdown("#### 2. 質問に回答")
        st.markdown("AIが追加情報を聞いてくるので、回答すると精度UP")

    with col3:
        st.markdown("#### 3. アイデアを評価")
        st.markdown("AIまたは手動で評価し、優先順位をつけます")

    st.markdown("---")
    st.markdown("### 📚 フレームワーク一覧")

    for name, info in FRAMEWORKS.items():
        with st.expander(f"**{name}** - {info['description']}"):
            for prompt_name, prompt_desc in info["prompts"]:
                st.markdown(f"- **{prompt_name}**: {prompt_desc}")
