# regex_extractor.py
from typing import Optional, Tuple
import re
from .base_extractor import BaseExtractor
from models import Invoice

class RegexExtractor(BaseExtractor):
    def extract_invoice_number(self, text: str) -> Optional[str]:
        match = re.search(r'(?:发票号码[:：])*\s*(\d{20})', text)
        return match.group(1) if match else None
    
    def extract_issue_date(self, text: str) -> Optional[str]:
        match = re.search(r'(?:开票日期[:：])*\s*(\d{4}年\d{1,2}月\d{1,2}日)', text)
        return match.group(1) if match else None
    
    def extract_item_name(self, text: str) -> Optional[str]:
        match = re.search(r'(\*[\u4e00-\u9fa5]+\*+[\u4e00-\u9fa5]+)', text)
        return match.group(1).strip() if match else None
    
    def extract(self, text: str) -> Invoice:
        cleaned_text = self.clean_text(text)
        invoice = Invoice(file_name="")
        
        invoice.invoice_number = self.extract_invoice_number(cleaned_text)
        invoice.issue_date = self.extract_issue_date(cleaned_text)
        invoice.buyer, invoice.seller = self.extract_companies(cleaned_text)
        invoice.item_name = self.extract_item_name(cleaned_text)
        invoice.amount, invoice.tax_amount, invoice.total_amount = self.extract_amounts(cleaned_text)

        return invoice
