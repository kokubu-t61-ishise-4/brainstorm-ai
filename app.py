"""BrainSpark - AIブレインストーミングアシスタント"""
import streamlit as st
from groq import Groq
from tavily import TavilyClient
import json
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
    base_prompt = """あなたは「BrainSpark」というAIブレインストーミングアシスタントです。

## あなたの役割
- ユーザーのアイデア出し、企画立案、情報検索を支援
- 必要に応じて追加の質問をして、より良い回答を提供
- 店舗・会場検索では詳細な条件を確認

## 回答のルール
1. **情報が不足している場合は必ず質問する**
   - 「〇〇について教えていただけますか？」と具体的に聞く
   - 選択肢を提示すると回答しやすい

2. **店舗・会場検索の場合**
   - 日時、人数、予算、ジャンル、必須条件を確認
   - コース情報、料金、特徴を詳しく紹介
   - 「空き状況は各店舗に直接ご確認ください」と案内

3. **アイデア出しの場合**
   - 目的、対象者、制約条件を確認
   - フレームワークを活用して多角的にアイデアを出す
   - 各アイデアの特徴やメリットを説明

4. **追加質問への対応**
   - 前の回答を踏まえて深掘り
   - 「他にも案が欲しい」→ 別の視点からアイデアを追加
   - 「もっと詳しく」→ 具体的な実施方法を説明

5. **回答形式**
   - 見やすく構造化（見出し、箇条書き）
   - 長すぎない（要点を絞る）
   - 必要に応じて表形式も使用
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


def process_message(client, tavily_client, user_message: str, chat_history: list, framework: str) -> tuple:
    """メッセージを処理し、必要に応じてWeb検索を実行"""

    # Web検索が必要か判断
    search_keywords = ["検索", "探して", "調べて", "会場", "店舗", "お店", "レストラン", "居酒屋",
                       "ホテル", "場所", "最新", "ニュース", "トレンド", "〜とは", "について教えて"]

    needs_search = any(keyword in user_message for keyword in search_keywords)
    search_results = None

    if needs_search and tavily_client:
        # 検索クエリを生成
        search_query = user_message.replace("を探して", "").replace("を調べて", "").replace("を検索", "")
        if "コース" not in search_query and any(k in user_message for k in ["会場", "店舗", "お店", "居酒屋", "レストラン"]):
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

    # 検索結果があれば追加
    if search_results:
        user_content = f"{user_message}\n\n【参考：Web検索結果】\n{search_results}"
    else:
        user_content = user_message

    messages.append({"role": "user", "content": user_content})

    # LLM呼び出し
    response = call_llm(client, messages)

    return response, search_results


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

    # AIの応答を生成
    with st.spinner("考え中..."):
        response, _ = process_message(client, tavily_client, quick_message, st.session_state.chat_history[:-1], selected_framework)

    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()

# 入力欄
st.markdown("---")

# 現在のトピック名を表示
if st.session_state.current_chat_name:
    st.caption(f"📝 現在のトピック: **{st.session_state.current_chat_name}**")

col1, col2 = st.columns([5, 1])

with col1:
    user_input = st.text_input(
        "メッセージを入力",
        placeholder="質問や依頼を入力してください...",
        key=f"user_input_{st.session_state.input_key}",  # キーを動的に変更してリセット
        label_visibility="collapsed"
    )

with col2:
    send_button = st.button("送信", type="primary", use_container_width=True)

# メッセージ送信処理
if send_button and user_input:
    # ユーザーメッセージを追加
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    # AIの応答を生成
    with st.spinner("考え中..."):
        response, search_results = process_message(
            client, tavily_client, user_input,
            st.session_state.chat_history[:-1],  # 最新のユーザーメッセージは除く
            selected_framework
        )

    # 検索結果があれば記録（オプション）
    if search_results:
        response_with_note = response + "\n\n---\n*💡 Web検索結果を参考にしました*"
    else:
        response_with_note = response

    st.session_state.chat_history.append({"role": "assistant", "content": response_with_note})

    # 入力欄をクリア（キーを変更してリセット）
    st.session_state.input_key += 1
    st.rerun()

# 便利なアクションボタン（会話がある場合）
if st.session_state.chat_history:
    st.markdown("---")
    st.markdown("#### 💡 続けて質問")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("もっと詳しく", use_container_width=True):
            follow_up = "もう少し詳しく教えてください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message(client, tavily_client, follow_up, st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with col2:
        if st.button("他の案も", use_container_width=True):
            follow_up = "他にも案を出してください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message(client, tavily_client, follow_up, st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with col3:
        if st.button("メリット・デメリット", use_container_width=True):
            follow_up = "それぞれのメリットとデメリットを教えてください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message(client, tavily_client, follow_up, st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with col4:
        if st.button("実施手順", use_container_width=True):
            follow_up = "具体的な実施手順を教えてください"
            st.session_state.chat_history.append({"role": "user", "content": follow_up})
            with st.spinner("考え中..."):
                response, _ = process_message(client, tavily_client, follow_up, st.session_state.chat_history[:-1], selected_framework)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
