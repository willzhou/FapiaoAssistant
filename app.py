import streamlit as st
from typing import Optional, Union
from config import MODEL_OPTIONS, COMPANY_SUFFIXES, API_CONFIG
from extractors import RegexExtractor, LLMExtractor, VLMExtractor
from utils.file_utils import process_pdf_files, process_image_files
from utils.display_utils import show_results, chat_interface
from models import Invoice
from config import logger

def init_extractor() -> Union[RegexExtractor, LLMExtractor, VLMExtractor]:
    """根据用户选择初始化提取器"""
    # 模式选择
    extraction_mode = st.sidebar.radio(
        "提取模式",
        options=["正则匹配", "语言大模型(LLM)", "视觉多模态模型(VLM)"],
        index=1,
        help="选择信息提取方式"
    )
    
    # 正则模式
    if extraction_mode == "正则匹配":
        return RegexExtractor(COMPANY_SUFFIXES)
    
    # 获取模型配置
    model_type = "visual" if extraction_mode == "视觉多模态模型(VLM)" else "text"
    selected_model = st.sidebar.selectbox(
        label=f"选择{'视觉多模态' if model_type=='visual' else '语言'}模型",
        options=[k for k, v in MODEL_OPTIONS.items() if v["type"] == model_type],
        index=0
    )
    model_config = MODEL_OPTIONS[selected_model]
    
    # LLM模式
    if extraction_mode == "语言大模型(LLM)":
        return LLMExtractor(
            suffixes=COMPANY_SUFFIXES,
            model_path=model_config["model_path"],
            api_key=API_CONFIG["api_key"],
            base_url=API_CONFIG["base_url"]
        )
    
    # 多模态模式
    return VLMExtractor(
        model_path=model_config["model_path"],
        api_key=API_CONFIG["api_key"],
        base_url=API_CONFIG["base_url"]
    )

def main():
    st.set_page_config(page_title="Fapiao Assistant", layout="wide")
    st.title("Fapiao Assistant")
    st.subheader("多模式智能发票信息批量提取系统")
    
    # 初始化关键会话状态
    if "app_initialized" not in st.session_state:
        st.session_state.update({
            "app_initialized": True,
            "invoices": [],
            "current_extractor": None,
            "current_model": None
        })
    
    # 侧边栏配置
    st.sidebar.header("⚙️ 处理设置")
    extractor = init_extractor()
    st.session_state.current_extractor = extractor
    
    # 获取当前模型配置（用于聊天）
    model_type = "text" if isinstance(extractor, VLMExtractor) else "visual"
    selected_model = next(
        k for k, v in MODEL_OPTIONS.items() 
        if v["type"] == model_type
    )
    st.session_state.current_model = MODEL_OPTIONS[selected_model]["model_path"]
    
    # 文件上传区域
    st.header("📤 上传文件")
    file_types = ["pdf", "png", "jpg"] if isinstance(extractor, VLMExtractor) else ["pdf"]

    uploaded_files = st.file_uploader(
        "选择发票文件",
        type=file_types,
        accept_multiple_files=True,
        help=f"支持格式: {', '.join(file_types)}"
    )
    
    # 处理按钮
    invoices = []
    if uploaded_files and st.button("开始提取"):
        with st.spinner("正在提取发票信息..."):
            try:
                # 根据文件类型选择处理器

                if isinstance(extractor, VLMExtractor):
                    for uploaded_file in uploaded_files:
                        invoice = extractor.extract(uploaded_file)
                        invoices.append(invoice)
                else:
                    process_func = process_pdf_files if uploaded_files[0].type == "application/pdf" else process_image_files
                    invoices = process_func(uploaded_files, extractor)
                    
                # 存储结果到会话状态
                st.session_state.invoices = invoices
                if any(invoice.error for invoice in invoices if hasattr(invoice, 'error')):
                    st.error("部分发票处理出错，请检查结果")
                else:
                    st.success(f"成功处理 {len(invoices)} 份发票!")
            except Exception as e:
                st.error(f"处理失败: {str(e)}")
                st.session_state.invoices = []

    # 结果显示
    if st.session_state.get("invoices"):
        st.divider()
        st.header("📊 提取结果")
        show_results(st.session_state.invoices)     
    
        st.divider()
        try:
            chat_interface(
                model_path=st.session_state.current_model,  # 使用统一模型配置
                invoices=st.session_state.invoices
            )
        except Exception as e:
            st.error(f"对话界面初始化失败: {str(e)}")
            logger.exception("对话界面错误详情:")

    # 在侧边栏添加关于信息
    st.sidebar.markdown("---")
    with st.sidebar.expander("ℹ️ 关于本系统"):
        st.markdown("""
        <style>
            .small-text {
                font-size: 0.9em !important;
                line-height: 1.3 !important;
            }
        </style>
        <div class="small-text">
            开发作者：<br>
            Will Zhou<br><br>
            遵循协议：<br>
            MIT license<br><br>
            系统版本：<br> 
            v0.1<br><br>
            <a href="https://github.com/willzhou/FapiaoAssistant">查看源码</a>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
