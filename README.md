# 题库答题助手

## 功能

- 🎯 **屏幕圈题**：鼠标框选屏幕上的题目文字
- 🔍 **离线OCR**：PaddleOCR 中文识别，完全断网运行
- 📚 **多源搜索**：同时搜索自定义题库 + C++ Primer + C++ Primer Plus
- ⚡ **模糊匹配**：OCR识别有错别字也能搜到

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行
```bash
python main.py
```

### 3. 使用
1. 点击「加载题库文件」加载你的 RAR/Excel 题库
2. 点击「更新教材题库」从 GitHub 下载 C++ 教材
3. 点击「开始圈题」（或按 Ctrl+Shift+Q）
4. 鼠标拖拽框选屏幕上的题目
5. 自动弹出答案

## 打包成 exe（U盘版）

```bash
# Windows
build.bat

# 手动
pyinstaller --name="AnswerTool" --onedir --noconsole main.py
```

打包后在 `dist/AnswerTool/` 目录，整个文件夹复制到U盘即可运行。

## 注意事项

- **首次运行需要联网**下载 PaddleOCR 模型（约100MB），之后完全离线
- RAR题库解压需要 `UnRAR.exe`，请放置到程序同目录
- 教材题库首次下载也需要联网，之后缓存在本地
