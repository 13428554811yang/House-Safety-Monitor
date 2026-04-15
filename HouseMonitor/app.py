import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.fft import fft, fftfreq

# --- 1. 页面基本设置 ---
st.set_page_config(page_title="房屋安全监测Demo", layout="wide", page_icon="🏗️")
st.title("🏗️ 房屋安全监测实时分析系统")
# --- 1.1 登录状态初始化 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 1.2 登录界面函数 ---
def login_screen():
    st.markdown("""
        <style>
        .login-box {
            background-color: #f0f2f6;
            padding: 2rem;
            border-radius: 10px;
            border: 1px solid #d1d5db;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.info("🔒 房屋安全监测系统 - 请先登录")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            
            # 这里设置你的账号密码
            if st.button("登录", use_container_width=True):
                if username == "admin" and password == "123456":
                    st.session_state.logged_in = True
                    st.rerun() # 登录成功立即刷新页面
                else:
                    st.error("用户名或密码错误")

# --- 1.3 权限逻辑判断 ---
if not st.session_state.logged_in:
    login_screen()
    st.stop() # 如果未登录，停止执行后面的所有代码

# --- 这里的下方就是你原本的代码逻辑 (st.title, 侧边栏等) ---
# st.sidebar.button("登出", on_click=lambda: st.session_state.update({"logged_in": False}))

# --- 隐藏 Streamlit 默认菜单和页脚 (让界面更像软件) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. 初始化全局状态 (文件仓库) ---
if 'file_db' not in st.session_state:
    st.session_state.file_db = {} 

if 'active_file' not in st.session_state:
    st.session_state.active_file = None

# --- 3. 定义数据处理函数 (带缓存) ---
@st.cache_data
def process_data(file_input):
    try:
        # 1. 倒带并读取
        file_input.seek(0)
        try:
            df = pd.read_csv(file_input, encoding='utf-8', sep=None, engine='python')
        except:
            file_input.seek(0)
            df = pd.read_csv(file_input, encoding='gbk', sep=None, engine='python')
            
        # 2. 清洗
        df.columns = [str(c).strip() for c in df.columns]
        
        # 3. 校验
        if len(df.columns) < 3:
            return None, None, "列数不足"

        # 4. 规范化
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

# --- 4. 侧边栏：文件管理区 ---
st.sidebar.header("📂 数据管理面板") # 恢复旧版文案

# [A] 文件上传区
uploaded_file = st.sidebar.file_uploader("上传新的监测数据 (CSV格式)", type=["csv", "txt"]) # 恢复旧版文案

# 逻辑：一旦有新文件上传，且它不在仓库里，就处理并存入仓库
if uploaded_file is not None:
    file_key = uploaded_file.name
    
    if file_key not in st.session_state.file_db:
        with st.spinner(f"正在分析 {file_key} ..."):
            df_new, sensors_new, status = process_data(uploaded_file)
            
            if status == "Success":
                st.session_state.file_db[file_key] = {
                    'df': df_new,
                    'sensors': sensors_new
                }
                st.session_state.active_file = file_key
                st.sidebar.success("✅ 已加载上传的文件") # 恢复旧版文案
            else:
                st.sidebar.error(f"导入失败: {status}")

# [B] 默认文件加载
if not st.session_state.file_db:
    try:
        with open("dynamic.csv", "rb") as f:
            class MockFile:
                def __init__(self, f): self.f = f; self.name = "dynamic.csv (默认)"
                def seek(self, p): self.f.seek(p)
                def read(self): return self.f.read()
                def __iter__(self): return self.f.__iter__()
            
            mock_f = MockFile(f)
            df_def, sensors_def, status = process_data(mock_f)
            if status == "Success":
                key = "默认演示数据"
                st.session_state.file_db[key] = {'df': df_def, 'sensors': sensors_def}
                st.session_state.active_file = key
                st.sidebar.info("ℹ️ 当前使用默认演示数据") # 恢复旧版文案
    except:
        pass 

# [C] 文件切换下拉框
all_files = list(st.session_state.file_db.keys())

if all_files:
    st.sidebar.markdown("---")
    index_val = 0
    if st.session_state.active_file in all_files:
        index_val = all_files.index(st.session_state.active_file)
        
    selected_file = st.sidebar.selectbox(
        "📑 选择要查看的数据源:", # 微调以适配多文件逻辑
        options=all_files,
        index=index_val
    )
    
    st.session_state.active_file = selected_file
    
    # [D] 从仓库取数据
    current_data = st.session_state.file_db[selected_file]
    df = current_data['df']
    sensor_list = current_data['sensors']
    
    # --- 绘图逻辑 (文字已完全恢复为您指定的旧版) ---
    st.sidebar.header("⚙️ 模拟参数设置") # 恢复旧版文案
    base_sensor = st.sidebar.selectbox("选择基准测点 (从文件中):", sensor_list) # 恢复旧版文案
    
    sensor_data = df[df['Name'] == base_sensor].sort_values('Time').drop_duplicates('Time')
    t_orig = (sensor_data['Time'] - sensor_data['Time'].iloc[0]).dt.total_seconds().values
    y_orig = sensor_data['Value'].values
    
    if len(t_orig) < 5:
        st.error("数据量太少，无法进行分析") # 恢复旧版文案
    else:
        # 重采样
        cs = CubicSpline(t_orig, y_orig)
        t_new = np.arange(0, 10, 0.005) # 10秒, 200Hz
        y_base = cs(t_new)
        
        sim_data = {
            "测点-1 (基准)": y_base,
            "测点-2 (微弱延迟)": np.roll(y_base, 10) + np.random.normal(0, 0.5, len(t_new)),
            "测点-3 (含环境噪)": y_base + np.random.normal(0, 2.0, len(t_new)),
            "测点-4 (结构漂移)": y_base + 5 * np.sin(t_new),
            "测点-5 (信号衰减)": y_base * 0.5
        }
        
        selected_curves = st.sidebar.multiselect(
            "图表显示测点:", # 恢复旧版文案
            options=list(sim_data.keys()),
            default=["测点-1 (基准)", "测点-2 (微弱延迟)"]
        )
        
        # 1. 时程图标题
        st.subheader("📈 实时加速度时程曲线 (200Hz)") # 恢复旧版文案
        
        chart_df = pd.DataFrame(sim_data, index=t_new)
        st.line_chart(chart_df[selected_curves])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 关键指标统计") # 恢复旧版文案
            
            target_key = selected_curves[0] if selected_curves else "测点-1 (基准)"
            val = sim_data[target_key]
            
            rms = np.sqrt(np.mean(val**2))
            peak = np.max(np.abs(val))
            
            # 恢复旧版详细 Metric 文案
            st.metric(label="当前采样频率", value="200 Hz")
            st.metric(label=f"{target_key} - 峰值加速度", value=f"{peak:.2f} mm/s²")
            st.metric(label=f"{target_key} - 均方根值 (RMS)", value=f"{rms:.2f}")
            
        with col2:
            st.subheader("🌊 频域分析 (FFT频谱)") # 恢复旧版文案
            
            N = len(t_new)
            T = 0.005
            yf = fft(sim_data["测点-1 (基准)"])
            xf = fftfreq(N, T)[:N//2]
            amp = 2.0/N * np.abs(yf[0:N//2])
            
            # 恢复旧版中文 DataFrame 列名
            fft_df = pd.DataFrame({'频率 (Hz)': xf, '振幅 (Amplitude)': amp})
            fft_df = fft_df[fft_df['频率 (Hz)'] < 50]
            
            st.line_chart(fft_df.set_index('频率 (Hz)'))
            
        # 恢复旧版底部说明
        st.info("💡 说明：系统已自动将上传的低频数据重采样至 200Hz 并完成频谱分析。")

else:
    st.warning("⚠️ 请上传 CSV 文件或将 dynamic.csv 放入文件夹") # 恢复旧版文案