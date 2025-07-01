import requests
import base64
import json
import logging
from typing import Dict, Optional, List, Tuple, Union
from io import BytesIO
from models import Invoice
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .base_extractor import BaseExtractor

import magic
from pdf2image import convert_from_bytes
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
import pdfplumber
from config import API_CONFIG, logger
from PIL import Image

import fitz  # pip install pymupdf


class VLMExtractor(BaseExtractor):
    SUPPORTED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/tiff'
    }

    def __init__(self, 
                 model_path: str = "qwen2.5vl:3b",
                 api_key: str = API_CONFIG["api_key"],
                 base_url: str = API_CONFIG["base_url"],
                 max_pages: int = 3):
        """
        初始化VLMExtractor
        
        Args:
            model_path: 模型路径 (default: "qwen2.5vl:3b")
            api_key: API密钥
            base_url: API基础地址
            max_pages: 处理PDF时的最大页数 (default: 3)
        """
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path
        self.model_name = model_path
        self.ollama_url = base_url
        self.api_key = api_key
        self.max_pages = max_pages

    def _generate_invoice_prompt(self) -> str:
        """生成发票提取的提示词"""
        
        prompt = """你是专业的发票信息提取助手。请你从以下发票文本或上传的文档图片中，提取以下信息，并按 JSON 格式返回。
                注意返回数据确保：金额98.77+税额2.96 == 税价合计(小写)101.73。
                返回示例：{
                    "购方名称": "北京星石娱动国际传媒有限公司", 
                    "销方名称": "苏州市吉利优行电子科技有限公司",
                    "发票号码": "25327000000693696263", 
                    "开票日期": "2025年06月23日", 
                    "项目名称": "*运输服务*客运服务费",
                    "金额": "98.77",
                    "税率": "3%",
                    "税额": "2.96",
                    "价税合计(小写)": "101.73",
                    "开票人": "胡晋阳"
                }。
                """

        return prompt

    def _process_uploaded_file(self, uploaded_file: UploadedFile) -> Tuple[List[bytes], str]:
        """
        处理上传文件，返回处理后的数据列表和内容类型
        
        Args:
            uploaded_file: 上传的文件对象
            
        Returns:
            Tuple[List[bytes], str]: (处理后的数据列表, 内容类型)
            
        Raises:
            ValueError: 文件类型不支持或处理失败
        """
        try:
            uploaded_file.seek(0)
            file_data = uploaded_file.read()
            content_type = getattr(uploaded_file, 'type', None) or magic.from_buffer(file_data[:1024], mime=True)
            
            if content_type not in self.SUPPORTED_MIME_TYPES:
                raise ValueError(f"不支持的文件类型: {content_type}")
            
            # PDF处理
            if content_type == 'application/pdf':
                return self._handle_pdf_conversion(file_data)
            
            # 图片处理（JPEG/PNG/TIFF）
            elif content_type.startswith('image/'):
                return self._handle_image_file(file_data, content_type)
        
        except Exception as e:
            self.logger.error(f"PDF处理失败: {str(e)}", exc_info=True)
            raise ValueError(f"文件处理失败: {str(e)}")
        
    def _handle_image_file(self, image_data: bytes, content_type: str) -> Tuple[List[bytes], str]:
        """
        处理图片文件
        
        Args:
            image_data: 图片二进制数据
            content_type: 图片MIME类型
            
        Returns:
            Tuple[List[bytes], str]: (图片数据列表, 内容类型)
        """
        try:
            # 验证图片有效性
            Image.open(BytesIO(image_data)).verify()
            return [image_data], content_type
        except Exception as e:
            raise ValueError(f"无效的图片文件: {str(e)}")
    
    def _handle_pdf_conversion(self, pdf_data: bytes) -> Tuple[List[bytes], str]:
        """处理PDF转换的专用方法"""
        # 尝试三种处理方式，按优先级降序
        try:
            # 方式1：转换为图片 (高质量)
            images = self._convert_pdf_to_images(pdf_data)
            # logger.error("以图片格式返回")
            return images, 'image/png'
            
        except PDFSyntaxError as e:
            self.logger.warning(f"PDF语法错误，尝试修复: {str(e)}")
            try:
                # 方式2：尝试修复PDF后转换
                fixed_pdf = self._repair_pdf(pdf_data)
                images = self._convert_pdf_to_images(fixed_pdf)
                return images, 'image/png'
            except Exception:
                # 方式3：降级为文本提取
                return self._extract_pdf_text(pdf_data), 'text/plain'
            
    def _convert_pdf_to_images(self, pdf_data: bytes) -> List[bytes]:
        """安全的PDF转图片实现"""
        def pdf_to_images(pdf_bytes, dpi=300):
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            images = []
            for page in doc:
                pix = page.get_pixmap(dpi=dpi, colorspace="rgb")
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            return [self._image_to_bytes(img) for img in images]
        
        try:
            return pdf_to_images(pdf_data)
        except Exception as e:
            pass

        try:
            images = convert_from_bytes(
                pdf_data,
                dpi=200,  # 平衡质量和性能
                first_page=1,
                last_page=min(3, self.max_pages),
                fmt='png',
                thread_count=2,  # 避免OOM
                poppler_path="/usr/bin"  # 显式指定路径
            )
            return [self._image_to_bytes(img) for img in images]
            
        except (PDFInfoNotInstalledError, PDFPageCountError) as e:
            raise ValueError("请安装poppler-utils: sudo apt install poppler-utils") from e
        except PDFSyntaxError as e:
            raise ValueError("PDF文件损坏或加密") from e
        except MemoryError:
            raise ValueError("内存不足，请减少处理页数") from e
        
    def _repair_pdf(self, pdf_data: bytes) -> bytes:
        """尝试修复损坏的PDF"""
        try:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(BytesIO(pdf_data))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            output = BytesIO()
            writer.write(output)
            return output.getvalue()
        except Exception as e:
            self.logger.warning(f"PDF修复失败: {str(e)}")
            raise ValueError("无法修复PDF文件") from e
        
    def _extract_pdf_text(self, pdf_data: bytes) -> List[str]:
        """降级文本提取"""
        try:
            with pdfplumber.open(BytesIO(pdf_data)) as pdf:
                return [
                    page.extract_text() 
                    for page in pdf.pages[:self.max_pages] 
                    if page.extract_text()
                ]
        except Exception as e:
            raise ValueError(f"文本提取失败: {str(e)}") from e
        
    def _image_to_bytes(self, image) -> bytes:
        """将PIL图像转换为字节"""
        with BytesIO() as buffer:
            image.save(buffer, format='PNG', optimize=True)
            return buffer.getvalue()

    def _call_vlm_api(self, inputs: List[Union[str, bytes]], prompt: str) -> Optional[Union[Dict, str]]:
        """
        调用VLM API处理数据
        
        Args:
            inputs: 输入数据列表（文本或图像字节）
            prompt: 处理提示词
            
        Returns:
            Union[Dict, str, None]: 解析后的结果
        """
        # 准备请求数据
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        # 添加认证头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 处理不同类型输入
        if isinstance(inputs[0], str):
            data["prompt"] = f"{prompt}\n\n请处理下面的输入文本：\n#输入文本:\n{inputs[0]}。\n\n输出：{{result}}"
        else:
            data["images"] = [
                base64.b64encode(img) # .decode('utf-8') 
                for img in inputs
            ]
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                headers=headers,
                json=data,
                timeout=60
            )
            # response.raise_for_status()
            
            result = response.json()
            if not result.get("response"):
                self.logger.error(f"API返回异常: {result}")
                return None
                
            return self._parse_api_response(result["response"])
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API请求失败: {str(e)}")
            return None

    def _parse_api_response(self, response: str) -> Union[Dict, str]:
        """解析API返回的响应"""
        try:
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:-3].strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            return response  # 返回原始响应

    def extract(self, uploaded_file: UploadedFile) -> Invoice:
        """
        从上传文件中提取发票信息
        
        Args:
            uploaded_file: 上传的文件对象
            
        Returns:
            Invoice: 提取的发票信息对象
        """
        file_name = getattr(uploaded_file, 'name', '未知文件')
        
        try:
            # 1. 处理文件
            processed_data, content_type = self._process_uploaded_file(uploaded_file)
            
            # 2. 准备API调用
            prompt = self._generate_invoice_prompt()
            
            # 3. 调用API
            result = self._call_vlm_api(processed_data, prompt)
            if not result:
                return Invoice(file_name=file_name, error="API处理失败")
            
            # 4. 转换为Invoice对象
            invoice =  self._create_invoice_from_result(file_name, result)
            return invoice
            
        except ValueError as e:
            return Invoice(file_name=file_name, error=str(e))
        except Exception as e:
            self.logger.error(f"提取过程失败: {str(e)}", exc_info=True)
            return Invoice(file_name=file_name, error=f"处理失败: {str(e)}")

    def _create_invoice_from_result(self, file_name: str, result: Union[Dict, str]) -> Invoice:
        """
        创建标准化Invoice对象
        
        Args:
            file_name: 文件名
            result: API返回结果
            
        Returns:
            Invoice: 标准化发票对象
        """
        # 如果是字符串响应，尝试解析
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                return Invoice(file_name=file_name, error="无法解析API响应")
        
        final_invoice =  Invoice(
            file_name=file_name,
            invoice_number=str(result.get("发票号码", "")).strip(),
            issue_date=self.parse_date(result.get("开票日期")),
            buyer=str(result.get("购方名称", "")).strip(),
            seller=str(result.get("销方名称", "")).strip(),
            item_name=str(result.get("项目名称")).strip(),
            amount=self.to_float(result.get("金额")),
            tax_amount=self.to_float(result.get("税额")),
            total_amount=self.to_float(result.get("价税合计(小写)", )),
            raw_text=json.dumps(result, ensure_ascii=False, indent=2),
            error=None
        )

        return final_invoice
