import json
from typing import Union, List, Dict
import openai
from openai import OpenAI
from config import API_CONFIG, logger
from models import Invoice

from urllib.parse import urljoin, urlparse

def preprocess_invoice_data(invoice_data: Union[Invoice, List[Invoice], Dict]) -> str:
    """将发票数据预处理为LLM可理解的文本"""
    if isinstance(invoice_data, Invoice):
        return invoice_data.to_json()
    elif isinstance(invoice_data, list):
        return "\n\n".join([inv.to_json() if isinstance(inv, Invoice) else str(inv) 
                          for inv in invoice_data])
    elif isinstance(invoice_data, dict):
        return json.dumps(invoice_data, indent=2, ensure_ascii=False)
    else:
        raise ValueError(f"不支持的发票数据类型:{invoice_data}, {str(type(invoice_data))}")

def ask_llm(
    model_path: str,
    user_query: str,
    invoice_data: Union[Invoice, List[Invoice]],
    temperature: float = 0.3
    ) -> str:
    """
    向LLM发送查询并获取回复
    
    参数:
        model_path: 模型标识 (如 "gpt-4-turbo")
        user_query: 用户问题
        invoice_data: 单张或多张发票数据
        temperature: 生成温度
    
    返回:
        LLM生成的回复文本
    """

    api_key=API_CONFIG["api_key"]
    base_url=API_CONFIG["base_url"]

    # 标准化URL（去除末尾斜杠）
    base_url = base_url.rstrip('/')
    # 检查是否已包含/v1
    parsed = urlparse(base_url)
    if not parsed.path.endswith('/v1'):
        base_url = urljoin(base_url + '/', 'v1')

    try:
        # 初始化客户端
        client = OpenAI(
            api_key = api_key,
            base_url = base_url
        )
        
        # 准备系统提示词
        system_prompt = """你是财务助理。"""
        
        # 预处理发票数据
        context_data = preprocess_invoice_data(invoice_data)
        
        # 构建消息历史
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"发票数据：\n{context_data}"},
            {"role": "user", "content": user_query}
        ]
        
        # 调用API
        response = client.chat.completions.create(
            model=model_path,
            messages=messages,
            temperature=temperature,
            stream=False
        )
        
        # 返回生成的回复
        return response.choices[0].message.content
        
    except openai.APIError as e:
        logger.error(f"API调用失败: {str(e)}")
        return f"查询失败：{e.message}"
    except Exception as e:
        logger.error(f"LLM处理异常: {str(e)}")
        return "系统处理问题时出错，请稍后再试"

