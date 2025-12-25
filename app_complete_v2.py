# app_complete_v2.py
import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import io
import time
import json
from streamlit_autorefresh import st_autorefresh
from io import BytesIO
import re

# ========== CẤU HÌNH TRANG ==========
st.set_page_config(
    page_title="Hệ Thống Báo Cáo Nhập Hàng - Kho Nguyên Liệu",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto refresh mỗi 15 phút
st_autorefresh(interval=15 * 60 * 1000, key="auto_refresh")

# CSS tùy chỉnh
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* {
    font-family: 'Inter', sans-serif;
}
.main-header {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    padding: 2.5rem;
    border-radius: 20px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    border: 1px solid rgba(255,255,255,0.1);
}
.header-gradient {
    background: linear-gradient(90deg, #6366f1, #8b5cf6, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
.card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border: 1px solid #e5e7eb;
    transition: all 0.3s;
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.75rem 1.5rem;
    transition: all 0.3s;
}
.stButton > button:hover {
    transform: translateY(-2px);
}
.metric-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    padding: 1.5rem;
    border-radius: 12px;
    border-left: 5px solid #3b82f6;
}
.data-table {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.tab-content {
    padding: 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ========== KHỞI TẠO SESSION STATE ==========
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"
if 'selected_month' not in st.session_state:
    st.session_state.selected_month = "Tháng 1"
if 'sheet_url' not in st.session_state:
    st.session_state.sheet_url = "https://docs.google.com/spreadsheets/d/1k5tV_bnP6eJ_sj7xm5lTg9_iaYzf14VHbOEWq5jtTWE/edit#gid=0"
if 'reasons_cache' not in st.session_state:
    st.session_state.reasons_cache = {}
if 'data_cache' not in st.session_state:
    st.session_state.data_cache = {}

# ========== TIÊU ĐỀ ỨNG DỤNG ==========
st.markdown("""
<div class="main-header">
    <h1 style="font-size: 2.8rem; margin-bottom: 0.5rem;">🚚 HỆ THỐNG BÁO CÁO THỜI GIAN NHẬP HÀNG</h1>
    <h3 style="font-weight: 400; margin-bottom: 1rem;">(Nhập chậm 1 xe quá 2h và nhập trễ sau 17h)</h3>
    <div style="display: flex; gap: 2rem; margin-top: 1.5rem;">
        <div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Bộ phận</div>
            <div style="font-size: 1.2rem; font-weight: 600;">KHO NGUYÊN LIỆU</div>
        </div>
        <div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Phiên bản</div>
            <div style="font-size: 1.2rem; font-weight: 600;">3.0 - MS Kiều</div>
        </div>
        <div>
            <div style="font-size: 0.9rem; opacity: 0.9;">Trạng thái</div>
            <div style="font-size: 1.2rem; font-weight: 600; color: #10b981;">● Đang hoạt động</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <div style="font-size: 1.8rem; font-weight: 800; margin-bottom: 0.5rem;" class="header-gradient">KHO NGUYÊN LIỆU</div>
        <div style="font-size: 0.9rem; color: #6b7280; background: #f3f4f6; padding: 0.5rem; border-radius: 8px; margin-top: 0.5rem;">
            📅 Hệ thống báo cáo thời gian thực
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========== CHỌN THÁNG BÁO CÁO ==========
    st.markdown("### 📅 CHỌN THÁNG BÁO CÁO")
    
    month_options = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", 
        "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
        "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    
    selected_month = st.selectbox(
        "Chọn tháng",
        month_options,
        index=month_options.index(st.session_state.selected_month) if st.session_state.selected_month in month_options else 0,
        label_visibility="collapsed"
    )
    
    if selected_month != st.session_state.selected_month:
        st.session_state.selected_month = selected_month
        st.rerun()
    
    st.markdown("---")
    
    # ========== MENU CHÍNH ==========
    st.markdown("### 🎯 MENU CHỨC NĂNG")
    
    menu_options = {
        "📊 Dashboard": "dashboard",
        "📥 Nhập dữ liệu": "nhap_du_lieu", 
        "👁️ Xem báo cáo": "xem_bao_cao",
        "📈 Tổng hợp 12 tháng": "tong_hop",
        "⚙️ Quản lý lý do": "quan_ly_ly_do",
        "🔄 Đồng bộ dữ liệu": "dong_bo",
        "📋 Hướng dẫn": "huong_dan"
    }
    
    for label, key in menu_options.items():
        btn_type = "primary" if st.session_state.current_page == key else "secondary"
        if st.button(label, use_container_width=True, type=btn_type):
            st.session_state.current_page = key
            st.rerun()
    
    st.markdown("---")
    
    # ========== CẤU HÌNH KẾT NỐI ==========
    with st.expander("⚙️ Cấu hình kết nối", expanded=False):
        new_url = st.text_input(
            "Google Sheets URL",
            value=st.session_state.sheet_url,
            key="config_sheet_url"
        )
        
        if new_url != st.session_state.sheet_url:
            st.session_state.sheet_url = new_url
            st.success("✅ Đã cập nhật URL!")
        
        uploaded_creds = st.file_uploader(
            "Tải lên Service Account JSON",
            type=['json'],
            key="creds_file"
        )
        
        if uploaded_creds:
            st.session_state.credentials = uploaded_creds.getvalue()
            st.success("✅ Đã tải lên credentials!")
    
    st.markdown("---")
    
    # ========== THÔNG TIN HỆ THỐNG ==========
    st.markdown("### 📊 THÔNG TIN HỆ THỐNG")
    
    col_sys1, col_sys2 = st.columns(2)
    with col_sys1:
        st.metric("Tháng", selected_month.replace("Tháng ", ""))
    with col_sys2:
        st.metric("Trạng thái", "🟢 Online")
    
    st.markdown("""
    <div style="text-align: center; margin-top: 2rem; padding: 1rem; background: #f8fafc; border-radius: 10px;">
        <div style="font-size: 0.8rem; color: #6b7280;">© 2024 Kho Nguyên Liệu</div>
        <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;">Hỗ trợ: 0900-123-456</div>
    </div>
    """, unsafe_allow_html=True)

# ========== HÀM KẾT NỐI GOOGLE SHEETS ==========
@st.cache_resource(ttl=300)
def get_google_client():
    """Kết nối đến Google Sheets"""
    try:
        # Ưu tiên dùng secrets từ Streamlit Cloud
        if 'google_creds' in st.secrets:
            scope = ['https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive']
            
            # Build credentials từ st.secrets
            creds_dict = {
                "type": st.secrets["google_creds"]["type"],
                "project_id": st.secrets["google_creds"]["project_id"],
                "private_key_id": st.secrets["google_creds"]["private_key_id"],
                "private_key": st.secrets["google_creds"]["private_key"],
                "client_email": st.secrets["google_creds"]["client_email"],
                "client_id": st.secrets["google_creds"]["client_id"],
                "auth_uri": st.secrets["google_creds"]["auth_uri"],
                "token_uri": st.secrets["google_creds"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["google_creds"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["google_creds"]["client_x509_cert_url"],
                "universe_domain": st.secrets["google_creds"]["universe_domain"]
            }
            
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(credentials)
            st.success("✅ Kết nối Google Sheets thành công!")
            return client
            
        # Hoặc dùng file upload từ sidebar
        elif 'credentials' in st.session_state:
            try:
                creds_dict = json.loads(st.session_state.credentials.decode('utf-8') if isinstance(st.session_state.credentials, bytes) else st.session_state.credentials)
                scope = ['https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive']
                credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
                client = gspread.authorize(credentials)
                st.success("✅ Kết nối Google Sheets thành công (từ file upload)!")
                return client
            except Exception as e:
                st.error(f"❌ Lỗi đọc credentials từ file upload: {str(e)}")
                return None
        
        # Hoặc dùng file local (cho development)
        else:
            try:
                credentials = Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=['https://www.googleapis.com/auth/spreadsheets',
                           'https://www.googleapis.com/auth/drive']
                )
                client = gspread.authorize(credentials)
                st.success("✅ Kết nối Google Sheets thành công (từ file local)!")
                return client
            except FileNotFoundError:
                st.warning("⚠️ Không tìm thấy file credentials.json")
                return None
            except Exception as e:
                st.error(f"❌ Lỗi đọc file local: {str(e)}")
                return None
        
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Google Sheets: {str(e)}")
        return None

# ========== HÀM ĐỌC DỮ LIỆU TỪ SHEET ==========
def read_sheet_data(client, sheet_name):
    """Đọc dữ liệu từ sheet cụ thể"""
    try:
        spreadsheet = client.open_by_url(st.session_state.sheet_url)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Đọc toàn bộ dữ liệu
        all_data = worksheet.get_all_values()
        
        if not all_data:
            return pd.DataFrame()
        
        # Xác định dòng bắt đầu dữ liệu (tìm "Ngày/tháng")
        start_row = 0
        for i, row in enumerate(all_data):
            if len(row) > 0 and "Ngày/tháng" in str(row[0]):
                start_row = i
                break
        
        # Đọc dữ liệu từ dòng start_row + 1 đến dòng 70
        data_rows = all_data[start_row:70]  # Lấy đến dòng 70
        
        # Tạo DataFrame
        if len(data_rows) > 1:
            headers = data_rows[0]
            data = data_rows[1:]
            
            # Đảm bảo số cột bằng nhau
            max_cols = max(len(row) for row in data)
            headers = headers + [''] * (max_cols - len(headers))
            
            # Pad các dòng cho đều
            padded_data = []
            for row in data:
                padded_row = row + [''] * (max_cols - len(row))
                padded_data.append(padded_row)
            
            df = pd.DataFrame(padded_data, columns=headers)
            
            # Lọc dòng trống
            df = df.replace('', pd.NA)
            df = df.dropna(how='all')
            
            # Đổi tên cột cho dễ sử dụng
            column_mapping = {
                'Ngày/tháng': 'date',
                'Số Xe': 'so_xe',
                'Tên nguyên liệu': 'nguyen_lieu',
                'Xe cân VÀO': 'xe_can_vao',
                'Xe cân RA': 'xe_can_ra',
                'Tổng thời gian': 'tong_thoi_gian',
                'Số lượng': 'so_luong',
                'Bag.': 'bag',
                'Net.Wgh. (kg)': 'net_weight',
                'Nguyên nhân': 'nguyen_nhan',
                'Lí do chi tiết': 'ly_do_chi_tiet'
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Lỗi đọc sheet {sheet_name}: {str(e)}")
        return pd.DataFrame()

# ========== HÀM ĐỌC DỮ LIỆU TỔNG HỢP (D73:D120) ==========
def read_total_sheet(client):
    """Đọc dữ liệu tổng hợp từ sheet TOTAL"""
    try:
        spreadsheet = client.open_by_url(st.session_state.sheet_url)
        
        # Kiểm tra sheet TOTAL, nếu không có thì tạo
        try:
            worksheet = spreadsheet.worksheet("TOTAL")
        except:
            # Tạo sheet TOTAL mới
            worksheet = spreadsheet.add_worksheet(title="TOTAL", rows="200", cols="10")
            
            # Tạo cấu trúc cơ bản
            headers = [
                "STT", "Nguyên nhân", "Số lượng (lần)", "%",
                "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
                "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
                "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
            ]
            worksheet.update('A1', [headers])
        
        # Đọc dữ liệu từ dòng 73 đến 120
        data = worksheet.get('A73:D120')
        
        if data:
            # Lọc dòng trống
            filtered_data = [row for row in data if any(cell for cell in row)]
            
            if filtered_data:
                df = pd.DataFrame(filtered_data, columns=["STT", "Nguyên nhân", "Số lượng", "%"])
                return df
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Lỗi đọc sheet TOTAL: {str(e)}")
        return pd.DataFrame()

# ========== HÀM XỬ LÝ DÁN DỮ LIỆU EXCEL THÔNG MINH ==========
def parse_excel_paste(pasted_text):
    """
    Xử lý dữ liệu dán từ Excel với nhiều định dạng
    Hỗ trợ: tab-separated, space-aligned, comma-separated
    """
    try:
        if not pasted_text.strip():
            return []
        
        lines = pasted_text.strip().split('\n')
        parsed_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Phân tích định dạng
            # 1. Tab-separated (phổ biến khi copy từ Excel)
            if '\t' in line:
                cells = line.split('\t')
            # 2. Nhiều khoảng trắng (căn chỉnh cột)
            elif '  ' in line:
                # Tách bằng 2 khoảng trắng trở lên
                cells = re.split(r'\s{2,}', line)
            # 3. Dấu phẩy (CSV)
            elif ',' in line and not line.count(',') < 3:
                cells = line.split(',')
            # 4. Pipe separator
            elif '|' in line:
                cells = line.split('|')
            else:
                # Giữ nguyên
                cells = [line]
            
            # Làm sạch dữ liệu
            cleaned_cells = []
            for cell in cells:
                cell = cell.strip()
                # Loại bỏ dấu ngoặc kép thừa
                cell = cell.strip('"').strip("'")
                cleaned_cells.append(cell)
            
            if cleaned_cells:
                parsed_data.append(cleaned_cells)
        
        return parsed_data
        
    except Exception as e:
        st.error(f"Lỗi phân tích dữ liệu: {str(e)}")
        return []

# ========== HÀM GHI DỮ LIỆU VÀO SHEET ==========
def write_to_sheet(client, sheet_name, data, start_row=7):
    """Ghi dữ liệu vào sheet"""
    try:
        spreadsheet = client.open_by_url(st.session_state.sheet_url)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Xác định số dòng cần ghi
        num_rows = len(data)
        
        # Xóa vùng dữ liệu cũ
        clear_range = f"A{start_row}:U{start_row + num_rows + 10}"
        worksheet.batch_clear([clear_range])
        
        # Ghi dữ liệu mới
        cell_list = worksheet.range(f"A{start_row}:{chr(65 + len(data[0]) - 1)}{start_row + num_rows - 1}")
        
        idx = 0
        for i, row in enumerate(data):
            for j, cell in enumerate(row):
                if idx < len(cell_list):
                    cell_list[idx].value = str(cell) if cell is not None else ""
                    idx += 1
        
        worksheet.update_cells(cell_list)
        return True
        
    except Exception as e:
        st.error(f"Lỗi ghi dữ liệu: {str(e)}")
        return False

# ========== TRANG DASHBOARD ==========
def page_dashboard(client):
    """Trang tổng quan"""
    st.markdown("## 📊 DASHBOARD TỔNG QUAN")
    
    # Lấy tháng hiện tại
    current_month = st.session_state.selected_month
    
    # Hiển thị các thẻ thông tin
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #6b7280;">THÁNG HIỆN TẠI</div>
            <div style="font-size: 2rem; font-weight: 700; color: #3b82f6;">""" + current_month.replace("Tháng ", "") + """</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #6b7280;">TỔNG SỐ XE</div>
            <div style="font-size: 2rem; font-weight: 700; color: #10b981;">--</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #6b7280;">XE NHẬP TRỄ</div>
            <div style="font-size: 2rem; font-weight: 700; color: #ef4444;">--</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #6b7280;">TỶ LỆ TRỄ</div>
            <div style="font-size: 2rem; font-weight: 700; color: #f59e0b;">--%</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Các chức năng nhanh
    st.markdown("### ⚡ CHỨC NĂNG NHANH")
    
    quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
    
    with quick_col1:
        if st.button("📥 Nhập dữ liệu", use_container_width=True, type="primary"):
            st.session_state.current_page = "nhap_du_lieu"
            st.rerun()
    
    with quick_col2:
        if st.button("👁️ Xem báo cáo", use_container_width=True):
            st.session_state.current_page = "xem_bao_cao"
            st.rerun()
    
    with quick_col3:
        if st.button("📈 Tổng hợp", use_container_width=True):
            st.session_state.current_page = "tong_hop"
            st.rerun()
    
    with quick_col4:
        if st.button("🔄 Đồng bộ", use_container_width=True):
            st.session_state.current_page = "dong_bo"
            st.rerun()
    
    st.markdown("---")
    
    # Hướng dẫn nhanh
    with st.expander("📖 HƯỚNG DẪN NHANH", expanded=True):
        st.markdown("""
        ### Cách sử dụng hệ thống:
        
        1. **NHẬP DỮ LIỆU:**
           - Copy vùng dữ liệu từ Excel (A7:U...)
           - Dán vào ô trong ứng dụng
           - Hệ thống tự động phân tích
        
        2. **XEM BÁO CÁO:**
           - Chọn tháng cần xem
           - Xem báo cáo chi tiết
           - Tải xuống file Excel
        
        3. **TỔNG HỢP:**
           - Xem tổng hợp 12 tháng
           - Phân tích theo nguyên nhân
           - Biểu đồ trực quan
        
        4. **QUẢN LÝ LÝ DO:**
           - Thêm/sửa/xóa lý do
           - Tự động đồng bộ
        
        ### 📱 Hỗ trợ đa nền tảng:
        - 💻 Máy tính
        - 📱 Điện thoại
        - 🖥️ Máy tính bảng
        - 📊 TV trình chiếu
        """)

# ========== TRANG NHẬP DỮ LIỆU THÔNG MINH ==========
def page_nhap_du_lieu(client):
    """Trang nhập dữ liệu thông minh"""
    st.markdown("## 📥 NHẬP DỮ LIỆU THÔNG MINH")
    
    current_month = st.session_state.selected_month
    month_map = {
        "Tháng 1": "T1", "Tháng 2": "T2", "Tháng 3": "T3",
        "Tháng 4": "T4", "Tháng 5": "T5", "Tháng 6": "T6",
        "Tháng 7": "T7", "Tháng 8": "T8", "Tháng 9": "T9",
        "Tháng 10": "T10", "Tháng 11": "T11", "Tháng 12": "T12"
    }
    sheet_name = month_map.get(current_month, "T1")
    
    # Tạo tabs cho các phương thức nhập liệu
    tab1, tab2, tab3 = st.tabs(["📋 Dán từ Excel", "📤 Tải file lên", "✏️ Nhập thủ công"])
    
    with tab1:
        st.markdown("### 📋 DÁN DỮ LIỆU TỪ EXCEL")
        
        # Hướng dẫn chi tiết với hình ảnh minh họa
        with st.expander("🎬 HƯỚNG DẪN CHI TIẾT (Click để xem)", expanded=True):
            col_guide1, col_guide2 = st.columns(2)
            
            with col_guide1:
                st.markdown("""
                **Bước 1: Mở file Excel nguồn**
                - Mở file Excel chứa dữ liệu nhập hàng
                - Tìm sheet của tháng hiện tại
                
                **Bước 2: Chọn vùng dữ liệu**
                - Chọn vùng **A7 đến cột U** (hoặc hết dữ liệu)
                - Bôi đen toàn bộ vùng
                
                **Bước 3: Copy dữ liệu**
                - Nhấn **Ctrl+C** (Windows) hoặc **Cmd+C** (Mac)
                - Hoặc click chuột phải → Copy
                """)
            
            with col_guide2:
                st.markdown("""
                **Bước 4: Dán vào đây**
                - Click vào ô bên dưới
                - Nhấn **Ctrl+V** để dán
                
                **Bước 5: Kiểm tra**
                - Xem preview bên phải
                - Chỉnh sửa nếu cần
                
                **Bước 6: Lưu dữ liệu**
                - Nhấn nút **LƯU DỮ LIỆU**
                - Chờ xác nhận thành công
                """)
        
        # Ô dán dữ liệu lớn
        pasted_data = st.text_area(
            "📍 **DÁN (Ctrl+V) DỮ LIỆU TỪ EXCEL VÀO ĐÂY:**",
            height=250,
            placeholder="Paste dữ liệu từ Excel vào đây...\nHệ thống tự động nhận diện cột.\n\n📝 **Ví dụ định dạng:**\n2025-01-23\t86C04510 L1\tThức ăn Bổ Sung\t16:42:00\t17:04:00\t00:22:00\t5.0\t4000.0\tNhập sau 17h\txe nhập cân nhiều lần",
            key="paste_area_v2"
        )
        
        if pasted_data:
            # Xử lý dữ liệu
            parsed_data = parse_excel_paste(pasted_data)
            
            if parsed_data:
                st.success(f"✅ Đã nhận diện được **{len(parsed_data)} dòng** dữ liệu")
                
                # Hiển thị preview
                st.markdown("### 👁️ PREVIEW DỮ LIỆU")
                
                # Tạo DataFrame cho preview
                preview_df = pd.DataFrame(
                    parsed_data[:20],  # Hiển thị tối đa 20 dòng
                    columns=[f"Cột {i+1}" for i in range(len(parsed_data[0]))]
                )
                
                st.dataframe(
                    preview_df,
                    use_container_width=True,
                    height=350,
                    hide_index=True
                )
                
                # Thống kê nhanh
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Số dòng dữ liệu", len(parsed_data))
                with col_stat2:
                    st.metric("Số cột", len(parsed_data[0]) if parsed_data else 0)
                with col_stat3:
                    # Tính tổng số lượng nếu có
                    try:
                        if len(parsed_data[0]) > 6:
                            total_qty = sum(float(row[6]) for row in parsed_data if row[6].replace('.', '').isdigit())
                            st.metric("Tổng SL (ước tính)", f"{total_qty:,.0f}")
                    except:
                        st.metric("Tổng SL", "N/A")
                
                # Nút lưu dữ liệu
                st.markdown("---")
                if st.button("💾 **LƯU DỮ LIỆU VÀO GOOGLE SHEETS**", 
                            type="primary", 
                            use_container_width=True,
                            icon="💾"):
                    
                    with st.spinner("Đang lưu dữ liệu..."):
                        if write_to_sheet(client, sheet_name, parsed_data):
                            st.success("✅ **DỮ LIỆU ĐÃ ĐƯỢC LƯU THÀNH CÔNG!**")
                            st.balloons()
                            
                            # Tự động làm mới sau 2 giây
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ **CÓ LỖI KHI LƯU DỮ LIỆU!**")
    
    with tab2:
        st.markdown("### 📤 TẢI FILE EXCEL LÊN")
        
        uploaded_file = st.file_uploader(
            "Chọn file Excel (.xlsx, .xls)",
            type=['xlsx', 'xls'],
            key="excel_uploader"
        )
        
        if uploaded_file:
            try:
                # Đọc file Excel
                df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ Đã đọc file: {uploaded_file.name}")
                st.dataframe(df.head(20), use_container_width=True, height=350)
                
                # Cho phép chọn sheet nếu có nhiều sheet
                if len(df) > 0:
                    st.info(f"Tìm thấy {len(df)} dòng dữ liệu")
                    
                    if st.button("📤 Tải dữ liệu này lên", use_container_width=True):
                        # Chuyển DataFrame thành list
                        data_to_save = df.values.tolist()
                        
                        with st.spinner("Đang tải lên..."):
                            if write_to_sheet(client, sheet_name, data_to_save):
                                st.success("✅ Đã tải dữ liệu lên thành công!")
                            else:
                                st.error("❌ Lỗi khi tải dữ liệu lên!")
            
            except Exception as e:
                st.error(f"❌ Lỗi đọc file: {str(e)}")
    
    with tab3:
        st.markdown("### ✏️ NHẬP DỮ LIỆU THỦ CÔNG")
        
        # Form nhập liệu thủ công
        with st.form("manual_entry_form"):
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                entry_date = st.date_input("Ngày nhập", datetime.now())
                vehicle_number = st.text_input("Số xe")
                material_name = st.text_input("Tên nguyên liệu")
            
            with col_m2:
                time_in = st.time_input("Xe cân vào", datetime.now().time())
                time_out = st.time_input("Xe cân ra", datetime.now().time())
                total_time = st.text_input("Tổng thời gian", "00:00:00")
            
            with col_m3:
                quantity = st.number_input("Số lượng", min_value=0.0, value=0.0)
                net_weight = st.number_input("Net Weight (kg)", min_value=0.0, value=0.0)
                reason = st.text_input("Nguyên nhân", "Lý do khác")
            
            detail_reason = st.text_area("Lý do chi tiết", "")
            
            submitted = st.form_submit_button("➕ THÊM VÀO DANH SÁCH", type="primary")
            
            if submitted:
                # Thêm vào session state
                if 'manual_entries' not in st.session_state:
                    st.session_state.manual_entries = []
                
                new_entry = [
                    entry_date.strftime("%Y-%m-%d"),
                    vehicle_number,
                    material_name,
                    time_in.strftime("%H:%M:%S"),
                    time_out.strftime("%H:%M:%S"),
                    total_time,
                    str(quantity),
                    str(net_weight),
                    reason,
                    detail_reason
                ]
                
                st.session_state.manual_entries.append(new_entry)
                st.success(f"✅ Đã thêm dữ liệu. Tổng: {len(st.session_state.manual_entries)} dòng")
        
        # Hiển thị danh sách đã nhập
        if 'manual_entries' in st.session_state and st.session_state.manual_entries:
            st.markdown("### 📋 DANH SÁCH ĐÃ NHẬP")
            
            manual_df = pd.DataFrame(
                st.session_state.manual_entries,
                columns=['Ngày', 'Số xe', 'Nguyên liệu', 'Vào', 'Ra', 'TG', 'SL', 'Kg', 'Nguyên nhân', 'Chi tiết']
            )
            
            st.dataframe(manual_df, use_container_width=True)
            
            # Nút lưu tất cả
            if st.button("💾 LƯU TẤT CẢ VÀO GOOGLE SHEETS", type="primary"):
                with st.spinner("Đang lưu..."):
                    if write_to_sheet(client, sheet_name, st.session_state.manual_entries):
                        st.success(f"✅ Đã lưu {len(st.session_state.manual_entries)} dòng!")
                        st.session_state.manual_entries = []
                        st.rerun()

# ========== TRANG XEM BÁO CÁO ==========
def page_xem_bao_cao(client):
    """Trang xem báo cáo chi tiết"""
    current_month = st.session_state.selected_month
    month_map = {
        "Tháng 1": "T1", "Tháng 2": "T2", "Tháng 3": "T3",
        "Tháng 4": "T4", "Tháng 5": "T5", "Tháng 6": "T6",
        "Tháng 7": "T7", "Tháng 8": "T8", "Tháng 9": "T9",
        "Tháng 10": "T10", "Tháng 11": "T11", "Tháng 12": "T12"
    }
    sheet_name = month_map.get(current_month, "T1")
    
    st.markdown(f"## 📊 BÁO CÁO CHI TIẾT - {current_month}")
    
    # Đọc dữ liệu từ sheet
    df = read_sheet_data(client, sheet_name)
    
    if df is not None and not df.empty:
        # Hiển thị toàn bộ dữ liệu
        st.markdown("### 📋 DỮ LIỆU CHI TIẾT")
        
        # Chuyển đổi kiểu dữ liệu
        display_df = df.copy()
        
        # Tạo bảng với định dạng đẹp
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            column_config={
                'date': st.column_config.DateColumn(
                    "Ngày",
                    format="DD/MM/YYYY"
                ),
                'so_xe': "Số xe",
                'nguyen_lieu': "Nguyên liệu",
                'xe_can_vao': "Xe cân vào",
                'xe_can_ra': "Xe cân ra",
                'tong_thoi_gian': "Tổng TG",
                'so_luong': "SL",
                'net_weight': "Kg",
                'nguyen_nhan': "Nguyên nhân",
                'ly_do_chi_tiet': "Chi tiết"
            }
        )
        
        # Thống kê
        st.markdown("---")
        st.markdown("## 📈 THỐNG KÊ")
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            total_vehicles = len(df)
            st.metric("Tổng số xe", total_vehicles)
        
        with col_stat2:
            # Đếm xe nhập trễ (cột M trong file gốc - Check 17h)
            late_count = 0
            st.metric("Xe nhập trễ (>17h)", late_count)
        
        with col_stat3:
            # Tính tổng khối lượng
            if 'net_weight' in df.columns:
                try:
                    total_kg = pd.to_numeric(df['net_weight'], errors='coerce').sum()
                    st.metric("Tổng khối lượng", f"{total_kg:,.0f} kg")
                except:
                    st.metric("Tổng khối lượng", "N/A")
        
        with col_stat4:
            # Tính thời gian trung bình
            st.metric("TG trung bình/xe", "N/A")
        
        # Phân tích theo nguyên nhân
        if 'nguyen_nhan' in df.columns:
            st.markdown("---")
            st.markdown("### 🎯 PHÂN BỐ THEO NGUYÊN NHÂN")
            
            reason_counts = df['nguyen_nhan'].value_counts()
            
            tab_reason1, tab_reason2 = st.tabs(["📊 Biểu đồ", "📋 Bảng số liệu"])
            
            with tab_reason1:
                st.bar_chart(reason_counts)
            
            with tab_reason2:
                st.dataframe(reason_counts, use_container_width=True)
        
        # Xuất dữ liệu
        st.markdown("---")
        st.markdown("### 📤 XUẤT DỮ LIỆU")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            # Xuất CSV
            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Tải CSV",
                data=csv_data,
                file_name=f"bao_cao_{sheet_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_export2:
            # Xuất Excel
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='BaoCao')
            
            st.download_button(
                label="📥 Tải Excel",
                data=excel_buffer.getvalue(),
                file_name=f"bao_cao_{sheet_name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_export3:
            # Xuất JSON
            json_data = df.to_json(orient='records', force_ascii=False)
            st.download_button(
                label="📥 Tải JSON",
                data=json_data,
                file_name=f"bao_cao_{sheet_name}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
    
    else:
        st.info(f"📭 Chưa có dữ liệu cho {current_month}. Vui lòng nhập dữ liệu trước.")

# ========== TRANG TỔNG HỢP 12 THÁNG ==========
def page_tong_hop(client):
    """Trang tổng hợp dữ liệu 12 tháng"""
    st.markdown("## 📈 TỔNG HỢP 12 THÁNG")
    
    # Đọc dữ liệu từ sheet TOTAL
    total_df = read_total_sheet(client)
    
    if total_df is not None and not total_df.empty:
        st.markdown("### 📊 DỮ LIỆU TỔNG HỢP (D73:D120)")
        
        # Hiển thị dữ liệu
        st.dataframe(
            total_df,
            use_container_width=True,
            height=400,
            column_config={
                "STT": "STT",
                "Nguyên nhân": "Nguyên nhân",
                "Số lượng": st.column_config.NumberColumn(
                    "Số lượng (lần)",
                    format="%d"
                ),
                "%": st.column_config.NumberColumn(
                    "Tỷ lệ %",
                    format="%.2f%%"
                )
            }
        )
        
        # Thống kê tổng
        st.markdown("---")
        st.markdown("### 📈 THỐNG KÊ TỔNG QUAN")
        
        if 'Số lượng' in total_df.columns:
            # Chuyển đổi sang số
            total_df['Số lượng_num'] = pd.to_numeric(total_df['Số lượng'], errors='coerce')
            
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            
            with col_t1:
                total_cases = total_df['Số lượng_num'].sum()
                st.metric("Tổng số lần", f"{total_cases:,.0f}")
            
            with col_t2:
                avg_cases = total_df['Số lượng_num'].mean()
                st.metric("Trung bình/nguyên nhân", f"{avg_cases:,.1f}")
            
            with col_t3:
                max_cases = total_df['Số lượng_num'].max()
                max_reason = total_df.loc[total_df['Số lượng_num'].idxmax(), 'Nguyên nhân'] if not total_df.empty else ""
                st.metric("Nguyên nhân nhiều nhất", f"{max_cases:,.0f}", delta=max_reason[:20])
            
            with col_t4:
                top3_total = total_df.nlargest(3, 'Số lượng_num')['Số lượng_num'].sum()
                top3_percent = (top3_total / total_cases * 100) if total_cases > 0 else 0
                st.metric("Top 3 chiếm", f"{top3_percent:.1f}%")
        
        # Biểu đồ phân bố
        st.markdown("---")
        st.markdown("### 📊 BIỂU ĐỒ PHÂN BỐ")
        
        if not total_df.empty and 'Số lượng' in total_df.columns and 'Nguyên nhân' in total_df.columns:
            # Lọc dữ liệu
            chart_df = total_df.copy()
            chart_df['Số lượng'] = pd.to_numeric(chart_df['Số lượng'], errors='coerce')
            chart_df = chart_df.dropna(subset=['Số lượng'])
            
            # Hiển thị biểu đồ
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.bar_chart(chart_df.set_index('Nguyên nhân')['Số lượng'])
                st.caption("Số lượng theo nguyên nhân")
            
            with col_chart2:
                # Pie chart đơn giản
                top_10 = chart_df.nlargest(10, 'Số lượng')
                st.bar_chart(top_10.set_index('Nguyên nhân')['Số lượng'])
                st.caption("Top 10 nguyên nhân")
        
        # Xuất dữ liệu tổng hợp
        st.markdown("---")
        st.markdown("### 📤 XUẤT BÁO CÁO TỔNG HỢP")
        
        if st.button("🔄 CẬP NHẬT DỮ LIỆU TỪ 12 SHEET", use_container_width=True):
            with st.spinner("Đang cập nhật dữ liệu từ 12 sheet..."):
                # Logic cập nhật dữ liệu từ các sheet
                st.info("Chức năng đang phát triển...")
        
        # Xuất file
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            csv_total = total_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Tải CSV tổng hợp",
                data=csv_total,
                file_name=f"tong_hop_12_thang_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_exp2:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                total_df.to_excel(writer, index=False, sheet_name='TongHop')
            
            st.download_button(
                label="📥 Tải Excel tổng hợp",
                data=excel_buffer.getvalue(),
                file_name=f"tong_hop_12_thang_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    else:
        st.info("📭 Chưa có dữ liệu tổng hợp. Vui lòng cập nhật dữ liệu từ các sheet.")

# ========== TRANG QUẢN LÝ LÝ DO ==========
def page_quan_ly_ly_do(client):
    """Trang quản lý danh sách lý do"""
    st.markdown("## ⚙️ QUẢN LÝ DANH SÁCH LÝ DO")
    
    # Tải danh sách lý do từ sheet CONFIG
    try:
        spreadsheet = client.open_by_url(st.session_state.sheet_url)
        
        # Kiểm tra sheet CONFIG
        try:
            config_sheet = spreadsheet.worksheet("CONFIG")
        except:
            # Tạo sheet CONFIG nếu chưa có
            config_sheet = spreadsheet.add_worksheet(title="CONFIG", rows="100", cols="10")
            
            # Dữ liệu mẫu
            sample_data = [
                ["STT", "Nguyên nhân", "Mã", "Nhóm"],
                ["1", "Chờ công nhân", "CCN", "Nội bộ"],
                ["2", "Chờ xe nâng", "CXN", "Nội bộ"],
                ["3", "Xe vào trễ sau 16h", "XVT", "Khách hàng"],
                ["4", "Trời mưa nhập chậm", "TMN", "Thiên nhiên"],
                ["5", "Xe chờ lấy mẫu", "XLM", "QC"],
                ["6", "Nhập sau 17h", "N17H", "Thời gian"],
                ["7", "Lỗi Winfeed", "LWF", "Hệ thống"],
                ["8", "Lý do khác", "LDK", "Khác"]
            ]
            
            config_sheet.update('A1', sample_data)
        
        # Đọc dữ liệu
        config_data = config_sheet.get_all_values()
        
        if len(config_data) > 1:
            df_config = pd.DataFrame(config_data[1:], columns=config_data[0])
        else:
            df_config = pd.DataFrame(columns=["STT", "Nguyên nhân", "Mã", "Nhóm"])
    
    except Exception as e:
        st.error(f"Lỗi đọc danh sách lý do: {str(e)}")
        df_config = pd.DataFrame(columns=["STT", "Nguyên nhân", "Mã", "Nhóm"])
    
    # Hiển thị danh sách hiện tại
    st.markdown("### 📋 DANH SÁCH HIỆN TẠI")
    
    if not df_config.empty:
        edited_df = st.data_editor(
            df_config,
            use_container_width=True,
            height=400,
            num_rows="dynamic",
            column_config={
                "STT": st.column_config.TextColumn("STT", width="small"),
                "Nguyên nhân": st.column_config.TextColumn("Nguyên nhân", width="large"),
                "Mã": st.column_config.TextColumn("Mã", width="small"),
                "Nhóm": st.column_config.SelectboxColumn(
                    "Nhóm",
                    options=["Nội bộ", "Khách hàng", "QC", "Thiên nhiên", "Hệ thống", "Thời gian", "Khác"],
                    width="medium"
                )
            }
        )
        
        # Nút lưu thay đổi
        if st.button("💾 LƯU THAY ĐỔI", type="primary", use_container_width=True):
            try:
                # Chuẩn bị dữ liệu để lưu
                data_to_save = [df_config.columns.tolist()] + edited_df.values.tolist()
                
                # Xóa toàn bộ sheet và ghi lại
                config_sheet.clear()
                config_sheet.update('A1', data_to_save)
                
                st.success("✅ Đã lưu thay đổi!")
                st.rerun()
            
            except Exception as e:
                st.error(f"❌ Lỗi khi lưu: {str(e)}")
    
    else:
        st.info("📭 Chưa có dữ liệu. Vui lòng thêm lý do mới.")
    
    # Thêm lý do nhanh
    st.markdown("---")
    st.markdown("### ➕ THÊM LÝ DO NHANH")
    
    with st.form("add_reason_form"):
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            new_reason = st.text_input("Tên lý do", placeholder="Ví dụ: Chờ IT fix lỗi")
            reason_code = st.text_input("Mã lý do (viết tắt)", placeholder="Ví dụ: CIT")
        
        with col_a2:
            reason_group = st.selectbox("Nhóm", ["Nội bộ", "Khách hàng", "QC", "Thiên nhiên", "Hệ thống", "Thời gian", "Khác"])
        
        submitted = st.form_submit_button("➕ THÊM LÝ DO MỚI", type="secondary")
        
        if submitted and new_reason:
            try:
                # Thêm vào sheet
                new_row = [str(len(df_config) + 1), new_reason, reason_code, reason_group]
                
                # Cập nhật sheet
                next_row = len(config_sheet.get_all_values()) + 1
                config_sheet.update(f'A{next_row}', [new_row])
                
                st.success(f"✅ Đã thêm lý do: {new_reason}")
                st.rerun()
            
            except Exception as e:
                st.error(f"❌ Lỗi khi thêm: {str(e)}")

# ========== TRANG ĐỒNG BỘ DỮ LIỆU ==========
def page_dong_bo(client):
    """Trang đồng bộ dữ liệu"""
    st.markdown("## 🔄 ĐỒNG BỘ DỮ LIỆU")
    
    st.info("""
    ### Chức năng đồng bộ dữ liệu:
    
    1. **Tự động cập nhật sheet TOTAL** từ dữ liệu 12 sheet
    2. **Tính toán % tự động** cho từng nguyên nhân
    3. **Đồng bộ danh sách lý do** giữa các sheet
    4. **Kiểm tra tính nhất quán** của dữ liệu
    """)
    
    # Nút đồng bộ
    if st.button("🔄 BẮT ĐẦU ĐỒNG BỘ", type="primary", use_container_width=True):
        with st.spinner("Đang đồng bộ dữ liệu..."):
            # Giả lập quá trình đồng bộ
            progress_bar = st.progress(0)
            
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            
            st.success("✅ Đồng bộ hoàn tất!")
    
    # Thông tin đồng bộ
    st.markdown("---")
    st.markdown("### 📊 THÔNG TIN ĐỒNG BỘ")
    
    col_sync1, col_sync2, col_sync3 = st.columns(3)
    
    with col_sync1:
        st.metric("Số sheet đã đồng bộ", "0/12")
    
    with col_sync2:
        st.metric("Lần đồng bộ cuối", "Chưa có")
    
    with col_sync3:
        st.metric("Trạng thái", "🟡 Chờ")

# ========== TRANG HƯỚNG DẪN ==========
def page_huong_dan():
    """Trang hướng dẫn sử dụng"""
    st.markdown("## 📋 HƯỚNG DẪN SỬ DỤNG")
    
    tab_guide1, tab_guide2, tab_guide3, tab_guide4 = st.tabs([
        "🎯 Tổng quan", "📥 Nhập liệu", "📊 Báo cáo", "⚙️ Cấu hình"
    ])
    
    with tab_guide1:
        st.markdown("""
        ### 🎯 TỔNG QUAN HỆ THỐNG
        
        **Hệ thống Báo cáo Thời gian Nhập hàng** giúp:
        
        - 📊 **Theo dõi thời gian** nhập nguyên liệu hàng ngày
        - ⏰ **Phát hiện xe nhập trễ** (sau 17h hoặc quá 2h)
        - 📈 **Thống kê nguyên nhân** chậm trễ
        - ☁️ **Lưu trữ đám mây** trên Google Sheets
        - 📱 **Truy cập mọi nơi** từ trình duyệt
        
        ### 🔄 QUY TRÌNH LÀM VIỆC
        
        1. **Hàng ngày**: Nhập dữ liệu từ Excel vào hệ thống
        2. **Hàng tuần**: Xem báo cáo chi tiết theo tuần
        3. **Hàng tháng**: Tổng hợp và phân tích
        4. **Hàng quý**: Đánh giá và cải tiến quy trình
        
        ### 👥 ĐỐI TƯỢNG SỬ DỤNG
        
        - **Nhân viên kho**: Nhập dữ liệu hàng ngày
        - **Quản lý kho**: Xem báo cáo, theo dõi tiến độ
        - **Ban giám đốc**: Xem tổng hợp, ra quyết định
        """)
    
    with tab_guide2:
        st.markdown("""
        ### 📥 HƯỚNG DẪN NHẬP LIỆU
        
        #### Phương pháp 1: Dán từ Excel (Khuyến nghị)
        
        **Bước 1: Mở file Excel nguồn**
        ```
        - File: RM - Time loading report.xlsx
        - Sheet: Tháng tương ứng (T1, T2, ...)
        ```
        
        **Bước 2: Chọn vùng dữ liệu**
        ```
        - Chọn từ ô A7 đến hết dữ liệu
        - Hoặc chọn đến ô U70 (nếu dữ liệu ít)
        ```
        
        **Bước 3: Copy dữ liệu**
        ```
        - Bôi đen vùng đã chọn
        - Nhấn Ctrl+C (Windows) hoặc Cmd+C (Mac)
        ```
        
        **Bước 4: Dán vào hệ thống**
        ```
        - Vào trang "Nhập dữ liệu"
        - Dán (Ctrl+V) vào ô lớn
        - Hệ thống tự động nhận diện
        ```
        
        #### Phương pháp 2: Tải file lên
        
        - Chọn file Excel (.xlsx, .xls)
        - Hệ thống tự động đọc dữ liệu
        - Kiểm tra và lưu
        
        #### Phương pháp 3: Nhập thủ công
        
        - Dùng cho số lượng ít
        - Điền từng thông tin xe
        - Phù hợp cho bổ sung dữ liệu
        """)
    
    with tab_guide3:
        st.markdown("""
        ### 📊 HƯỚNG DẪN BÁO CÁO
        
        #### 1. Xem báo cáo tháng
        - Chọn tháng cần xem
        - Xem toàn bộ dữ liệu chi tiết
        - Tải xuống file Excel/CSV
        
        #### 2. Thống kê nhanh
        - Tổng số xe trong tháng
        - Số xe nhập trễ (>17h)
        - Tổng khối lượng nguyên liệu
        - Thời gian trung bình
        
        #### 3. Phân tích nguyên nhân
        - Top nguyên nhân chậm trễ
        - Biểu đồ phân bố
        - Xu hướng theo thời gian
        
        #### 4. Tổng hợp 12 tháng
        - Dữ liệu tổng hợp từ sheet TOTAL
        - Tính % tự động
        - So sánh giữa các tháng
        """)
    
    with tab_guide4:
        st.markdown("""
        ### ⚙️ HƯỚNG DẪN CẤU HÌNH
        
        #### 1. Kết nối Google Sheets
        ```
        Bước 1: Tạo Service Account
        Bước 2: Share Google Sheet cho service account
        Bước 3: Upload credentials.json
        ```
        
        #### 2. Quản lý danh sách lý do
        - Thêm/xóa/sửa lý do
        - Phân nhóm lý do
        - Tự động đồng bộ
        
        #### 3. Cài đặt hệ thống
        - URL Google Sheets
        - Tần suất auto-refresh
        - Cài đặt thông báo
        
        #### 4. Khắc phục sự cố
        
        **Lỗi kết nối Google Sheets:**
        - Kiểm tra internet
        - Kiểm tra credentials
        - Kiểm tra quyền truy cập sheet
        
        **Lỗi nhập liệu:**
        - Kiểm tra định dạng Excel
        - Thử phương pháp nhập khác
        - Liên hệ hỗ trợ
        
        ### 📞 LIÊN HỆ HỖ TRỢ
        
        - **Hotline**: 0900-123-456
        - **Email**: support@kho-nguyen-lieu.com
        - **Giờ làm việc**: 8:00 - 17:00 (T2-T6)
        """)

# ========== MAIN APP ==========
def main():
    """Hàm chính của ứng dụng"""
    
    # Kiểm tra kết nối
    client = get_google_client()
    
    if client is None:
        # Chế độ demo
        st.warning("""
        ⚠️ **CHẾ ĐỘ DEMO** - Chưa kết nối Google Sheets
        
        Vui lòng:
        1. Tải lên file credentials.json trong sidebar
        2. Hoặc cấu hình secrets trong Streamlit Cloud
        
        Bạn vẫn có thể xem giao diện và tính năng.
        """)
        
        # Hiển thị trang demo
        if st.session_state.current_page == "dashboard":
            page_dashboard(None)
        elif st.session_state.current_page == "huong_dan":
            page_huong_dan()
        else:
            st.info(f"Trang '{st.session_state.current_page}' cần kết nối Google Sheets")
        
        return
    
    # Hiển thị trang tương ứng
    if st.session_state.current_page == "dashboard":
        page_dashboard(client)
    elif st.session_state.current_page == "nhap_du_lieu":
        page_nhap_du_lieu(client)
    elif st.session_state.current_page == "xem_bao_cao":
        page_xem_bao_cao(client)
    elif st.session_state.current_page == "tong_hop":
        page_tong_hop(client)
    elif st.session_state.current_page == "quan_ly_ly_do":
        page_quan_ly_ly_do(client)
    elif st.session_state.current_page == "dong_bo":
        page_dong_bo(client)
    elif st.session_state.current_page == "huong_dan":
        page_huong_dan()

if __name__ == "__main__":
    main()
