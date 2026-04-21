import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.fft import fft, fftfreq

# --- 1. 页面基本设置 ---
st.set_page_config(page_title="房屋安全监测Demo", layout="wide", page_icon="🏗️")

# --- 1.1 登录状态管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    st.markdown("""
        <style>
        .login-container { max-width: 400px; margin: auto; padding: 2rem; background: #f9f9f9; border-radius: 10px; border: 1px solid #ddd; }
        </style>
    """, unsafe_allow_html=True)
    with st.container():
        st.info("🔒 房屋安全监测系统 - 请先登录")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            if st.button("登录", use_container_width=True):
                # 这里可以修改你的账号密码
                if username == "admin" and password == "123456":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("用户名或密码错误")

# 权限拦截
if not st.session_state.logged_in:
    login_screen()
    st.stop()

# --- 2. 界面显示与隐藏设置 ---
st.title("🏗️ 房屋安全监测实时分析系统")

# hide_st_style = """
#             <style>
#             #MainMenu {visibility: hidden;}
#             footer {visibility: hidden;}
#             header {visibility: hidden;}
#             </style>
#             """
# st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. 初始化全局状态 (文件仓库) ---
if 'file_db' not in st.session_state:
    st.session_state.file_db = {} 

if 'active_file' not in st.session_state:
    st.session_state.active_file = None

# --- 4. 定义数据处理函数 (带缓存) ---
@st.cache_data
def process_data(file_input):
    try:
        file_input.seek(0)
        try:
            df = pd.read_csv(file_input, encoding='utf-8', sep=None, engine='python')
        except:
            file_input.seek(0)
            df = pd.read_csv(file_input, encoding='gbk', sep=None, engine='python')
        
        df.columns = [str(c).strip() for c in df.columns]
        if len(df.columns) < 3:
            return None, None, "列数不足"

        raw_columns = df.columns
        df.rename(columns={
            raw_columns[0]: 'Name', 
            raw_columns[1]: 'Time', 
            raw_columns[2]: 'Value'
        }, inplace=True)
        
        df['Time'] = pd.to_datetime(df['Time'])
        unique_sensors = df['Name'].unique()
        return df, unique_sensors, "Success"
    except Exception as e:
        return None, None, str(e)

# --- 5. 侧边栏：管理面板 ---
st.sidebar.header("📂 数据管理面板")

# [A] 文件上传
uploaded_file = st.sidebar.file_uploader("上传新的监测数据 (CSV格式)", type=["csv", "txt"])
if uploaded_file is not None:
    file_key = uploaded_file.name
    if file_key not in st.session_state.file_db:
        with st.spinner(f"正在分析 {file_key} ..."):
            df_new, sensors_new, status = process_data(uploaded_file)
            if status == "Success":
                st.session_state.file_db[file_key] = {'df': df_new, 'sensors': sensors_new}
                st.session_state.active_file = file_key
                st.sidebar.success("✅ 已加载新文件")

# [B] 默认文件加载 (dynamic.csv)
if not st.session_state.file_db:
    try:
        with open("dynamic.csv", "rb") as f:
            # 模拟文件对象
            class MockFile:
                def __init__(self, f): self.f = f; self.name = "dynamic.csv"
                def seek(self, p): self.f.seek(p)
                def read(self): return self.f.read()
                def __iter__(self): return self.f.__iter__()
            df_def, sensors_def, status = process_data(MockFile(f))
            if status == "Success":
                key = "默认演示数据"
                st.session_state.file_db[key] = {'df': df_def, 'sensors': sensors_def}
                st.session_state.active_file = key
    except:
        pass

# [C] 核心分析与绘图
all_files = list(st.session_state.file_db.keys())
if all_files:
    # 切换文件
    idx = all_files.index(st.session_state.active_file) if st.session_state.active_file in all_files else 0
    selected_file = st.sidebar.selectbox("📑 选择查看的数据源:", options=all_files, index=idx)
    st.session_state.active_file = selected_file
    
    current_data = st.session_state.file_db[selected_file]
    df, sensor_list = current_data['df'], current_data['sensors']

    st.sidebar.markdown("---")
    base_sensor = st.sidebar.selectbox("选择基准测点 (从文件中):", sensor_list)
    
    # 提取并重采样数据
    sensor_data = df[df['Name'] == base_sensor].sort_values('Time').drop_duplicates('Time')
    t_orig = (sensor_data['Time'] - sensor_data['Time'].iloc[0]).dt.total_seconds().values
    y_orig = sensor_data['Value'].values

    if len(t_orig) < 5:
        st.error("数据点不足，无法进行重采样分析")
    else:
        # 三次样条插值 (200Hz)
        cs = CubicSpline(t_orig, y_orig)
        t_new = np.arange(0, 10, 0.005) 
        y_base = cs(t_new)
        
        # 模拟多通道数据
        sim_data = {
            "测点-1 (基准)": y_base,
            "测点-2 (延迟)": np.roll(y_base, 10) + np.random.normal(0, 0.5, len(t_new)),
            "测点-3 (含噪)": y_base + np.random.normal(0, 2.0, len(t_new)),
            "测点-4 (漂移)": y_base + 5 * np.sin(t_new)
        }
        
        selected_curves = st.sidebar.multiselect("图表显示测点:", options=list(sim_data.keys()), default=["测点-1 (基准)"])
        
        # --- 时程图 (标注单位) ---
        st.subheader("📈 实时加速度时程曲线 (200Hz)")
        chart_df = pd.DataFrame(sim_data, index=t_new)
        st.line_chart(chart_df[selected_curves], x_label="时间 (s)", y_label="加速度 (mm/s²)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 关键指标统计")
            target = selected_curves[0] if selected_curves else "测点-1 (基准)"
            val = sim_data[target]
            st.metric("当前采样频率", "200 Hz")
            st.metric(f"{target} - 峰值", f"{np.max(np.abs(val)):.2f} mm/s²")
            st.metric(f"{target} - RMS值", f"{np.sqrt(np.mean(val**2)):.2f}")
            
        with col2:
            st.subheader("🌊 频域分析 (FFT频谱)")
            N, T = len(t_new), 0.005
            yf = fft(sim_data["测点-1 (基准)"])
            xf = fftfreq(N, T)[:N//2]
            amp = 2.0/N * np.abs(yf[0:N//2])
            fft_df = pd.DataFrame({'频率 (Hz)': xf, '振幅': amp})
            fft_df = fft_df[fft_df['频率 (Hz)'] < 50]
            # --- 频谱图 (标注单位) ---
            st.line_chart(fft_df.set_index('频率 (Hz)'), x_label="频率 (Hz)", y_label="振幅 (Amplitude)")

    if st.sidebar.button("🚪 退出登录"):
        st.session_state.logged_in = False
        st.rerun()
else:
    st.warning("⚠️ 待处理：请上传 CSV 文件")