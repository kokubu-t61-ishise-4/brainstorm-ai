"""アイデアソン・アシスタント - ブレインストーミングAIエージェント"""
import streamlit as st
from groq import Groq
import json
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="アイデアソン・アシスタント",
    page_icon="💡",
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


def generate_ideas(client, theme: str, framework: str, num_ideas: int = 5) -> str:
    """アイデアを生成"""
    framework_info = FRAMEWORKS[framework]

    if framework == "自由発想":
        prompt = f"""
あなたはアイデアソンのファシリテーターです。
以下のテーマについて、創造的で実用的なアイデアを{num_ideas}個生成してください。

テーマ: {theme}

各アイデアは以下の形式で出力してください：
1. [アイデアのタイトル]: [具体的な説明（50-100字程度）]

多様な視点から、実現可能かつ斬新なアイデアを出してください。
"""
    else:
        viewpoints = "\n".join([f"- {name}: {desc}" for name, desc in framework_info["prompts"]])
        prompt = f"""
あなたはアイデアソンのファシリテーターです。
「{framework}」フレームワークを使って、以下のテーマについてアイデアを生成してください。

テーマ: {theme}

フレームワークの視点:
{viewpoints}

各視点から1つずつ、合計{len(framework_info["prompts"])}個のアイデアを出してください。
形式:
【視点名】[アイデアのタイトル]: [具体的な説明（50-100字程度）]

実現可能かつ創造的なアイデアを出してください。
"""

    return call_llm(client, prompt)


def deepen_idea(client, idea: str, theme: str) -> str:
    """アイデアを深掘り"""
    prompt = f"""
以下のアイデアを深掘りして、より具体的な企画案に発展させてください。

テーマ: {theme}
アイデア: {idea}

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

# API初期化
client = init_groq()

# サイドバー
with st.sidebar:
    st.markdown("### 💡 アイデアソン・アシスタント")
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
        text_export = f"テーマ: {st.session_state.theme}\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
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
        st.rerun()

# メインコンテンツ
st.markdown('<p class="main-header">💡 アイデアソン・アシスタント</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AIと一緒にブレインストーミング。フレームワークを活用して効率的にアイデアを発想・評価</p>', unsafe_allow_html=True)

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
    generate_btn = st.button("✨ アイデアを生成", type="primary", use_container_width=True)

if generate_btn and theme:
    st.session_state.theme = theme
    with st.spinner(f"「{selected_framework}」でアイデアを生成中..."):
        result = generate_ideas(client, theme, selected_framework)

        # 結果をパース（シンプルに行ごとに分割）
        lines = [line.strip() for line in result.split("\n") if line.strip()]
        new_ideas = []
        for line in lines:
            if any(c.isalnum() for c in line) and len(line) > 10:
                # 番号や記号を除去
                clean = line.lstrip("0123456789.-）)】・ ")
                if clean and clean not in st.session_state.ideas:
                    new_ideas.append(clean)

        st.session_state.ideas.extend(new_ideas[:10])  # 最大10個追加
        st.rerun()

# タブ表示
if st.session_state.ideas:
    tab1, tab2, tab3 = st.tabs(["📝 アイデア一覧", "⭐ 評価", "🔀 組み合わせ"])

    with tab1:
        st.markdown("### 生成されたアイデア")

        for i, idea in enumerate(st.session_state.ideas):
            with st.container():
                col1, col2, col3 = st.columns([6, 1, 1])

                with col1:
                    # 評価済みならスコア表示
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
                            result = deepen_idea(client, idea, st.session_state.theme)
                            st.session_state.deepened[idea] = result

                with col3:
                    if st.button("削除", key=f"del_{i}"):
                        st.session_state.ideas.remove(idea)
                        if idea in st.session_state.evaluations:
                            del st.session_state.evaluations[idea]
                        st.rerun()

                # 深掘り結果表示
                if idea in st.session_state.deepened:
                    with st.expander("📖 深掘り結果", expanded=True):
                        st.markdown(st.session_state.deepened[idea])

                st.markdown("---")

    with tab2:
        st.markdown("### アイデア評価")
        st.caption("各アイデアを4つの観点で評価します（AI自動評価 or 手動評価）")

        # 一括AI評価
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

        # 個別評価
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

                    # 評価結果表示
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

        # ランキング表示
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

            # 組み合わせ結果表示
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

else:
    # 初期表示
    st.markdown("---")
    st.markdown("### 🚀 使い方")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1. テーマを入力")
        st.markdown("ブレインストーミングしたいテーマを入力します")

    with col2:
        st.markdown("#### 2. フレームワークを選択")
        st.markdown("SCAMPER、6W2Hなどの思考法を選びます")

    with col3:
        st.markdown("#### 3. アイデアを評価")
        st.markdown("AIまたは手動で評価し、優先順位をつけます")

    st.markdown("---")
    st.markdown("### 📚 フレームワーク一覧")

    for name, info in FRAMEWORKS.items():
        with st.expander(f"**{name}** - {info['description']}"):
            for prompt_name, prompt_desc in info["prompts"]:
                st.markdown(f"- **{prompt_name}**: {prompt_desc}")
