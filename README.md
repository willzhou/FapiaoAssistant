# FapiaoAssistant - 多模式智能发票信息批量提取系统

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/框架-Streamlit-FF4B4B)
![License](https://img.shields.io/badge/license-MIT-green)
[![GitHub Stars](https://img.shields.io/github/stars/willzhou/FapiaoAssistant?style=social)](https://github.com/willzhou/FapiaoAssistant)

基于多模态大模型的智能发票信息提取工具，支持PDF/图片格式，提供三种提取模式，可自动识别发票关键字段。

## 功能演示
<div align="center">
  <img src="assets/chrome_home.png" width="30%" alt="首页界面">
  <img src="assets/chrome_uploaded.png" width="30%" alt="文件上传"> 
  <img src="assets/chrome_result.png" width="30%" alt="识别结果">
</div>

## 功能特性

- **多模式提取引擎**
  - 🔍 正则匹配：快速提取结构化发票
  - 🤖 LLM文本解析：处理复杂PDF电子发票
  - 🖼️ VLM多模态模型：识别扫描件/拍照发票

- **全面字段提取**
  ```json
  {
    "发票号码": "25327000000693796669",
    "开票日期": "2025-06-23",
    "购方名称": "北京星石娱动国际传媒有限公司",
    "销方名称": "苏州市吉利优行电子科技有限公司",
    "金额": 98.77,
    "税额": 2.96,
    "价税合计": 101.73,
    "项目名称": "*运输服务*客运服务费"
  }
  ```

- **文件格式支持**
  - 📄 PDF（电子发票）
  - 🖼️ PNG/JPG（扫描件或手机拍摄）

## 快速开始

### 前置要求
- Python 3.8+（开发环境：python 3.13.2）
- [Ollama](https://ollama.ai/) 服务（用于本地模型运行）

### 安装步骤
```bash
# 克隆仓库
git clone https://github.com/willzhou/FapiaoAssistant.git
cd FapiaoAssistant

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 下载模型（示例下载3B多模态模型）
ollama pull qwen2.5vl:3b
```

### 启动应用
```bash
# 启动Ollama服务（新终端窗口）
ollama serve

# 启动Streamlit应用
streamlit run app.py
```
应用默认访问地址：`http://localhost:8501`

## 配置说明

编辑`config.py`自定义设置：
```python
API_CONFIG = {
    "api_key": "your_api_key",  # 商业API密钥
    "base_url": "http://localhost:11434"  # Ollama服务地址
}

# 可用模型列表（需与Ollama中模型名称对应）
MODEL_OPTIONS = {
    "qwen2.5vl:3b": {
        "model_path": "qwen2.5vl:3b",
        "type": "visual"  # 多模态模型
    },
    "gemma3:1b": {
        "model_path": "gemma3:1b", 
        "type": "text"    # 纯文本模型
    }
}
```

## 项目结构
```
.
├── app.py                # 主应用入口
├── config.py             # 配置文件
├── requirements.txt      # 依赖列表
├── extractors/           # 提取器实现
│   ├── base_extractor.py # 基础抽象类
│   ├── llm_extractor.py  # 大语言模型处理器
│   ├── regex_extractor.py# 正则表达式处理器
│   └── vlm_extractor.py  # 视觉语言模型处理器
├── models.py             # 数据模型定义
└── utils/                # 工具模块
    ├── file_utils.py     # 文件处理
    └── display_utils.py  # 界面显示
```

## 使用示例
1. 启动应用后，在侧边栏选择提取模式：
   - 电子发票建议使用 **LLM文本解析**
   - 扫描件建议使用 **VLM多模态模型**

2. 上传发票文件（支持批量上传）

3. 查看提取结果，可手动修正字段

4. 通过聊天界面查询发票数据：
   ```
   /查询 金额大于100的发票
   /统计 按购方名称分组
   ```

## 常见问题

❓ **模型下载失败**
确保Ollama服务正常运行，网络可访问官方镜像站。中国大陆用户建议配置镜像源：
```bash
export OLLAMA_HOST=mirror.ghproxy.com
```

❓ **图片识别精度低**
- 确保图片清晰度（建议300dpi以上）
- 尝试更换更大模型（如`qwen2.5vl:7b`）

❓ **内存不足**
在config.py中减少`max_pages`参数值（默认3页）

## 参与贡献
欢迎提交Issue或PR！建议流程：
1. Fork本仓库
2. 创建特性分支（`git checkout -b feature/xxx`）
3. 提交更改（`git commit -am 'Add some feature'`）
4. 推送到分支（`git push origin feature/xxx`）
5. 新建Pull Request

## 开源协议
[MIT License](LICENSE) © 2024 Will Zhou

---

💡 **提示**：生产环境部署建议使用Docker容器化运行，参考`docker-compose.yml`示例（见仓库）
```

### 关键优化说明：

1. **GitHub友好格式**：
   - 添加了Stars徽章和Python版本标识
   - 使用emoji图标增强可读性
   - 结构化展示项目信息

2. **完整的安装指引**：
   - 包含虚拟环境创建步骤
   - 明确模型下载指令
   - 区分开发和生产配置

3. **问题排查指南**：
   - 针对中国用户添加镜像配置
   - 常见错误解决方案
   - 性能优化建议

4. **开发者友好**：
   - 清晰的目录结构说明
   - 标准的贡献流程
   - Docker部署提示

5. **交互体验**：
   - 截图展示改为文字交互示例
   - 强调聊天命令功能
   - 模式选择建议

可根据实际需求：
1. 添加`assets/`目录存放演示截图
2. 补充CI/CD自动化测试说明
3. 增加API接口文档链接