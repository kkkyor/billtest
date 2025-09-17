import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="영업사원 수수료 현황",
    page_icon="👨‍💼",
    layout="wide"
)

# --- 구글 시트 연결 및 데이터 로드 ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    """gspread 클라이언트 객체를 생성하고 캐시합니다."""
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=600)
def load_data_from_google_sheet():
    """구글 시트에서 데이터를 로드하고 실제 시트의 행 번호를 포함한 DataFrame으로 변환합니다."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1A5yp1fIlsLw4OLjd2TX8VHfHLGSExCWvAbu-CBI8Euo/edit?gid=170654087")
        worksheet = spreadsheet.worksheet("온라인")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        # ❗ 변경점 1: 실제 시트의 행 번호를 추적하기 위한 열 추가 (헤더가 1행이므로 데이터는 2행부터 시작)
        df['sheet_row_number'] = range(2, len(df) + 2)
        return worksheet, df
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None, None

# ❗ 변경점 2: '전체 삭제 후 새로 쓰기' 대신 '부분 업데이트' 함수로 교체
def update_rows_in_sheet(worksheet, edited_df):
    """수정된 DataFrame의 각 행을 구글 시트의 해당 위치에 업데이트합니다."""
    try:
        headers = worksheet.row_values(1)
        if 'sheet_row_number' not in edited_df.columns:
            st.error("업데이트할 행 번호를 찾을 수 없습니다. 데이터 로딩 부분을 확인해주세요.")
            return False

        # 여러 행을 한번에 업데이트하기 위한 리스트 준비
        update_requests = []
        for index, row in edited_df.iterrows():
            row_number = int(row['sheet_row_number'])
            # 시트의 헤더 순서에 맞게 행 데이터 정렬
            ordered_row_values = [row.get(h, '') for h in headers]
            update_requests.append({
                'range': f'A{row_number}', # A열부터 시작하는 행 전체 범위
                'values': [ordered_row_values],
            })
        
        # gspread의 batch_update 기능을 사용하여 여러 행을 한번의 API 호출로 업데이트
        if update_requests:
            worksheet.batch_update(update_requests, value_input_option='USER_ENTERED')

        return True
    except Exception as e:
        st.error(f"시트 업데이트 중 오류 발생: {e}")
        return False

# --- UI 구성 ---
st.title("👨‍💼 영업사원별 수수료 현황 조회 및 편집")
st.markdown("---")

worksheet, df = load_data_from_google_sheet()

if df is not None:
    if '영업자' in df.columns:
        salespeople = sorted(df['영업자'].dropna().unique())

        with st.sidebar:
            st.header("🔍 검색 옵션")
            selected_salesperson = st.selectbox(
                "영업자 이름을 선택하세요:",
                options=[""] + salespeople,
                index=0,
                key="salesperson_selector"
            )
            st.info("조회할 영업자의 이름을 목록에서 선택하세요.")

        st.header(f"📋 '{selected_salesperson}' 님 데이터 편집")

        if selected_salesperson:
            result_df = df[df['영업자'] == selected_salesperson].copy()
            
            if not result_df.empty:
                st.info("✍️ 표시가 된 항목들은 **입력을 권장**하는 주요 항목입니다. 셀을 더블클릭하여 수정해주세요.")

                edited_df = st.data_editor(
                    result_df,
                    column_config={
                        # ❗ 변경점 3: 사용자에게 보일 필요 없는 행 번호 열은 숨김 처리
                        "sheet_row_number": None, 
                        "수수료율입력": st.column_config.NumberColumn(
                            "✍️ 수수료율", help="수수료 **비율(%)**을 입력해주세요. 예: 3.5"
                        ),
                        "수수료금액입력": st.column_config.NumberColumn(
                            "✍️ 수수료금액", help="계산된 **수수료 총액**을 입력해주세요."
                        ),
                        "전화번호": st.column_config.TextColumn(
                            "✍️ 전화번호", help="고객의 연락처를 입력해주세요."
                        ),
                        "전기차보조금": st.column_config.NumberColumn(
                            "✍️ 전기차보조금", help="전기차 보조금이 있는 경우 **금액**을 입력해주세요."
                        )
                    },
                    num_rows="dynamic",
                    key=f"editor_{selected_salesperson}"
                )

                st.markdown("---")
                
                # ❗ 변경점 4: 새로운 업데이트 함수를 호출하도록 버튼 로직 수정
                if st.button("💾 변경사항 구글 시트에 저장하기", type="primary"):
                    with st.spinner("저장 중..."):
                        # Pandas의 `compare` 기능을 사용하여 실제로 변경된 행만 필터링
                        changes = result_df.compare(edited_df)
                        if not changes.empty:
                            changed_indices = changes.index
                            rows_to_update = edited_df.loc[changed_indices]
                            
                            if update_rows_in_sheet(worksheet, rows_to_update):
                                st.success("🎉 성공적으로 구글 시트에 저장되었습니다!")
                                st.cache_data.clear()
                                st.rerun() # 저장 후 즉시 새로고침하여 최신 상태 반영
                            else:
                                st.error("저장에 실패했습니다.")
                        else:
                            st.info("변경된 내용이 없습니다.")
            else:
                st.warning("선택하신 이름과 일치하는 데이터가 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 조회할 영업자 이름을 선택해주세요.")
    else:
        st.error("'영업자' 열을 찾을 수 없습니다. 구글 시트의 열 이름을 확인해주세요.")
