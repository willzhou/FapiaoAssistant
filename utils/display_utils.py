# utils/display_utils.py
import streamlit as st
import pandas as pd
from io import BytesIO
from typing import List, Union
from models import Invoice
from .llm_utils import ask_llm
from config import logger
from typing import Union, List, Dict

def show_results(invoices: Union[Invoice, List[Invoice], Dict]):
    """显示发票处理结果（包含错误处理和两种视图模式）"""
    st.markdown("### 发票信息提取结果")
    
    # 错误文件处理
    error_files = [inv for inv in invoices if hasattr(inv, 'error') and inv.error]
    if error_files:
        st.warning(f"{len(error_files)}个文件处理失败")
        for inv in error_files:
            with st.expander(f"❌ 错误文件: {getattr(inv, 'file_name', '未知文件')}", expanded=False):
                st.error(f"错误类型: {getattr(inv, 'error', '未知错误')}")
                if hasattr(inv, 'raw_text'):
                    st.text_area("原始文本", inv.raw_text, height=100, key=f"error_{id(inv)}")
    
    # 成功文件处理
    success_files = [inv for inv in invoices if not (hasattr(inv, 'error') and inv.error)]
    if not success_files:
        st.info("没有成功处理的发票文件")
        return

    # 视图模式选择
    display_mode = st.radio("显示模式", ["表格视图", "详细视图"], horizontal=True, key="view_mode")
    
    try:
        if display_mode == "表格视图":
            # 表格视图处理
            df = pd.DataFrame([{
                '文件名称': getattr(inv, 'file_name', ''),
                '发票号码': getattr(inv, 'invoice_number', '未提取'),
                '开票日期': getattr(inv, 'issue_date', '未提取'),
                '购方名称': getattr(inv, 'buyer', '未提取'),
                '销方名称': getattr(inv, 'seller', '未提取'),
                '项目名称': getattr(inv, 'item_name', '未提取'),
                '金额': getattr(inv, 'amount', '未提取'),
                '税额': getattr(inv, 'tax_amount', '未提取'),
                '价税合计': getattr(inv, 'total_amount', '未提取')
            } for inv in success_files])
            
            st.dataframe(df, use_container_width=True)

            # Excel导出功能
            if st.button("导出为Excel", key="export_excel"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='发票信息')
                st.download_button(
                    label="下载Excel文件",
                    data=output.getvalue(),
                    file_name="发票信息.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel"
                )

            # # Excel导出功能 + 打印组合
            # if st.button("导出为Excel", key="export_excel"):
            #     output = BytesIO()
            #     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            #         df.to_excel(writer, index=False, sheet_name='发票信息')

            #     # 创建并排按钮列
            #     col1, col2 = st.columns(2)
                
            #     with col1:
            #         # 下载Excel按钮（原功能保留）
            #         st.download_button(
            #             label="📥 下载Excel",
            #             data=output.getvalue(),
            #             file_name="发票信息.xlsx",
            #             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            #             key="download_excel"
            #         )
                
            #     with col2:
            #         if st.button("🖨️ 打印预览", key="print_excel_data"):
            #             # 方法1：改进的打印方案（解决窗口拦截问题）
            #             print_html = f"""
            #             <!DOCTYPE html>
            #             <html>
            #             <head>
            #                 <title>发票信息打印</title>
            #                 <style>
            #                     body {{ font-family: 'SimSun', Arial; margin: 20px; }}
            #                     h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            #                     table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            #                     th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            #                     th {{ background-color: #f2f2f2; }}
            #                     @media print {{
            #                         .no-print {{ display: none; }}
            #                         body {{ zoom: 90%; }}
            #                     }}
            #                 </style>
            #             </head>
            #             <body>
            #                 <h1>发票信息 <span class="no-print">(打印时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')})</span></h1>
            #                 {df.to_html(index=False, border=0, classes="print-table")}
            #                 <div class="no-print" style="margin-top: 30px;">
            #                     <button onclick="window.print()" style="padding: 8px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">🖨️ 立即打印</button>
            #                     <button onclick="window.close()" style="padding: 8px 15px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: 10px;">❌ 关闭窗口</button>
            #                 </div>
            #                 <script>
            #                     // 自动聚焦打印按钮
            #                     window.onload = function() {{
            #                         // 先尝试直接打印
            #                         setTimeout(function() {{ window.print(); }}, 300);
                                    
            #                         // 如果10秒后窗口仍存在，显示提示
            #                         setTimeout(function() {{
            #                             if (!document.hidden) {{
            #                                 alert("如果打印窗口未自动弹出，请检查浏览器设置或手动点击打印按钮");
            #                             }}
            #                         }}, 10000);
            #                     }};
            #                 </script>
            #             </body>
            #             </html>
            #             """
                        
            #             # 使用st.components.v1.iframe确保兼容性
            #             st.components.v1.iframe(
            #                 src="about:blank",
            #                 width=0,
            #                 height=0,
            #                 scrolling=False
            #             )
                        
            #             js = f"""
            #             <script>
            #             var printWin = window.open("", "_blank");
            #             printWin.document.open();
            #             printWin.document.write(`{print_html}`);
            #             printWin.document.close();
            #             </script>
            #             """
            #             st.components.v1.html(js, height=0)
                        
            #             # # 方法2：备用方案 - 当前页打印
            #             # st.warning("如果新窗口未弹出，请使用下方备用打印方案：")
            #             # if st.button("🖨️ 备用打印方案"):
            #             #     st.markdown(f"""
            #             #     <style>
            #             #     @media print {{
            #             #         .no-print, .stButton {{ display: none !important; }}
            #             #         body {{ zoom: 85%; font-family: 'SimSun' !important; }}
            #             #     }}
            #             #     </style>
            #             #     <h2 style="text-align:center">发票信息</h2>
            #             #     {df.to_html(index=False)}
            #             #     <script>window.print();</script>
            #             #     """, unsafe_allow_html=True)
        
        else:
            # 详细视图处理
            for idx, inv in enumerate(success_files, 1):
                with st.expander(f"📄 发票 #{idx}: {getattr(inv, 'file_name', '无名文件')}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("基本信息")
                        st.write(f"**发票号码**: {getattr(inv, 'invoice_number', '未提取')}")
                        st.write(f"**开票日期**: {getattr(inv, 'issue_date', '未提取')}")
                        st.write(f"**购方名称**: {getattr(inv, 'buyer', '未提取')}")
                        st.write(f"**销方名称**: {getattr(inv, 'seller', '未提取')}")
                    
                    with col2:
                        st.subheader("金额信息")
                        st.write(f"**项目名称**: {getattr(inv, 'item_name', '未提取')}")
                        st.write(f"**金额**: {getattr(inv, 'amount', '未提取')}")
                        st.write(f"**税额**: {getattr(inv, 'tax_amount', '未提取')}")
                        st.write(f"**价税合计**: {getattr(inv, 'total_amount', '未提取')}")
                    
                    if hasattr(inv, 'raw_text'):
                        st.text_area("原始文本", 
                                    inv.raw_text, 
                                    height=200, 
                                    key=f"rawtext_{idx}")
    
    except Exception as e:
        st.error(f"视图渲染错误: {str(e)}")
        st.exception(e)  # 显示完整错误堆栈


def chat_interface(model_path: str, invoices: Union[Invoice, List[Invoice], Dict]):
    """支持 /clear 命令的聊天界面（仅按钮/Ctrl+Enter发送）"""
    st.subheader("💬 发票信息查询助手")
    
    # 初始化 session_state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "input_area_key" not in st.session_state:
        st.session_state.input_area_key = 0
    
    # 主布局容器
    with st.container():
        # 聊天记录区域
        chat_container = st.empty()
        with chat_container.container():

            # 渲染历史消息
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # 紧凑布局样式
            st.markdown("""
                <style>
                    .chat-area {
                        max-height: calc(100vh - 210px);
                        overflow-y: auto;
                        margin-bottom: 0;
                        padding-bottom: 10px;
                    }
                    .input-footer {
                        position: fixed;
                        bottom: 0;
                        left: 0;
                        right: 0;
                        background: white;
                        padding: 0.5rem 1rem 1rem;
                        border-top: 1px solid #eee;
                        z-index: 100;
                    }
                    .stTextArea textarea {
                        min-height: 80px !important;
                    }
                    .command-hint {
                        color: #666;
                        font-size: 0.9em;
                        margin-top: 5px;
                    }
                </style>
                <div class="chat-area"></div>
            """, unsafe_allow_html=True)
        
        # 输入区域
        with st.container():
            st.markdown('<div class="input-footer">', unsafe_allow_html=True)
            
            # 输入框（带键盘事件控制）
            prompt = st.text_area(
                " ",
                height=80,
                key=f"input_area_{st.session_state.input_area_key}",
                label_visibility="collapsed",
                placeholder="输入关于发票的问题... (输入 /clear 清空历史)"
            )
            
            # 命令提示
            st.markdown('<div class="command-hint">支持命令: /clear | 发送方式: 发送按钮或Ctrl+Enter</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns([0.3, 0.7])
            with col1:
                clear_clicked = st.button("清空历史", key="clear_btn", use_container_width=True)
            with col2:
                send_clicked = st.button("发送", key="send_btn", use_container_width=True, type="primary")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 键盘事件处理JS（仅响应Ctrl+Enter）
            st.components.v1.html("""
            <script>
            document.addEventListener('DOMContentLoaded', () => {
                const textarea = document.querySelector('textarea[aria-label=" "]');
                if (textarea) {
                    textarea.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' && e.ctrlKey) {
                            e.preventDefault();
                            const sendBtn = document.querySelector('button[kind="primary"]');
                            if (sendBtn) sendBtn.click();
                        }
                    });
                }
            });
            </script>
            """, height=0)
            
            # 处理清空命令
            if clear_clicked or (prompt and prompt.strip() == "/clear"):
                st.session_state.chat_history = []
                st.session_state.input_area_key += 1
                st.rerun()
                return
            
            # 处理发送逻辑（仅通过按钮或Ctrl+Enter触发）
            if send_clicked:
                current_prompt = prompt.strip()
                if not current_prompt:
                    st.warning("请输入有效内容")
                    st.stop()
                
                # 添加用户消息
                st.session_state.chat_history.append({"role": "user", "content": current_prompt})
                
                # 获取LLM回复
                with st.spinner("正在思考..."):
                    try:
                        response = ask_llm(model_path, current_prompt, invoices)
                    except Exception as e:
                        response = f"处理出错: {str(e)}"
                
                # 添加助手回复
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                # 重置输入框
                st.session_state.input_area_key += 1
                st.rerun()