# models/invoice.py
from typing import Dict, Optional
from dataclasses import dataclass
import json

@dataclass
class Invoice:
    file_name: str
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = None
    buyer: Optional[str] = None
    seller: Optional[str] = None
    item_name: Optional[str] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    raw_text: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "文件名": self.file_name,
            "发票号码": self.invoice_number or "未提取",
            "开票日期": self.issue_date or "未提取",
            "购方名称": self.buyer or "未提取",
            "销方名称": self.seller or "未提取",
            "项目名称": self.item_name or "未提取",
            "金额": self.amount or "未提取",
            "税额": self.tax_amount or "未提取",
            "价税合计": self.total_amount or "未提取",
            "原始文本": self.raw_text or "",
            "错误信息": self.error or ""
        }
    
    def to_json(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """生成JSON字符串
        
        参数:
            indent: 缩进空格数
            ensure_ascii: 是否转义非ASCII字符
            
        返回:
            格式化的JSON字符串
        """
        return json.dumps(
            {
                "文件名": self.file_name,
                "发票号码": self.invoice_number,
                "开票日期": self.issue_date,
                "购方名称": self.buyer,
                "销方名称": self.seller,
                "项目名称": self.item_name,
                "金额": self.amount,
                "税额": self.tax_amount,
                "价税合计": self.total_amount,
                "错误信息": self.error,
                # 原始文本过大时不完整输出
                "原始文本": len(self.raw_text) if self.raw_text else 0
            },
            indent=indent,
            ensure_ascii=ensure_ascii,
            default=str  # 处理datetime等不可序列化对象
        )
