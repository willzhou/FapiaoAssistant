# utils/file_utils.py
import pdfplumber
from PIL import Image
from typing import List, Union
import pytesseract
import io
from models import Invoice
from streamlit.runtime.uploaded_file_manager import UploadedFile
from extractors import LLMExtractor, VLMExtractor
from config import logger

# 新增多模态处理函数
def extract_text_from_file(file) -> str:
    """支持PDF/图片的通用文本提取"""
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type.startswith("image/"):
        return extract_text_from_image(file)
    else:
        raise ValueError(f"不支持的格式: {file.type}")
    
def extract_text_from_pdf(file) -> str:
    with pdfplumber.open(file) as pdf:
        return "".join(page.extract_text() or "" for page in pdf.pages)

def extract_text_from_image(file) -> str:
    """图片OCR提取"""
    image = Image.open(io.BytesIO(file.read()))
    return pytesseract.image_to_string(image)

def extract_visual_features(file, vl_model) -> dict:
    """使用VL模型提取视觉特征"""
    if file.type == "application/pdf":
        images = convert_pdf_to_images(file)
    else:
        images = [Image.open(io.BytesIO(file.read()))]
    
    visual_features = []
    for img in images:
        features = vl_model.extract_visual_features(img)
        visual_features.append(features)
    return {"visual_features": visual_features}

def convert_pdf_to_images(file, dpi=200):
    """将PDF页面转为PIL图像列表"""
    import pdf2image
    return pdf2image.convert_from_bytes(
        file.read(),
        dpi=dpi,
        fmt="jpeg",
        thread_count=4
    )

def process_files(
    files: List[UploadedFile],
    extractor,
    vl_model=None,
    use_visual: bool = False
    ) -> List[Invoice]:
    """支持多模态的通用处理函数"""
    results = []
    for file in files:
        try:
            # 基础文本提取
            text = extract_text_from_file(file)
            
            # 视觉特征提取（可选）
            visual_data = None
            if use_visual and vl_model:
                visual_data = extract_visual_features(file, vl_model)
            
            # 调用提取器
            invoice = extractor.extract(
                text=text,
                visual_data=visual_data
            )
            
            invoice.file_name = file.name
            invoice.raw_text = text[:500] + "..." if len(text) > 500 else text
            results.append(invoice)
            
        except Exception as e:
            results.append(Invoice(file_name=file.name, error=str(e)))
    return results

def process_pdf_files(files, extractor) -> List[Invoice]:
    results = []
    for file in files:
        try:
            ftext = file if isinstance(extractor, VLMExtractor) else extract_text_from_pdf(file)
            invoice = extractor.extract(ftext)
            invoice.file_name = file.name
            invoice.raw_text = ftext[:500] + "..." if len(ftext) > 500 else ftext
            results.append(invoice)
        except Exception as e:
            results.append(Invoice(file_name=file.name, error=str(e)))
    return results

def process_image_files(
    files: List[UploadedFile],
    extractor,
    vl_model=None
    ) -> List[Invoice]:
    """处理上传的图片文件"""
    invoices = []
    for uploaded_file in files:
        try:
            if isinstance(extractor, LLMExtractor):
                image = Image.open(uploaded_file)
                if vl_model:
                    visual_data = vl_model.process_images([image])
                    invoice = extractor.extract_from_visual(visual_data)
                else:
                    # 备用：使用OCR提取文本
                    text = pytesseract.image_to_string(image, lang='chi_sim')
                    invoice = extractor.extract(text)
                    
                invoice.file_name = uploaded_file.name
                invoices.append(invoice)
            else:
                invoice = extractor.extract(uploaded_file)
                invoice.file_name = uploaded_file.name
                invoices.append(invoice)
        except Exception as e:
            logger.error(f"处理图片 {uploaded_file.name} 失败: {str(e)}")
            invoices.append(Invoice(file_name=uploaded_file.name, error=str(e)))
    return invoices


def encode_image(image_path: str) -> str:
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')