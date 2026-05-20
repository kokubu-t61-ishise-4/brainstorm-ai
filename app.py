"""BrainSpark - AIブレインストーミングアシスタント"""
import streamlit as st
from groq import Groq
from tavily import TavilyClient
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
    .search-box {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .search-result {
        background: #f8f9fa;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #dee2e6;
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
        st.error(f"Groq APIキーの設定エラー: {e}")
        return None


def init_tavily():
    """Tavily APIの初期化"""
    try:
        client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
        return client
    except Exception as e:
        st.warning(f"Tavily APIキーが設定されていません。Web検索機能は無効です。")
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


def web_search(tavily_client, query: str, max_results: int = 5, search_type: str = "info") -> list:
    """Tavilyでウェブ検索を実行"""
    try:
        # 店舗検索の場合はより多くの結果を取得
        if search_type == "venue":
            max_results = 10

        response = tavily_client.search(
            query=query,
            search_depth="advanced" if search_type == "venue" else "basic",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )
        return response
    except Exception as e:
        return {"error": str(e)}


def build_venue_search_queries(theme: str, additional_info: dict) -> list:
    """店舗検索用の詳細なクエリを生成"""
    queries = []

    # 基本クエリの構築
    base_terms = []

    # 追加情報からキーワードを抽出
    location = ""
    budget = ""
    cuisine = ""
    features = []

    for key, value in additional_info.items():
        if value:
            key_lower = key.lower()
            if "日時" in key or "時期" in key or "いつ" in key:
                continue  # 日時は検索クエリには含めない
            elif "ジャンル" in key or "料理" in key or "種類" in key:
                cuisine = value
            elif "条件" in key or "希望" in key or "必須" in key:
                features.append(value)
            elif "人数" in key:
                base_terms.append(f"{value}人")
            elif "予算" in key or "金額" in key:
                budget = value

    # メインクエリ
    main_query = f"{theme} コース 料金 飲み放題"
    if cuisine:
        main_query = f"{theme} {cuisine} コース 料金"
    queries.append(main_query)

    # 詳細クエリ
    if budget:
        queries.append(f"{theme} {budget} コース内容 メニュー")

    # 個室などの条件がある場合
    for feature in features[:1]:  # 最大1つ
        queries.append(f"{theme} {feature} 宴会 プラン")

    return queries[:3]  # 最大3クエリ


def analyze_intent(client, theme: str) -> dict:
    """ユーザーの入力を分析し、Web検索が必要か判断する"""
    prompt = f"""
あなたはAIアシスタントです。
ユーザーの入力を分析し、どのように対応すべきか判断してください。

ユーザーの入力: {theme}

以下のJSON形式で回答してください：
{{
    "intent": "search" または "ideation" または "both",
    "search_type": "venue" または "info" または "none",
    "needs_search": true または false,
    "search_queries": ["検索クエリ1", "検索クエリ2"],
    "reason": "判断理由",
    "needs_clarification": true または false,
    "clarification_questions": [
        {{"id": "q1", "question": "質問文", "options": ["選択肢1", "選択肢2", "選択肢3"]}}
    ]
}}

判断基準：
- "search": 具体的な情報検索が必要（店舗検索、最新ニュース、価格調査、場所探しなど）
  例: 「新宿で忘年会の会場を探して」「2026年のトレンドを調べて」
- "ideation": アイデア出し・企画立案が目的
  例: 「新商品のアイデアを出して」「イベントの企画を考えて」
- "both": 検索結果を元にアイデアを出す
  例: 「最新トレンドを踏まえた新商品企画」「競合調査をしてから差別化案を出して」

search_type:
- "venue": 店舗・会場・場所を探している（飲食店、イベント会場、ホテルなど）
- "info": 情報・ニュース・トレンドを調べている
- "none": 検索不要

【重要】店舗・会場検索（search_type: "venue"）の場合は、必ず以下の質問を含めてください：
- 希望の日時・時期
- 料理のジャンルや会場の種類
- 必須条件（個室、飲み放題、駅近、喫煙可など）
- その他の希望

search_queries: Web検索が必要な場合、効果的な検索クエリを1-3個生成
  - 店舗検索の場合は「〇〇 コース 飲み放題 料金」のように詳細情報が取れるクエリにする
needs_clarification: 情報が不足している場合はtrue
  - 店舗・会場検索の場合は、基本的にtrue（詳細条件を聞く）
clarification_questions: 追加で聞くべき質問（最大4つ、選択式）
"""

    try:
        response = call_llm(client, prompt)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response[json_start:json_end])
    except:
        pass
    return {
        "intent": "ideation",
        "needs_search": False,
        "search_queries": [],
        "reason": "分析できませんでした",
        "needs_clarification": False,
        "clarification_questions": []
    }


def format_search_results(search_response: dict) -> str:
    """検索結果を整形する"""
    if "error" in search_response:
        return f"検索エラー: {search_response['error']}"

    formatted = ""

    # AI要約があれば追加
    if search_response.get("answer"):
        formatted += f"【要約】\n{search_response['answer']}\n\n"

    # 個別結果
    results = search_response.get("results", [])
    if results:
        formatted += "【検索結果】\n"
        for i, result in enumerate(results, 1):
            title = result.get("title", "タイトルなし")
            content = result.get("content", "")[:200]
            url = result.get("url", "")
            formatted += f"{i}. {title}\n   {content}...\n   URL: {url}\n\n"

    return formatted


def generate_ideas_with_search(client, theme: str, framework: str, search_results: str, additional_info: dict = None) -> str:
    """検索結果を踏まえてアイデアを生成"""
    framework_info = FRAMEWORKS[framework]

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
以下のテーマと検索結果に基づいて、創造的で実用的なアイデアを5個生成してください。

テーマ: {theme}
{context_text}

【参考：Web検索結果】
{search_results}

各アイデアは以下の形式で出力してください：
1. [アイデアのタイトル]: [具体的な説明（50-100字程度）]

検索結果の情報を活用し、実現可能かつ斬新なアイデアを出してください。
"""
    else:
        viewpoints = "\n".join([f"- {name}: {desc}" for name, desc in framework_info["prompts"]])
        prompt = f"""
あなたはアイデアソンのファシリテーターです。
「{framework}」フレームワークを使って、以下のテーマについてアイデアを生成してください。

テーマ: {theme}
{context_text}

【参考：Web検索結果】
{search_results}

フレームワークの視点:
{viewpoints}

各視点から1つずつアイデアを出してください。
形式:
【視点名】[アイデアのタイトル]: [具体的な説明（50-100字程度）]

検索結果の情報を活用し、実現可能かつ創造的なアイデアを出してください。
"""

    return call_llm(client, prompt)


def generate_search_response(client, theme: str, search_results: str, additional_info: dict = None, search_type: str = "info") -> str:
    """検索結果を元に回答を生成（店舗検索など）"""
    context_text = ""
    if additional_info:
        context_lines = []
        for key, value in additional_info.items():
            if value:
                context_lines.append(f"- {key}: {value}")
        if context_lines:
            context_text = "\n条件:\n" + "\n".join(context_lines)

    # 店舗・会場検索の場合は専用のプロンプト
    if search_type == "venue":
        prompt = f"""
あなたは店舗・会場探しの専門アシスタントです。
ユーザーの条件に合う店舗・会場を、検索結果を元に詳しく紹介してください。

リクエスト: {theme}
{context_text}

【Web検索結果】
{search_results}

以下の形式で、条件に合う店舗を3〜5件紹介してください：

---
## 🏠 [店舗名/会場名]

**基本情報**
- 📍 エリア/最寄り駅:
- 💰 予算: 1人あたり〇〇円
- 👥 収容人数: 〇〜〇名
- 🚬 喫煙: 可/不可/分煙

**コース情報**（わかる範囲で）
- コース名: 〇〇コース
- 料金: 〇〇円（税込/税抜）
- 内容: 料理〇品＋飲み放題〇時間
- 飲み放題の種類:

**おすすめポイント**
- （この店舗の特徴や強み）

**予約・詳細**
- URL: （検索結果のURLがあれば）
- ⚠️ 空き状況は上記URLまたは店舗に直接ご確認ください

---

【注意事項】
- 検索結果に情報がない項目は「要確認」と記載
- 各店舗の後に「---」で区切る
- 最後に「💡 ご予約の際は、直接お店に空き状況をご確認ください」と追記
"""
    else:
        prompt = f"""
あなたは親切なアシスタントです。
ユーザーのリクエストに対して、検索結果を元に分かりやすく回答してください。

リクエスト: {theme}
{context_text}

【Web検索結果】
{search_results}

以下のルールで回答してください：
1. 検索結果から relevant な情報を抽出・整理
2. 条件に合うものをリストアップ
3. それぞれの特徴やおすすめポイントを簡潔に説明
4. 具体的な情報（価格、場所、URLなど）があれば含める
5. 箇条書きで見やすく整理

検索結果に十分な情報がない場合は、その旨を伝え、追加で調べるべきことを提案してください。
"""

    return call_llm(client, prompt)


def generate_ideas_with_context(client, theme: str, framework: str, additional_info: dict, num_ideas: int = 5) -> str:
    """追加情報を含めてアイデアを生成"""
    framework_info = FRAMEWORKS[framework]

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
if "intent_analysis" not in st.session_state:
    st.session_state.intent_analysis = None
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "search_response" not in st.session_state:
    st.session_state.search_response = None
if "search_type" not in st.session_state:
    st.session_state.search_type = "info"

# API初期化
client = init_groq()
tavily_client = init_tavily()

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

    # 機能説明
    st.markdown("#### 🔍 自動判断機能")
    st.caption("入力内容に応じて自動で判断します：")
    st.caption("• 🌐 Web検索が必要 → 自動検索")
    st.caption("• 💡 アイデア出し → フレームワーク適用")
    st.caption("• 🔄 両方必要 → 検索→アイデア生成")

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
        st.session_state.intent_analysis = None
        st.session_state.search_results = None
        st.session_state.search_response = None
        st.session_state.search_type = "info"
        st.rerun()

# メインコンテンツ
st.markdown('<p class="main-header">⚡ BrainSpark</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AIと一緒にブレインストーミング。Web検索も自動で行い、最高精度のアイデアを生み出します</p>', unsafe_allow_html=True)

if not client:
    st.warning("Groq APIキーを設定してください（.streamlit/secrets.toml）")
    st.stop()

# テーマ入力
col1, col2 = st.columns([3, 1])
with col1:
    theme = st.text_input(
        "🎯 テーマ・質問を入力",
        placeholder="例: 新商品のアイデア、新宿で忘年会の会場を探して、最新トレンドを踏まえた企画...",
        value=st.session_state.theme
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("✨ 実行", type="primary", use_container_width=True)

# テーマ分析と処理
if analyze_btn and theme:
    st.session_state.theme = theme
    st.session_state.skip_questions = False
    st.session_state.search_results = None
    st.session_state.search_response = None

    with st.spinner("入力を分析中..."):
        analysis = analyze_intent(client, theme)
        st.session_state.intent_analysis = analysis

        intent = analysis.get("intent", "ideation")
        needs_search = analysis.get("needs_search", False)
        search_queries = analysis.get("search_queries", [])
        needs_clarification = analysis.get("needs_clarification", False)
        questions = analysis.get("clarification_questions", [])
        search_type = analysis.get("search_type", "info")
        st.session_state.search_type = search_type

        # 店舗検索の場合、追加質問がなければデフォルトの質問を設定
        if search_type == "venue" and not questions:
            needs_clarification = True
            questions = [
                {"id": "datetime", "question": "希望の日時・時期は？", "options": ["今週末", "来週", "12月中", "1月", "日程未定"]},
                {"id": "cuisine", "question": "料理のジャンル・会場の雰囲気は？", "options": ["和食", "イタリアン・洋食", "中華", "居酒屋", "ホテル宴会場", "こだわりなし"]},
                {"id": "features", "question": "必須条件は？（複数ある場合は「その他」で入力）", "options": ["個室", "飲み放題付き", "駅近（徒歩5分以内）", "貸切可能", "特になし"]},
                {"id": "other", "question": "その他の希望があれば教えてください", "options": []}
            ]

        # 追加質問が必要な場合
        if needs_clarification and questions:
            st.session_state.clarification_questions = {"questions": questions, "reason": analysis.get("reason", "")}
            st.session_state.waiting_for_answers = True
            st.rerun()

        # Web検索が必要な場合（追加質問がない場合のみ実行）
        if needs_search and tavily_client and search_queries and not needs_clarification:
            with st.spinner("🔍 Web検索中..."):
                all_results = []

                # 店舗検索の場合は詳細なクエリを使用
                if search_type == "venue":
                    search_queries = build_venue_search_queries(theme, st.session_state.additional_info)

                for query in search_queries[:3]:
                    result = web_search(tavily_client, query, search_type=search_type)
                    if "error" not in result:
                        all_results.append(result)

                if all_results:
                    combined_results = {
                        "answer": all_results[0].get("answer", ""),
                        "results": []
                    }
                    for r in all_results:
                        combined_results["results"].extend(r.get("results", []))

                    st.session_state.search_results = format_search_results(combined_results)

                    # 検索のみの場合
                    if intent == "search":
                        response = generate_search_response(client, theme, st.session_state.search_results, st.session_state.additional_info, search_type)
                        st.session_state.search_response = response
                        st.rerun()

                    # 検索＋アイデア出しの場合
                    elif intent == "both":
                        result = generate_ideas_with_search(client, theme, selected_framework, st.session_state.search_results, st.session_state.additional_info)

                        lines = [line.strip() for line in result.split("\n") if line.strip()]
                        new_ideas = []
                        for line in lines:
                            if any(c.isalnum() for c in line) and len(line) > 10:
                                clean = line.lstrip("0123456789.-）)】・ ")
                                if clean and clean not in st.session_state.ideas:
                                    new_ideas.append(clean)

                        st.session_state.ideas.extend(new_ideas[:10])
                        st.rerun()

        # アイデア出しのみの場合
        if intent == "ideation" or (intent == "both" and not st.session_state.search_results):
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
    st.markdown("### 💬 より良い結果を出すために教えてください")
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
        if st.button("📝 この情報で実行", type="primary", use_container_width=True):
            st.session_state.additional_info = answers
            st.session_state.waiting_for_answers = False
            st.session_state.clarification_questions = None

            # 再度分析して実行
            analysis = st.session_state.intent_analysis
            intent = analysis.get("intent", "ideation") if analysis else "ideation"
            search_queries = analysis.get("search_queries", []) if analysis else []
            search_type = st.session_state.search_type

            if analysis and analysis.get("needs_search") and tavily_client:
                with st.spinner("🔍 Web検索中..."):
                    all_results = []

                    # 店舗検索の場合は詳細なクエリを使用
                    if search_type == "venue":
                        search_queries = build_venue_search_queries(st.session_state.theme, answers)

                    for query in search_queries[:3]:
                        result = web_search(tavily_client, query, search_type=search_type)
                        if "error" not in result:
                            all_results.append(result)

                    if all_results:
                        combined_results = {
                            "answer": all_results[0].get("answer", ""),
                            "results": []
                        }
                        for r in all_results:
                            combined_results["results"].extend(r.get("results", []))

                        st.session_state.search_results = format_search_results(combined_results)

                        if intent == "search":
                            response = generate_search_response(client, st.session_state.theme, st.session_state.search_results, answers, search_type)
                            st.session_state.search_response = response
                            st.rerun()
                        elif intent == "both":
                            result = generate_ideas_with_search(client, st.session_state.theme, selected_framework, st.session_state.search_results, answers)

                            lines = [line.strip() for line in result.split("\n") if line.strip()]
                            new_ideas = []
                            for line in lines:
                                if any(c.isalnum() for c in line) and len(line) > 10:
                                    clean = line.lstrip("0123456789.-）)】・ ")
                                    if clean and clean not in st.session_state.ideas:
                                        new_ideas.append(clean)

                            st.session_state.ideas.extend(new_ideas[:10])
                            st.rerun()
            else:
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
        if st.button("⏭️ スキップして実行", use_container_width=True):
            st.session_state.waiting_for_answers = False
            st.session_state.skip_questions = True
            st.session_state.clarification_questions = None

            analysis = st.session_state.intent_analysis
            intent = analysis.get("intent", "ideation") if analysis else "ideation"
            search_queries = analysis.get("search_queries", []) if analysis else []
            search_type = st.session_state.search_type

            if analysis and analysis.get("needs_search") and tavily_client:
                with st.spinner("🔍 Web検索中..."):
                    all_results = []

                    # 店舗検索の場合でもスキップされた場合は基本クエリを使用
                    if search_type == "venue" and not search_queries:
                        search_queries = [f"{st.session_state.theme} コース 飲み放題 料金"]

                    for query in search_queries[:3]:
                        result = web_search(tavily_client, query, search_type=search_type)
                        if "error" not in result:
                            all_results.append(result)

                    if all_results:
                        combined_results = {
                            "answer": all_results[0].get("answer", ""),
                            "results": []
                        }
                        for r in all_results:
                            combined_results["results"].extend(r.get("results", []))

                        st.session_state.search_results = format_search_results(combined_results)

                        if intent == "search":
                            response = generate_search_response(client, st.session_state.theme, st.session_state.search_results, {}, search_type)
                            st.session_state.search_response = response
                            st.rerun()
                        elif intent == "both":
                            result = generate_ideas_with_search(client, st.session_state.theme, selected_framework, st.session_state.search_results, {})

                            lines = [line.strip() for line in result.split("\n") if line.strip()]
                            new_ideas = []
                            for line in lines:
                                if any(c.isalnum() for c in line) and len(line) > 10:
                                    clean = line.lstrip("0123456789.-）)】・ ")
                                    if clean and clean not in st.session_state.ideas:
                                        new_ideas.append(clean)

                            st.session_state.ideas.extend(new_ideas[:10])
                            st.rerun()
            else:
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

# 検索結果の表示（検索のみの場合）
if st.session_state.search_response and not st.session_state.waiting_for_answers:
    st.markdown("### 🔍 検索結果")

    st.markdown(st.session_state.search_response)

    if st.session_state.search_results:
        with st.expander("📄 元の検索データを見る"):
            st.text(st.session_state.search_results)

    st.markdown("---")

    # 検索結果からアイデア出しに移行するオプション
    if st.button("💡 この情報を元にアイデアを出す", type="secondary"):
        with st.spinner(f"「{selected_framework}」でアイデアを生成中..."):
            result = generate_ideas_with_search(client, st.session_state.theme, selected_framework, st.session_state.search_results, st.session_state.additional_info)

            lines = [line.strip() for line in result.split("\n") if line.strip()]
            new_ideas = []
            for line in lines:
                if any(c.isalnum() for c in line) and len(line) > 10:
                    clean = line.lstrip("0123456789.-）)】・ ")
                    if clean and clean not in st.session_state.ideas:
                        new_ideas.append(clean)

            st.session_state.ideas.extend(new_ideas[:10])
            st.session_state.search_response = None  # 検索結果表示をクリア
        st.rerun()

# タブ表示（アイデアがある場合）
if st.session_state.ideas and not st.session_state.waiting_for_answers:
    tab1, tab2, tab3 = st.tabs(["📝 アイデア一覧", "⭐ 評価", "🔀 組み合わせ"])

    with tab1:
        st.markdown("### 生成されたアイデア")

        # 検索結果があれば表示
        if st.session_state.search_results:
            with st.expander("🔍 参考にしたWeb検索結果"):
                st.text(st.session_state.search_results)

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

elif not st.session_state.waiting_for_answers and not st.session_state.search_response:
    # 初期表示
    st.markdown("---")
    st.markdown("### 🚀 使い方")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1. 入力")
        st.markdown("テーマや質問を自由に入力")
        st.caption("例：")
        st.caption("• 新商品のアイデア")
        st.caption("• 新宿で忘年会の会場を探して")
        st.caption("• 最新トレンドを踏まえた企画")

    with col2:
        st.markdown("#### 2. 自動判断")
        st.markdown("AIが最適な方法を自動選択")
        st.caption("• 🔍 Web検索が必要 → 自動検索")
        st.caption("• 💡 アイデア出し → フレームワーク適用")
        st.caption("• 🔄 両方 → 検索→生成")

    with col3:
        st.markdown("#### 3. 結果")
        st.markdown("検索結果やアイデアを表示")
        st.caption("• 検索結果の整理・要約")
        st.caption("• アイデアの評価・深掘り")
        st.caption("• エクスポート機能")

    st.markdown("---")
    st.markdown("### 📚 フレームワーク一覧")

    for name, info in FRAMEWORKS.items():
        with st.expander(f"**{name}** - {info['description']}"):
            for prompt_name, prompt_desc in info["prompts"]:
                st.markdown(f"- **{prompt_name}**: {prompt_desc}")
