import streamlit as st
import pandas as pd
import random

class VocabularyData:
    """語彙データの読み込みと問題生成の責務を担うクラス"""
    def __init__(self, csv_file: str):
        try:
            self.df = pd.read_csv(csv_file)
        except FileNotFoundError:
            st.error("致命的エラー: 指定されたデータソースが存在しません。")
            st.stop()

    def generate_question(self, mode: str, level: int) -> dict:
        """指定レベル・モードに基づき、正解とダミー選択肢を抽出する"""
        level_df = self.df[self.df['level'] == level]
        if len(level_df) < 4:
            return {"error": "指定レベルのデータセットが不足しています（最低4語必要）。"}

        # 正解をランダムに1つ選択
        correct_item = level_df.sample(1).iloc[0]
        pos_target = correct_item['pos']

        # ダミーの抽出（同一品詞を優先）
        distractors_df = level_df[(level_df['id'] != correct_item['id']) & (level_df['pos'] == pos_target)]
        
        # 同一品詞が足りない場合は、別品詞から補充して制約を緩和
        if len(distractors_df) < 3:
            fallback_df = level_df[level_df['id'] != correct_item['id']]
            distractors_df = fallback_df.sample(3)
        else:
            distractors_df = distractors_df.sample(3)

        options = [correct_item] + [row for _, row in distractors_df.iterrows()]
        random.shuffle(options)

        # モードに応じた問題テキストと正解の定義
        q_col = 'italian' if mode == "it_to_ja" else 'japanese'
        a_col = 'japanese' if mode == "it_to_ja" else 'italian'

        return {
            "question_text": correct_item[q_col],
            "correct_answer": correct_item[a_col],
            "example_it": correct_item['example_it'],
            "example_ja": correct_item['example_ja'],
            "options": [opt[a_col] for opt in options]
        }

class SessionManager:
    """状態管理（スコア、現在の問題など）の責務を担うクラス"""
    @staticmethod
    def initialize():
        if "score" not in st.session_state:
            st.session_state.score = 0
        if "attempts" not in st.session_state:
            st.session_state.attempts = 0
        if "current_q" not in st.session_state:
            st.session_state.current_q = None
        if "answered" not in st.session_state:
            st.session_state.answered = False

    @staticmethod
    def reset_question():
        st.session_state.current_q = None
        st.session_state.answered = False

class AppUI:
    """インターフェースの描画処理を担うクラス"""
    def __init__(self, vocab_data: VocabularyData):
        self.vocab = vocab_data

    def render(self):
        st.title("イタリア語語彙学習システム")
        
        # コントロールパネル
        col1, col2 = st.columns(2)
        with col1:
            mode = st.selectbox("学習モード", ["it_to_ja", "ja_to_it"], format_func=lambda x: "伊 → 日" if x == "it_to_ja" else "日 → 伊", on_change=SessionManager.reset_question)
        with col2:
            level = st.selectbox("CEFR レベル", [1, 2, 3, 4, 5, 6], format_func=lambda x: f"レベル {x} (A1-C2相当)", on_change=SessionManager.reset_question)

        # スコア表示
        st.write(f"**スコア:** {st.session_state.score} / {st.session_state.attempts}")
        st.markdown("---")

        # 問題の生成と保持
        if st.session_state.current_q is None:
            q_data = self.vocab.generate_question(mode, level)
            if "error" in q_data:
                st.warning(q_data["error"])
                return
            st.session_state.current_q = q_data

        q_data = st.session_state.current_q

        # 問題表示
        st.subheader(f"問題: {q_data['question_text']}")

        # 選択肢ボタンの生成
        if not st.session_state.answered:
            for opt in q_data['options']:
                if st.button(opt, use_container_width=True):
                    st.session_state.attempts += 1
                    if opt == q_data['correct_answer']:
                        st.session_state.score += 1
                        st.success("正解")
                    else:
                        st.error(f"誤答。正解は: {q_data['correct_answer']}")
                    
                    st.info(f"**例文:** {q_data['example_it']} \n\n **訳:** {q_data['example_ja']}")
                    st.session_state.answered = True
                    st.rerun()
        else:
            if st.button("次の問題へ", type="primary"):
                SessionManager.reset_question()
                st.rerun()

# メイン実行ブロック
if __name__ == "__main__":
    SessionManager.initialize()
    vocab_db = VocabularyData("words.csv")
    ui = AppUI(vocab_db)
    ui.render()
