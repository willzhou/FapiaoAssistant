# extractors/llm_extractor.py
import json
import re
from typing import Optional

from openai import OpenAI

import logging
from models import Invoice
from .base_extractor import BaseExtractor
from config import API_CONFIG, COMPANY_SUFFIXES

from urllib.parse import urljoin, urlparse


class LLMExtractor(BaseExtractor):
    def __init__(self, model_path: str, 
                 api_key: str = API_CONFIG["api_key"], base_url: str = API_CONFIG["base_url"],
                 suffixes: list = COMPANY_SUFFIXES):
        super().__init__(suffixes)
        self.logger = logging.getLogger(__name__)

        # 标准化URL（去除末尾斜杠）
        base_url = base_url.rstrip('/')
        
        # 检查是否已包含/v1
        parsed = urlparse(base_url)
        if not parsed.path.endswith('/v1'):
            base_url = urljoin(base_url + '/', 'v1')


        self.model_path = model_path
        self.client = OpenAI(
            api_key = api_key,
            base_url = base_url,
            timeout=60.0
        )

    def generate_prompt(self, text: str) -> str:
        prompt = f"""你现在是智能发票处理助手invoice_extractor。
            请你从“发票文本”中提取关键信息，并按以下JSON格式返回。
            # 样本 1
            invoice_sample1='''电子发票（普通发票）
            发票号码：25112000000130340249
            开票日期：2025年06月24日
            购 名称：北京星石娱动国际传媒有限公司 销 名称：北京那家雅居餐饮有限责任公司
            买 售
            方 方
            信 统一社会信用代码/纳税人识别号：91110116MA01BP9R44 信 统一社会信用代码/纳税人识别号：91110105562126449H
            息 息
            项目名称 规格型号 单 位 数 量 单 价 金 额 税率/征收率 税 额
            *餐饮服务*餐费 1652.8301886792453 652.83 6% 39.17
            合 计 ¥652.83 ¥39.17
            价税合计（大写） 陆佰玖拾贰圆整 （小写）¥692.00
            备
            注
            开票人：胡晋阳
            胡晋阳'''
            返回示例：{{
                "buyer": "北京星石娱动国际传媒有限公司",
                "seller": "北京那家雅居餐饮有限责任公司",
                "invoice_number": "25112000000130340249",
                "issue_date": "2025年06月24日",
                "project_name": "*餐饮服务*餐费",
                "amount": "652.83",
                "tax_rate": "6%",
                "tax_amount": "39.17",
                "total_with_tax_lowercase": "692.00",
                "issuer": "胡晋阳"
            }}
            # 样本 2
            invoce_sample2='''
            电子发票（普通发票）
            发票号码： 25327000000693696263
            旅客运输服务
            开票日期： 2025年06月23日
            购 销
            买 名称：北京星石娱动国际传媒有限公司 售 名称：苏州市吉利优行电子科技有限公司
            方 方
            信
            统一社会信用代码/纳税人识别号：91110116MA01BP9R44
            信
            统一社会信用代码/纳税人识别号：91320594MA1MFD7F31
            息 息
            项目名称 单 价 数 量 金 额 税率/征收率 税 额
            *运输服务*客运服务费 129.757282 1 129.76 3% 3.89
            *运输服务*客运服务费 -30.99 3% -0.93
            合 计 ¥98.77 ¥2.96
            出行人 有效身份证件号 出行日期 出发地 到达地 等 级 交通工具类型
            价税合计（大写） 壹佰零壹圆柒角叁分 （小写）¥101.73
            备
            注
            开票人：钟寒冰'''
            返回示例：{{
                "buyer": "北京星石娱动国际传媒有限公司",
                "seller": "苏州市吉利优行电子科技有限公司",
                "invoice_number": "25327000000693696263",
                "issue_date": "2025年06月23日",
                "project_name": "*运输服务*客运服务费",
                "amount": "98.77",
                "tax_rate": "3%",
                "tax_amount": "2.96",
                "total_with_tax_lowercase": "101.73",
                "issuer": "胡晋阳"
            }}
            # 发票文本：
            {text}"""
        
        prompt = f"""你现在是智能发票处理助手invoice_extractor。
            请你从“发票文本”中提取关键信息，并按以下JSON格式返回。
            # 样本 2
            invoce_sample2='''
            电子发票（普通发票）
            发票号码： 25327000000693696263
            旅客运输服务
            开票日期： 2025年06月23日
            购 销
            买 名称：北京星石娱动国际传媒有限公司 售 名称：苏州市吉利优行电子科技有限公司
            方 方
            信
            统一社会信用代码/纳税人识别号：91110116MA01BP9R44
            信
            统一社会信用代码/纳税人识别号：91320594MA1MFD7F31
            息 息
            项目名称 单 价 数 量 金 额 税率/征收率 税 额
            *运输服务*客运服务费 129.757282 1 129.76 3% 3.89
            *运输服务*客运服务费 -30.99 3% -0.93
            合 计 ¥98.77 ¥2.96
            出行人 有效身份证件号 出行日期 出发地 到达地 等 级 交通工具类型
            价税合计（大写） 壹佰零壹圆柒角叁分 （小写）¥101.73
            备
            注
            开票人：钟寒冰'''
            返回示例：{{
                "购方名称": "北京星石娱动国际传媒有限公司", 
                "销方名称": "苏州市吉利优行电子科技有限公司",
                "发票号码": "25327000000693696263", 
                "开票日期": "2025年06月23日", 
                "项目名称": "*运输服务*客运服务费",
                "金额": "98.77",
                "税率": "3%",
                "税额": "2.96",
                "价税合计": "101.73",
                "开票人": "胡晋阳"
            }}。
            # 发票文本：
            {text}"""

        return prompt
    
    def extract_with_llm(self, text: str) -> Optional[Invoice]:
        prompt = self.generate_prompt(text)
        try:
            # logging.error(f"llm extract2: {response}")
            response = self.client.chat.completions.create(
                model=self.model_path,
                messages=[
                    {"role": "system", "content": "你是智能发票处理助手。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            # logging.error(f"llm extract2: {response}")
            result = response.choices[0].message.content
            if json_match := re.search(r'\{.*\}', result, re.DOTALL):
                return json.loads(json_match.group())
        except Exception as e:
            self.logger.error(f"{__name__}.extract_with_llm 运行失败: {str(e)}")
            raise

        return None
    
    def extract(self, text: str) -> Invoice:
        result = self.extract_with_llm(text)
        # logging.error(f"llm extract: {llm_result}")
        try:
            if result:
                return Invoice(
                    file_name = "",
                    invoice_number=str(result.get("发票号码", "")).strip(),
                    issue_date=self.parse_date(result.get("开票日期")),
                    buyer=str(result.get("购方名称", "")).strip(),
                    seller=str(result.get("销方名称", "")).strip(),
                    item_name=str(result.get("项目名称")).strip(),
                    amount=self.to_float(result.get("金额")),
                    tax_amount=self.to_float(result.get("税额")),
                    total_amount=self.to_float(result.get("价税合计", )),
                    raw_text=json.dumps(result, ensure_ascii=False, indent=2),
                    error=None
                )
        except Exception as e:    
            self.logger.error(f"{__name__}.extract 运行失败: {str(e)}")
            raise

        return Invoice(file_name="", error="LLM提取失败")
    