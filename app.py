"""BrainSpark - AIブレインストーミングアシスタント"""
import streamlit as st
from groq import Groq
from tavily import TavilyClient
import json
import pandas as pd
from datetime import datetime, timedelta

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
    .chat-user {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #2196f3;
    }
    .chat-assistant {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
    }
    .usage-ok { color: #28a745; }
    .usage-warning { color: #ffc107; }
    .usage-danger { color: #dc3545; }
    .score-high { color: #28a745; font-weight: bold; }
    .score-mid { color: #ffc107; font-weight: bold; }
    .score-low { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# フレームワーク定義
FRAMEWORKS = {
    "自動選択": {
        "description": "AIが最適なフレームワークを自動選択",
        "prompts": []
    },
    "SCAMPER": {
        "description": "7つの視点で既存アイデアを変化させる",
        "prompts": [
            ("S - Substitute（代用）", "何か別のもので代用できないか？"),
            ("C - Combine（組み合わせ）", "他と組み合わせられないか？"),
            ("A - Adapt（適応）", "他の分野に適応できないか？"),
            ("M - Modify（修正）", "形や機能を変更したら？"),
            ("P - Put to other uses（転用）", "別の使い方はできないか？"),
            ("E - Eliminate（削除）", "何かを取り除いたら？"),
            ("R - Reverse（逆転）", "逆にしたら？"),
        ]
    },
    "6W2H": {
        "description": "8つの質問で企画を網羅的に整理",
        "prompts": [
            ("What", "何を？"), ("Why", "なぜ？"), ("Who", "誰が？"), ("Whom", "誰に？"),
            ("When", "いつ？"), ("Where", "どこで？"), ("How", "どうやって？"), ("How much", "いくらで？"),
        ]
    },
    "オズボーンのチェックリスト": {
        "description": "9つの質問でアイデアを拡張",
        "prompts": [
            ("転用", "他に使い道は？"), ("応用", "他から借りられないか？"), ("変更", "変えたら？"),
            ("拡大", "大きくしたら？"), ("縮小", "小さくしたら？"), ("代用", "代用したら？"),
            ("再配置", "並べ替えたら？"), ("逆転", "逆にしたら？"), ("結合", "組み合わせたら？"),
        ]
    },
}

# API制限
GROQ_LIMIT_PER_MINUTE = 30
TAVILY_LIMIT_PER_MONTH = 1000


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
        return None


def update_usage(api_type: str):
    """API使用回数を更新"""
    now = datetime.now()

    if api_type == "groq":
        # 1分以上経過していたらリセット
        if "groq_reset_time" not in st.session_state or now > st.session_state.groq_reset_time:
            st.session_state.groq_count = 0
            st.session_state.groq_reset_time = now + timedelta(minutes=1)
        st.session_state.groq_count += 1

    elif api_type == "tavily":
        # 月が変わっていたらリセット
        if "tavily_month" not in st.session_state or st.session_state.tavily_month != now.month:
            st.session_state.tavily_count = 0
            st.session_state.tavily_month = now.month
        st.session_state.tavily_count += 1


def get_usage_display():
    """使用状況の表示用テキストを取得"""
    now = datetime.now()

    # Groq
    groq_count = st.session_state.get("groq_count", 0)
    groq_reset_time = st.session_state.get("groq_reset_time", now)

    # リセット時間を過ぎていたらカウンターをリセット
    if now > groq_reset_time:
        st.session_state.groq_count = 0
        st.session_state.groq_reset_time = now + timedelta(minutes=1)
        groq_count = 0

    groq_remaining = GROQ_LIMIT_PER_MINUTE - groq_count

    if groq_remaining > 20:
        groq_class = "usage-ok"
        groq_status = "✅"
    elif groq_remaining > 5:
        groq_class = "usage-warning"
        groq_status = "⚠️"
    else:
        groq_class = "usage-danger"
        groq_status = "🚫"

    # リセットまでの秒数
    if groq_count >= GROQ_LIMIT_PER_MINUTE:
        seconds_until_reset = max(0, int((groq_reset_time - now).total_seconds()))
        groq_text = f'{groq_status} <span class="{groq_class}">制限中（{seconds_until_reset}秒後リセット）</span>'
    else:
        groq_text = f'{groq_status} <span class="{groq_class}">約{groq_remaining}回/分</span>'

    # Tavily
    tavily_count = st.session_state.get("tavily_count", 0)
    tavily_remaining = TAVILY_LIMIT_PER_MONTH - tavily_count

    if tavily_count >= TAVILY_LIMIT_PER_MONTH:
        tavily_class = "usage-danger"
        tavily_text = f'🚫 <span class="{tavily_class}">月間上限（来月リセット）</span>'
    elif tavily_remaining > 500:
        tavily_class = "usage-ok"
        tavily_text = f'✅ <span class="{tavily_class}">約{tavily_remaining}回/月</span>'
    elif tavily_remaining > 100:
        tavily_class = "usage-warning"
        tavily_text = f'⚠️ <span class="{tavily_class}">約{tavily_remaining}回/月</span>'
    else:
        tavily_class = "usage-danger"
        tavily_text = f'⚠️ <span class="{tavily_class}">残りわずか（約{tavily_remaining}回/月）</span>'

    return groq_text, tavily_text


def call_llm(client, messages: list) -> str:
    """LLMを呼び出す（会話履歴対応）"""
    try:
        update_usage("groq")

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        error_str = str(e).lower()

        # レート制限エラーの検出
        if "rate_limit" in error_str or "rate limit" in error_str or "429" in error_str:
            # カウンターをリセット時間まで最大値に設定
            st.session_state.groq_count = GROQ_LIMIT_PER_MINUTE
            st.session_state.groq_reset_time = datetime.now() + timedelta(minutes=1)
            return "⚠️ **API制限に達しました**\n\n1分間に送信できるメッセージ数の上限に達しました。\n\n**約1分後に再試行してください。**\n\n（ページをリロードせずにお待ちください）"

        # その他のエラー
        return f"⚠️ エラーが発生しました: {e}"


def web_search(tavily_client, query: str, max_results: int = 8) -> dict:
    """Tavilyでウェブ検索を実行"""
    try:
        update_usage("tavily")

        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )
        return response
    except Exception as e:
        error_str = str(e).lower()

        # レート制限または使用量超過エラーの検出
        if "rate" in error_str or "limit" in error_str or "429" in error_str or "quota" in error_str:
            st.session_state.tavily_count = TAVILY_LIMIT_PER_MONTH
            return {"error": "⚠️ **Web検索の月間上限に達しました**\n\n来月1日にリセットされます。\n\nWeb検索なしでアイデア出しは引き続き利用できます。"}

        return {"error": f"検索エラー: {e}"}


def format_search_results(search_response: dict) -> str:
    """検索結果を整形する"""
    if "error" in search_response:
        return f"検索エラー: {search_response['error']}"

    formatted = ""
    if search_response.get("answer"):
        formatted += f"【要約】\n{search_response['answer']}\n\n"

    results = search_response.get("results", [])
    if results:
        formatted += "【検索結果】\n"
        for i, result in enumerate(results, 1):
            title = result.get("title", "タイトルなし")
            content = result.get("content", "")[:200]
            url = result.get("url", "")
            formatted += f"{i}. {title}\n   {content}...\n   URL: {url}\n\n"

    return formatted


def get_system_prompt(framework: str) -> str:
    """システムプロンプトを生成"""
    base_prompt = """あなたは「BrainSpark」というAIアシスタントです。

## 重要：言語について
必ず日本語で回答してください。中国語の簡体字（兴、头、实など）は使わず、日本語の漢字（興、頭、実など）を使用してください。

## あなたの使命

**「最高精度の回答を出すこと」**

これがあなたの唯一かつ最も重要な目標です。
そのために、あなたは自分で考え、必要な行動を取ってください。

## 最高精度の回答を出すための原則

### 1. 情報が不十分なまま回答しない

曖昧なリクエストに対して、推測だけで一般的な回答を返すことは「最高精度」ではありません。

**必ず自問してください：**
- この情報だけで、本当にユーザーに最適な回答ができるか？
- 何を知ればもっと良い回答ができるか？
- ユーザーが本当に知りたいことは何か？

足りない情報があれば、**まず質問してください**。

### 2. 質問は具体的に

悪い例：「もう少し詳しく教えてください」
良い例：「より良い回答をするために教えてください：
1. 〇〇について（選択肢があれば提示）
2. △△について
3. □□について」

### 3. 質問と回答のバランス

- 最初のリクエスト → 必要な情報を確認する質問
- 情報が揃ったら → 具体的で実用的な回答
- 追加質問には → 前の回答を踏まえて深掘り

### 4. あらゆるリクエストに対応

アイデア出し、企画、検索、相談、質問、作業依頼...
どんなリクエストでも、「最高精度の回答を出す」という原則で対応してください。

何について情報が必要かは、リクエストの内容に応じて自分で判断してください。

## 回答の形式

- 見やすく構造化（見出し、箇条書き）
- 長すぎない（要点を絞る）
- 具体的（抽象論より実例）
"""

    if framework != "自動選択" and framework in FRAMEWORKS:
        framework_info = FRAMEWORKS[framework]
        viewpoints = "\n".join([f"- {name}: {desc}" for name, desc in framework_info["prompts"]])
        base_prompt += f"""

## 使用するフレームワーク: {framework}
{framework_info['description']}

視点:
{viewpoints}

アイデア出しの際は、このフレームワークの視点を活用してください。
"""

    return base_prompt


def analyze_if_clarification_needed(client, user_message: str, collected_info: list = None) -> dict:
    """ユーザーの入力を分析し、追加情報が必要か判断"""

    # 既に収集した情報を含めて分析
    collected_text = ""
    if collected_info:
        collected_text = "\n\n【既に収集した情報】\n" + "\n".join([f"- {info}" for info in collected_info])

    analysis_prompt = f"""ユーザーからのリクエストを分析してください。

リクエスト: {user_message}{collected_text}

このリクエストに対して「最高精度の回答」を出すために、追加で聞くべき情報があるか判断してください。

## 判断基準
- 曖昧で一般的な回答しかできない → 質問が必要
- 具体的な回答ができる十分な情報がある → 質問不要
- 単純な事実の質問 → 質問不要
- 挨拶や雑談 → 質問不要

## 出力形式（必ずこのJSON形式で）
{{
    "needs_clarification": true または false,
    "reason": "判断理由を1文で",
    "questions": [
        "質問1",
        "質問2",
        "質問3"
    ]
}}

質問が必要ない場合は questions を空配列 [] にしてください。
質問は最大5個まで、具体的に。既に収集した情報に含まれている内容は聞かないでください。"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": analysis_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=512,
        )
        result = response.choices[0].message.content

        # JSONを抽出
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(result[json_start:json_end])
    except:
        pass

    return {"needs_clarification": False, "questions": []}


def generate_training_topic(client, training_type: str) -> str:
    """トレーニング用のお題を生成"""
    prompts = {
        "idea": """ビジネスシーンでのアイデア出しトレーニング用のお題を1つ生成してください。

例：
- 「会議の生産性を上げるアイデアを3つ出してください」
- 「新入社員の定着率を上げる施策を考えてください」
- 「社内コミュニケーションを活性化する方法を3つ挙げてください」

お題のみを出力してください。説明や前置きは不要です。""",

        "reply": """日常会話やビジネスシーンでの返答トレーニング用のお題を1つ生成してください。

形式：「〇〇と言われました。どう返しますか？」

例：
- 「上司から『最近どう？』と聞かれました。どう返しますか？」
- 「同僚から『この仕事、手伝ってもらえない？』と言われました。どう返しますか？」
- 「会議で『〇〇さんはどう思う？』と急に振られました。どう返しますか？」

お題のみを出力してください。説明や前置きは不要です。""",

        "opinion": """意見を述べるトレーニング用のお題を1つ生成してください。

形式：「〇〇についてあなたの意見を述べてください」

例：
- 「リモートワークと出社、どちらが良いと思いますか？理由も含めて述べてください」
- 「AIの業務活用について、あなたの意見を述べてください」
- 「週休3日制について、賛成・反対の立場を明確にして意見を述べてください」

お題のみを出力してください。説明や前置きは不要です。""",

        "question": """質問力を鍛えるトレーニング用のお題を1つ生成してください。

形式：状況を説明し、「この場面で良い質問を3つ考えてください」

例：
- 「新しいプロジェクトの説明を受けました。理解を深めるための質問を3つ考えてください」
- 「取引先が新サービスを紹介してくれました。興味を示す質問を3つ考えてください」
- 「チームメンバーが困っている様子です。状況を把握するための質問を3つ考えてください」

お題のみを出力してください。説明や前置きは不要です。""",

        "summary": """要約力を鍛えるトレーニング用のお題を1つ生成してください。

形式：100-150字程度の文章を提示し、「一言（20字以内）で要約してください」

ビジネスや日常に関連した内容にしてください。

お題のみを出力してください。説明や前置きは不要です。"""
    }

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompts.get(training_type, prompts["idea"])}],
            model="llama-3.3-70b-versatile",
            temperature=0.9,
            max_tokens=256,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "会議をもっと効率的にするアイデアを3つ出してください"


def generate_training_feedback(client, training_type: str, topic: str, user_answer: str) -> str:
    """トレーニングの回答にフィードバック"""
    prompt = f"""ユーザーがトレーニングに取り組みました。建設的なフィードバックをしてください。

【お題】
{topic}

【ユーザーの回答】
{user_answer}

【フィードバックのルール】
1. まず良い点を具体的に褒める
2. さらに良くするためのアドバイスを1-2点
3. 別の視点からのアイデアを1-2個提案
4. 励ましの言葉で締める

簡潔に、温かみのあるトーンでお願いします。"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=512,
        )
        return response.choices[0].message.content
    except Exception as e:
        return "回答ありがとうございます！良い練習になりましたね。"


def generate_single_question(question: str, remaining_count: int) -> str:
    """1つの質問を整形して返す"""
    if remaining_count > 0:
        return f"より良い回答のために教えてください：\n\n**{question}**\n\n（あと{remaining_count}問あります。「とりあえず回答」ボタンで今の情報で回答することもできます）"
    else:
        return f"最後の質問です：\n\n**{question}**\n\n（「とりあえず回答」ボタンで今の情報で回答することもできます）"


def process_message_with_search(client, tavily_client, original_request: str, collected_info: list, chat_history: list, framework: str) -> tuple:
    """収集した情報を基に最終回答を生成"""

    # Web検索が必要か判断
    search_keywords = ["検索", "探して", "調べて", "会場", "店舗", "お店", "レストラン", "居酒屋",
                       "ホテル", "場所", "最新", "ニュース", "トレンド", "〜とは", "について教えて"]

    needs_search = any(keyword in original_request for keyword in search_keywords)
    search_results = None

    if needs_search and tavily_client:
        search_query = original_request.replace("を探して", "").replace("を調べて", "").replace("を検索", "")
        if "コース" not in search_query and any(k in original_request for k in ["会場", "店舗", "お店", "居酒屋", "レストラン"]):
            search_query += " コース 料金 飲み放題"

        with st.spinner("🔍 Web検索中..."):
            result = web_search(tavily_client, search_query)
            if "error" not in result:
                search_results = format_search_results(result)

    # メッセージ構築
    messages = [{"role": "system", "content": get_system_prompt(framework)}]

    # 会話履歴を追加
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # 収集した情報を含めたリクエスト
    if collected_info:
        info_text = "\n".join([f"- {info}" for info in collected_info])
        user_content = f"{original_request}\n\n【追加情報】\n{info_text}"
    else:
        user_content = original_request

    if search_results:
        user_content += f"\n\n【参考：Web検索結果】\n{search_results}"

    messages.append({"role": "user", "content": user_content})

    response = call_llm(client, messages)

    return response, search_results


def start_clarification_process(client, user_message: str):
    """質問プロセスを開始"""
    update_usage("groq")
    analysis = analyze_if_clarification_needed(client, user_message)

    if analysis.get("needs_clarification") and analysis.get("questions"):
        st.session_state.pending_questions = analysis["questions"]
        st.session_state.collected_info = []
        st.session_state.original_request = user_message
        st.session_state.asking_questions = True
        return True
    return False


def is_user_asking_question(user_input: str) -> bool:
    """ユーザーの入力が質問かどうか判定"""
    question_patterns = ["？", "?", "どう", "何", "なぜ", "どのような", "例えば", "具体的に", "教えて", "わからない", "意味"]
    return any(pattern in user_input for pattern in question_patterns)


def answer_user_question_during_clarification(client, user_question: str, current_question: str) -> str:
    """質問中にユーザーが質問してきた場合に回答"""
    prompt = f"""ユーザーに質問をしたところ、ユーザーから逆に質問されました。
ユーザーの質問に簡潔に答えてから、改めて元の質問をしてください。

【あなたがした質問】
{current_question}

【ユーザーからの質問】
{user_question}

簡潔に回答してください。"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=512,
        )
        return response.choices[0].message.content
    except:
        return f"すみません、もう少し詳しく説明しますね。\n\n{current_question}"


# URLパラメータをチェック（トレーニングモード）
query_params = st.query_params
is_training_mode = query_params.get("mode") == "training"

# セッション状態の初期化
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "groq_count" not in st.session_state:
    st.session_state.groq_count = 0
if "groq_reset_time" not in st.session_state:
    st.session_state.groq_reset_time = datetime.now() + timedelta(minutes=1)
if "tavily_count" not in st.session_state:
    st.session_state.tavily_count = 0
if "tavily_month" not in st.session_state:
    st.session_state.tavily_month = datetime.now().month
if "saved_chats" not in st.session_state:
    st.session_state.saved_chats = []  # 保存された会話のリスト
if "current_chat_name" not in st.session_state:
    st.session_state.current_chat_name = None
if "input_key" not in st.session_state:
    st.session_state.input_key = 0  # 入力欄リセット用
if "training_active" not in st.session_state:
    st.session_state.training_active = False
if "training_topic" not in st.session_state:
    st.session_state.training_topic = None
if "training_type" not in st.session_state:
    st.session_state.training_type = None
if "pending_questions" not in st.session_state:
    st.session_state.pending_questions = []  # 残りの質問リスト
if "collected_info" not in st.session_state:
    st.session_state.collected_info = []  # 収集した情報
if "original_request" not in st.session_state:
    st.session_state.original_request = None  # 元のリクエスト
if "asking_questions" not in st.session_state:
    st.session_state.asking_questions = False  # 質問中フラグ

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
    if selected_framework in FRAMEWORKS:
        st.caption(FRAMEWORKS[selected_framework]["description"])

    st.markdown("---")

    # 使用状況
    st.markdown("#### 📊 API使用状況")
    groq_text, tavily_text = get_usage_display()

    st.markdown("**Groq (LLM)**")
    st.markdown(groq_text, unsafe_allow_html=True)

    st.markdown("**Tavily (Web検索)**")
    st.markdown(tavily_text, unsafe_allow_html=True)

    if not tavily_client:
        st.caption("⚠️ Web検索は無効")

    st.caption("※ 目安の数値です。制限に達するとメッセージが表示されます。")

    st.markdown("---")

    # 会話履歴の統計
    if st.session_state.chat_history:
        st.markdown("#### 💬 会話")
        msg_count = len(st.session_state.chat_history)
        st.caption(f"メッセージ数: {msg_count}")

    st.markdown("---")

    # エクスポート
    if st.session_state.chat_history:
        st.markdown("#### 💾 エクスポート")
        export_data = {
            "生成日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "会話履歴": st.session_state.chat_history,
        }
        st.download_button(
            "会話をJSONでダウンロード",
            json.dumps(export_data, ensure_ascii=False, indent=2),
            "brainspark_chat.json",
            "application/json",
            use_container_width=True
        )

        # テキスト形式
        text_export = f"BrainSpark 会話ログ\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for msg in st.session_state.chat_history:
            role = "あなた" if msg["role"] == "user" else "BrainSpark"
            text_export += f"【{role}】\n{msg['content']}\n\n"

        st.download_button(
            "会話をテキストでダウンロード",
            text_export,
            "brainspark_chat.txt",
            "text/plain",
            use_container_width=True
        )

    st.markdown("---")

    # 会話の保存・管理
    st.markdown("#### 💾 会話の保存")

    # 現在の会話を保存
    if st.session_state.chat_history:
        save_name = st.text_input(
            "保存名",
            value=st.session_state.current_chat_name or "",
            placeholder="例: 忘年会の店探し",
            key="save_name_input"
        )

        if st.button("📥 この会話を保存", use_container_width=True):
            if save_name:
                # 同じ名前があれば上書き、なければ追加
                existing_idx = None
                for i, saved in enumerate(st.session_state.saved_chats):
                    if saved["name"] == save_name:
                        existing_idx = i
                        break

                chat_data = {
                    "name": save_name,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "history": st.session_state.chat_history.copy()
                }

                if existing_idx is not None:
                    st.session_state.saved_chats[existing_idx] = chat_data
                    st.success(f"「{save_name}」を上書き保存しました")
                else:
                    st.session_state.saved_chats.append(chat_data)
                    st.success(f"「{save_name}」を保存しました")

                st.session_state.current_chat_name = save_name
            else:
                st.warning("保存名を入力してください")

    # 保存済みの会話を読み込み
    if st.session_state.saved_chats:
        st.markdown("#### 📂 保存済みの会話")

        for i, saved in enumerate(st.session_state.saved_chats):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.caption(f"**{saved['name']}**")
                st.caption(f"{saved['timestamp']}")

            with col2:
                if st.button("📖", key=f"load_{i}", help="読み込む"):
                    st.session_state.chat_history = saved["history"].copy()
                    st.session_state.current_chat_name = saved["name"]
                    st.session_state.input_key += 1
                    st.rerun()

            with col3:
                if st.button("🗑️", key=f"delete_{i}", help="削除"):
                    st.session_state.saved_chats.pop(i)
                    st.rerun()

    st.markdown("---")

    # 新しいトピックを開始
    if st.button("🆕 新しいトピックを開始", use_container_width=True, type="primary"):
        # 現在の会話があれば保存を促す
        if st.session_state.chat_history and not st.session_state.current_chat_name:
            st.session_state.show_save_prompt = True
        else:
            st.session_state.chat_history = []
            st.session_state.current_chat_name = None
            st.session_state.input_key += 1
            st.rerun()

    if st.session_state.get("show_save_prompt"):
        st.warning("現在の会話を保存しますか？")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("保存せず開始", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.current_chat_name = None
                st.session_state.show_save_prompt = False
                st.session_state.input_key += 1
                st.rerun()
        with col2:
            if st.button("キャンセル", use_container_width=True):
                st.session_state.show_save_prompt = False
                st.rerun()

# メインコンテンツ
st.markdown('<p class="main-header">⚡ BrainSpark</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AIと会話しながらブレインストーミング。追加質問や深掘りも自由にできます</p>', unsafe_allow_html=True)

# トレーニングモード（URLに?mode=trainingがある場合のみ表示）
if is_training_mode:
    st.markdown("---")

    # トレーニングセクション
    with st.expander("🎯 スキルトレーニング", expanded=not st.session_state.training_active):
        st.markdown("""
        **コミュニケーション力を鍛えましょう！**

        以下から練習したいスキルを選んでください。AIがお題を出し、回答にフィードバックします。
        """)

        training_types = {
            "idea": "💡 アイデア出し",
            "reply": "💬 会話の返答",
            "opinion": "🎤 意見を述べる",
            "question": "❓ 質問力",
            "summary": "📝 要約力"
        }

        cols = st.columns(len(training_types))
        for i, (key, label) in enumerate(training_types.items()):
            with cols[i]:
                if st.button(label, key=f"train_{key}", use_container_width=True):
                    st.session_state.training_type = key
                    st.session_state.training_active = True
                    with st.spinner("お題を生成中..."):
                        update_usage("groq")
                        st.session_state.training_topic = generate_training_topic(client, key)
                    st.rerun()

    # トレーニング実行中
    if st.session_state.training_active and st.session_state.training_topic:
        st.markdown("---")
        st.markdown("### 📋 お題")
        st.info(st.session_state.training_topic)

        # 回答入力
        with st.form(key="training_form", clear_on_submit=True):
            training_answer = st.text_area(
                "あなたの回答",
                placeholder="考えて回答を入力してください...",
                height=150
            )

            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                submit_training = st.form_submit_button("📤 回答を送信", type="primary", use_container_width=True)
            with col2:
                skip_topic = st.form_submit_button("🔄 別のお題", use_container_width=True)
            with col3:
                end_training = st.form_submit_button("終了", use_container_width=True)

        if submit_training and training_answer:
            with st.spinner("フィードバックを生成中..."):
                update_usage("groq")
                feedback = generate_training_feedback(
                    client,
                    st.session_state.training_type,
                    st.session_state.training_topic,
                    training_answer
                )

            st.markdown("### 💬 フィードバック")
            st.success(feedback)

            # 次のお題へ進むボタン
            if st.button("🔄 次のお題に挑戦", use_container_width=True):
                with st.spinner("お題を生成中..."):
                    update_usage("groq")
                    st.session_state.training_topic = generate_training_topic(client, st.session_state.training_type)
                st.rerun()

        if skip_topic:
            with st.spinner("お題を生成中..."):
                update_usage("groq")
                st.session_state.training_topic = generate_training_topic(client, st.session_state.training_type)
            st.rerun()

        if end_training:
            st.session_state.training_active = False
            st.session_state.training_topic = None
            st.session_state.training_type = None
            st.rerun()

if not client:
    st.warning("Groq APIキーを設定してください（.streamlit/secrets.toml）")
    st.stop()

# 会話履歴の表示
chat_container = st.container()
with chat_container:
    if not st.session_state.chat_history:
        # 初期メッセージ
        st.markdown("---")
        st.markdown("### 👋 ようこそ！")
        st.markdown("""
何でも聞いてください。例えば：

- 💡 **アイデア出し**: 「新商品のアイデアを出して」「プレゼンの構成を考えて」
- 🔍 **検索**: 「新宿で忘年会の会場を探して」「2026年のトレンドを調べて」
- 🤔 **相談**: 「この企画のメリット・デメリットを教えて」
- 📎 **ファイル分析**: SQLやCSVをアップロードして「このクエリを説明して」「データを分析して」

**情報が足りなければ質問します。回答に対して追加で質問することもできます。**
        """)

        # クイックスタート
        st.markdown("---")
        st.markdown("#### 🚀 クイックスタート")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💡 アイデア出し", use_container_width=True):
                st.session_state.quick_start = "新商品や新サービスのアイデアを出したいです"
                st.rerun()

        with col2:
            if st.button("🏠 会場探し", use_container_width=True):
                st.session_state.quick_start = "忘年会の会場を探しています"
                st.rerun()

        with col3:
            if st.button("📊 プレゼン相談", use_container_width=True):
                st.session_state.quick_start = "プレゼンの構成を考えたいです"
                st.rerun()

    else:
        # 会話履歴を表示
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">🧑 <strong>あなた</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-assistant">⚡ <strong>BrainSpark</strong><br>{msg["content"]}</div>', unsafe_allow_html=True)

# クイックスタート処理
if "quick_start" in st.session_state:
    quick_message = st.session_state.quick_start
    del st.session_state.quick_start

    # ユーザーメッセージを追加
    st.session_state.chat_history.append({"role": "user", "content": quick_message})

    # 質問プロセスを開始
    with st.spinner("分析中..."):
        if start_clarification_process(client, quick_message):
            # 最初の質問を表示
            first_question = st.session_state.pending_questions.pop(0)
            remaining = len(st.session_state.pending_questions)
            response = generate_single_question(first_question, remaining)
        else:
            # 質問不要なら直接回答
            response, _ = process_message_with_search(client, tavily_client, quick_message, [], st.session_state.chat_history[:-1], selected_framework)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()

# 入力欄
st.markdown("---")

# 現在のトピック名を表示
if st.session_state.current_chat_name:
    st.caption(f"📝 現在のトピック: **{st.session_state.current_chat_name}**")

# ファイルアップロード
uploaded_file = st.file_uploader(
    "📎 ファイルをアップロード（Excel, CSV, SQL, TXT, JSON など）",
    type=["xlsx", "xls", "csv", "sql", "txt", "json", "xml", "md", "py", "js", "ts", "html", "css", "yaml", "yml", "log", "ini", "conf", "sh", "bat"],
    help="ファイルをドラッグ＆ドロップまたは選択してください"
)

# アップロードされたファイルの内容を取得
uploaded_content = None
if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower()

    try:
        # Excel形式
        if file_ext in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
            uploaded_content = f"【データ形状】{df.shape[0]}行 × {df.shape[1]}列\n\n【列名】\n{', '.join(df.columns.tolist())}\n\n【データ（先頭20行）】\n{df.head(20).to_string()}"
            with st.expander(f"📊 {uploaded_file.name} の内容（クリックで表示）"):
                st.dataframe(df.head(50))
            st.caption(f"✅ Excel読み込み完了（{df.shape[0]}行 × {df.shape[1]}列）。メッセージと一緒に送信されます。")

        # CSV形式
        elif file_ext == "csv":
            df = pd.read_csv(uploaded_file)
            uploaded_content = f"【データ形状】{df.shape[0]}行 × {df.shape[1]}列\n\n【列名】\n{', '.join(df.columns.tolist())}\n\n【データ（先頭20行）】\n{df.head(20).to_string()}"
            with st.expander(f"📊 {uploaded_file.name} の内容（クリックで表示）"):
                st.dataframe(df.head(50))
            st.caption(f"✅ CSV読み込み完了（{df.shape[0]}行 × {df.shape[1]}列）。メッセージと一緒に送信されます。")

        # テキスト形式
        else:
            uploaded_content = uploaded_file.read().decode("utf-8")
            with st.expander(f"📄 {uploaded_file.name} の内容（クリックで表示）"):
                st.code(uploaded_content[:2000] + ("..." if len(uploaded_content) > 2000 else ""), language="text")
            st.caption(f"✅ ファイル読み込み完了（{len(uploaded_content)}文字）。メッセージと一緒に送信されます。")

    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")
        uploaded_content = None

# 入力欄（フォームでEnter送信を確実に）
with st.form(key=f"chat_form_{st.session_state.input_key}", clear_on_submit=True):
    user_input = st.text_input(
        "メッセージを入力",
        placeholder="質問や依頼を入力してください...（Enterで送信）",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns([4, 1])
    with col1:
        send_button = st.form_submit_button("送信", type="primary", use_container_width=True)
    with col2:
        if st.session_state.asking_questions:
            skip_questions = st.form_submit_button("とりあえず回答", use_container_width=True)
        else:
            skip_questions = False

# 「とりあえず回答」処理
if skip_questions and st.session_state.asking_questions:
    st.session_state.chat_history.append({"role": "user", "content": "（とりあえず今の情報で回答してください）"})

    with st.spinner("回答を生成中..."):
        response, search_results = process_message_with_search(
            client, tavily_client,
            st.session_state.original_request,
            st.session_state.collected_info,
            st.session_state.chat_history[:-1],
            selected_framework
        )

    if search_results:
        response += "\n\n---\n*💡 Web検索結果を参考にしました*"

    st.session_state.chat_history.append({"role": "assistant", "content": response})

    # 質問状態をリセット
    st.session_state.asking_questions = False
    st.session_state.pending_questions = []
    st.session_state.collected_info = []
    st.session_state.original_request = None
    st.session_state.input_key += 1
    st.rerun()

# メッセージ送信処理
if send_button and user_input:
    # ファイルが添付されている場合、メッセージに含める
    full_message = user_input
    if uploaded_content:
        file_name = uploaded_file.name if uploaded_file else "file"
        full_message = f"{user_input}\n\n【添付ファイル: {file_name}】\n```\n{uploaded_content[:8000]}\n```"
        if len(uploaded_content) > 8000:
            full_message += "\n（ファイルが長いため最初の8000文字のみ表示）"

    st.session_state.chat_history.append({"role": "user", "content": full_message})

    # 質問中の場合
    if st.session_state.asking_questions:
        # ユーザーが質問してきた場合（例：「例えばどのようなことですか？」）
        if is_user_asking_question(user_input):
            # 直前の質問を取得（履歴から）
            last_ai_message = ""
            for msg in reversed(st.session_state.chat_history[:-1]):
                if msg["role"] == "assistant":
                    last_ai_message = msg["content"]
                    break

            with st.spinner("回答中..."):
                update_usage("groq")
                response = answer_user_question_during_clarification(client, user_input, last_ai_message)

            st.session_state.chat_history.append({"role": "assistant", "content": response})
        else:
            # 通常の回答として収集
            st.session_state.collected_info.append(full_message)

            # 次の質問があるか確認
            if st.session_state.pending_questions:
                next_question = st.session_state.pending_questions.pop(0)
                remaining = len(st.session_state.pending_questions)
                response = generate_single_question(next_question, remaining)
            else:
                # 全ての質問に回答済み → 最終回答を生成
                with st.spinner("回答を生成中..."):
                    response, search_results = process_message_with_search(
                        client, tavily_client,
                        st.session_state.original_request,
                        st.session_state.collected_info,
                        st.session_state.chat_history[:-1],
                        selected_framework
                    )

                if search_results:
                    response += "\n\n---\n*💡 Web検索結果を参考にしました*"

                # 質問状態をリセット
                st.session_state.asking_questions = False
                st.session_state.pending_questions = []
                st.session_state.collected_info = []
                st.session_state.original_request = None

            st.session_state.chat_history.append({"role": "assistant", "content": response})

    else:
        # 新しいリクエスト
        with st.spinner("分析中..."):
            if start_clarification_process(client, full_message):
                # 最初の質問を表示
                first_question = st.session_state.pending_questions.pop(0)
                remaining = len(st.session_state.pending_questions)
                response = generate_single_question(first_question, remaining)
            else:
                # 質問不要なら直接回答
                response, search_results = process_message_with_search(
                    client, tavily_client, full_message, [],
                    st.session_state.chat_history[:-1], selected_framework
                )
                if search_results:
                    response += "\n\n---\n*💡 Web検索結果を参考にしました*"

        st.session_state.chat_history.append({"role": "assistant", "content": response})

    st.session_state.input_key += 1
    st.rerun()

# 便利なアクションボタン（会話がある場合、質問中でない場合）
if st.session_state.chat_history and not st.session_state.asking_questions:
    st.markdown("---")
    st.markdown("#### 💡 続けて質問")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("もっと詳しく", use_container_width=True):
            follow_up = "もう少し詳しく教えてください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message_with_search(client, tavily_client, follow_up, [], st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with col2:
        if st.button("他の案も", use_container_width=True):
            follow_up = "他にも案を出してください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message_with_search(client, tavily_client, follow_up, [], st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with col3:
        if st.button("メリット・デメリット", use_container_width=True):
            follow_up = "それぞれのメリットとデメリットを教えてください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message_with_search(client, tavily_client, follow_up, [], st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with col4:
        if st.button("実施手順", use_container_width=True):
            follow_up = "具体的な実施手順を教えてください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message_with_search(client, tavily_client, follow_up, [], st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
