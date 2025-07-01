import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List

# 保持原有logger配置
logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """加载YAML配置文件"""
    config_path = Path(__file__).parent / "settings.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# 加载配置数据
_config = load_config()

# 保持原有变量名和结构
API_CONFIG = _config['api_config']
OLLAMA_MODEL_OPTIONS = _config['ollama_model_options']
VLLM_MODEL_OPTIONS = _config['vllm_model_options']
MODEL_OPTIONS = OLLAMA_MODEL_OPTIONS if _config['default_model'] == 'ollama' else VLLM_MODEL_OPTIONS
COMPANY_SUFFIXES = _config['company_suffixes']
DEFAULT_INVOICE_FIELDS = _config['default_invoice_fields']
SUPPORTED_FILE_TYPES = _config['supported_file_types']

def switch_to_vllm():
    """切换到VLLM模型（保持原有功能）"""
    global MODEL_OPTIONS
    MODEL_OPTIONS = VLLM_MODEL_OPTIONS
    logger.info("已切换到VLLM模型配置")

def switch_to_ollama():
    """切换回OLLAMA模型"""
    global MODEL_OPTIONS
    MODEL_OPTIONS = OLLAMA_MODEL_OPTIONS
    logger.info("已切换到OLLAMA模型配置")
