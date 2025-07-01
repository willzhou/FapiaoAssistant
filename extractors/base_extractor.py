# extractors/base_extractor.py
from typing import Dict, Optional, Tuple
import re
from models import Invoice
from config import logger
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Union

class BaseExtractor:
    def __init__(self, suffixes: list):
        self.suffixes = suffixes
    
    def clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    
    def extract_companies(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        suffixes = "|".join(self.suffixes)
        pattern = re.compile(r"""
            (?:(?:[购买销售]\s*)?名称\s*[:：]\s*)?
            ([^\s：:]+?(?:{})[^)\s]*)
            \s+
            (?:(?:[销售售]\s*)?名称\s*[:：]\s*)?
            ([^\s：:]+?(?:{})[^)\s]*)
        """.format(suffixes, suffixes), re.VERBOSE | re.DOTALL)
        
        match = pattern.search(text)
        return (match.group(1).strip(), match.group(2).strip()) if match else (None, None)
    
    def extract_amounts(self, text: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        cleaned = re.sub(r'[ \s\u3000]+', ' ', text.strip())

        amount, tax, total_amount = None, None, None

        ## SOME BUGS WITH SAMPLE:
        ## text = """合 计 ¥ 61.46 ¥ 1.84
        ## 出行人 有效身份证件号 出行日期 出发地 到达地 等级 交通工具类型
        ## 价税合计(大写) ⨂ 陆拾叁元叁角 (小写) ¥ 63.3"""

        # 提取金额、税额
        total_match1 = re.search(
            r'(?:合\s*计|价税合计).*?[^¥]*¥\s*(\d+\.\d{1,2}).*?[^¥]*¥\s*(\d+\.\d{1,2})',
            cleaned
        )
        # 提取税价合计
        total_match2 = re.search(
            r"价税合计\s*\(?[大小]写\)?[^¥]*¥\s*(\d+\.\d{1,2})",
            cleaned
        ) or re.search(
            r"价税合计[^\d]*[^¥]*¥\s*(\d+\.\d{1,2})", 
            cleaned
        )
        if total_match1:
            amount, tax = (float(total_match1.group(1)), float(total_match1.group(2)))

        if total_match2:
            total_amount = float(total_match2.group(1))
        
        if  amount and tax and total_amount:
            return amount, tax, total_amount
        
        # 模式2：处理明细行累加
        detail_lines = re.findall(
            r'(?:\*.*?\*)\s+[\d.-]+\s+\d+\s+([\d.-]+)\s+\d+%?\s+([\d.-]+)',
            cleaned
        )
        if detail_lines:
            amount = sum(float(line[0]) for line in detail_lines)
            tax = sum(float(line[1]) for line in detail_lines)
            return (round(amount, 2), round(tax, 2), total_amount)
        
        # 模式3：反向计算价税合计
        total = re.search(r'价税合计.*?¥\s*(\d+\.\d{2})', cleaned)
        if total:
            total_val = float(total.group(1))
            # 按照最常见税率计算（3%或6%）
            tax_rate = 0.03 if '3%' in cleaned else 0.06
            amount = round(total_val / (1 + tax_rate), 2)
            tax = round(total_val - amount, 2)
            return (amount, tax, total_amount)
        
        return amount, tax, total_amount
    
    def extract(self, text: str) -> Invoice:
        raise NotImplementedError

    def safe_extract(self, text: str) -> Invoice:
        try:
            return self.extract(text)
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return Invoice(error=str(e))
        

    # 日期处理
    def parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in ("%Y年%m月%d日", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return date_str

    def _chinese_amount_to_float(self, amount_str: str) -> float:
        """
        将中文大写金额转换为浮点数
        
        Args:
            amount_str: 中文大写金额字符串（如"壹万贰仟叁佰肆拾伍元整"）
            
        Returns:
            float: 转换后的数字
            
        Raises:
            ValueError: 当输入格式无效时
        """
        # 1. 预处理字符串
        amount_str = amount_str.strip()
        if not amount_str:
            return 0.0
        
        # 2. 去除无关字符
        for char in ["元", "整", "人民币", "¥", "RMB"]:
            amount_str = amount_str.replace(char, "")
        
        # 3. 定义映射关系
        digit_map = {
            '零': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4,
            '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9
        }
        unit_map = {
            '分': 0.01, '角': 0.1,
            '拾': 10, '佰': 100, '仟': 1000,
            '万': 10000, '亿': 100000000
        }
        
        # 4. 分离整数和小数部分
        if "点" in amount_str:
            integer_part, decimal_part = amount_str.split("点")
        else:
            integer_part = amount_str
            decimal_part = ""
        
        # 5. 转换整数部分
        integer_value = 0.0
        temp_value = 0
        current_unit = 1
        
        for char in reversed(integer_part):
            if char in digit_map:
                temp_value += digit_map[char] * current_unit
            elif char in unit_map:
                if unit_map[char] > current_unit:
                    integer_value += temp_value
                    temp_value = 0
                    current_unit = unit_map[char]
                else:
                    current_unit = unit_map[char]
                    temp_value *= current_unit
        integer_value += temp_value
        
        # 6. 转换小数部分
        decimal_value = 0.0
        if decimal_part:
            for char in decimal_part:
                if char in digit_map:
                    decimal_value = decimal_value * 10 + digit_map[char]
            decimal_value /= 10 ** len(decimal_part)
        
        return integer_value + decimal_value

    def to_float(self, value: Union[str, int, float]) -> float:
        """
        增强型转换函数，支持多种输入格式
        
        Args:
            value: 输入值（可以是数字、字符串数字或中文大写金额）
            
        Returns:
            float: 转换后的数值
        """
        if isinstance(value, (int, float)):
            return float(value)
        
        if not isinstance(value, str):
            return 0.0
        
        # 尝试直接转换数字字符串
        try:
            return float(value)
        except ValueError:
            pass
        
        # 检查是否中文大写金额
        chinese_digits = {'零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖'}
        if any(char in value for char in chinese_digits):
            try:
                return self._chinese_amount_to_float(value)
            except (ValueError, KeyError):
                pass
        
        return 0.0  # 默认返回0.0而不是None
