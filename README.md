# FreeToken 推理引擎源码教材

📖 **[在线阅读完整教材 →](https://via-vie.github.io/Freetoken-textbook/)**

直接在浏览器中阅读，无需下载或安装 GPU 环境。也可以进入 **[第一章](https://via-vie.github.io/Freetoken-textbook/#ch01)**、**[实验与验收指南](https://via-vie.github.io/Freetoken-textbook/#ch20)** 或 **[源码阅读索引](https://via-vie.github.io/Freetoken-textbook/source.html)**。

离线阅读：下载整个目录后，在浏览器中打开本地 `index.html`，无需启动服务器或联网加载脚本。

面向第一次接触 FreeToken 源码的读者，从一条请求串起 MoE 数学、启动与模型加载、调度、专家缓存、CPU/GPU 混合执行、prefill 双缓冲、量化、CUDA Graph、KV 与递归状态、返回与取消、容量重建，以及扩展架构。

- 22 章连续讲解，每章标明输入、处理与输出，包含理解题与展开答案。
- 12 幅原创 SVG，可单独打开与放大。
- 8 个独立 CPU 教学实验与网页数据检查器。
- 固定提交源码卡、本地源码阅读器、精确函数范围与官方永久链接。
- 单 A100 的分阶段实验指南，以及实际 HTTP/SSE 采集客户端。

## 从这里开始

第一次阅读：第 1–8 章；理解 FreeToken 特点：第 9–16 章；补完整服务：第 17–19 章；动手和验收：第 20–22 章。

在本目录运行，不需要第三方包：

```powershell
python labs/run.py check
python labs/run.py moe
python labs/run.py cache
python labs/run.py hybrid
python labs/run.py prefill
python labs/run.py kv
python labs/run.py anchor
python labs/run.py request
python labs/run.py budget
```

CPU 实验是教学数学/控制模型，**没有执行真实 FreeToken**。带宽、容量与毫秒值为标注的假设，不是跑分。真实 A100 实验见网页第 20 章；当前未在用户服务器执行。

## 源码依据

官方项目：[FlashML-org/FreeToken](https://github.com/FlashML-org/FreeToken)。固定提交：`e4f69d9e232448fc168389c29f6f9364869cff35`。

`_source/FreeToken-e4f69d9/` 为选取的官方源码快照，不是可安装的完整克隆。采集范围与逐文件 Git blob、SHA256 记录在 `_research/source-manifest.json`。网页源码阅读器位于 `source.html`，只生成书中直接引用及必要文档的页面。外部依赖 flashlib 等未作为本书完整源码收录。

教学组织参考[白木原 MiniMind 第 1 章](https://tutorial.baimuyuan.online/minimind-tutorial/chapters/01-LLM%E5%85%A8%E6%99%AF%E4%B8%8E%E9%A1%B9%E7%9B%AE%E5%AF%BC%E8%A7%88)，本书正文、图解和实验独立编写。

## 维护

```powershell
python _tools/build_book.py
python _tools/verify_book.py
```

正文源文件：`_book/manuscript.txt`。网页样式和行为：`assets/`。图解生成：`_tools/diagrams.py`。构建使用 Python 标准库，所有实验 JSON 内嵌到页面，避免 `file://` 下 fetch 权限问题。

原始 FreeToken 源码保留上游 Apache-2.0 许可证与版权归属，见快照 `LICENSE` 与 `source/LICENSE.html`。本书新增文本、SVG、教学代码按本目录 `LICENSE` 的 Apache-2.0 许可提供；参考教程内容未复制入正文。`_research/reference-chapter01.html` 仅供本次研究，已从 Git 提交列表忽略。
