# 风电法规监测系统 V7.3 —— V7.1 + V7.2 + V7.3 整合完整版

**这是一份完整 GitHub 网站项目，不是补丁。** 三轮国内政策抓取修复已经合并在此项目中，上传时不必逐一安装 V7.1、V7.2、V7.3。

## 包含的功能

- V7.1：第一批国内专站定向解析，及北极星风力发电网的政策线索机制。
- V7.2：17个其余国内来源的专用列表/日期/嵌入页面解析，修复抓取后 Git 提交冲突处理。
- V7.3：对旧日志中35个连接失败来源建立逐站补查配置；其中一个山西来源属于上轮已处理项，其余34个配置了自动尝试的官方备用目录。
- 原有国外21个适配器、国外来源配置、网站 HTML/CSS/JavaScript 保持不变。
- 含 `.github/workflows/update.yml`、依赖文件、测试、诊断数据、网站静态资源和随版本打包的 `site/data/` 数据快照。

## 最重要的提醒：不要意外覆盖新政策数据

**本压缩包包含 `site/data/`，是打包时的历史快照，不保证等于你现在 GitHub 仓库的最新数据。**

- **新建空仓库：** 解压后复制最外层项目文件夹内的所有文件和目录（包括隐藏 `.github`），用 GitHub Desktop 提交、Push。
- **更新已经运行的仓库：** 先在 GitHub Desktop 本地仓库备份当前 `site/data/` 文件夹。复制整合包中的项目文件，再用备份的 `site/data/` 恢复覆盖本地同名目录，以保留最新政策、游标与抓取状态。核对 GitHub Desktop 的文件差异后再提交。
- 不要删除 GitHub Desktop 创建的隐藏 `.git/` 文件夹；不要把整合包的顶层目录再嵌套到仓库根目录。
- GitHub 网页不适合一次性上传大量文件且容易遗漏隐藏目录，建议通过 GitHub Desktop 操作。

## 安装后的检查

1. 仓库根目录应直接看到 `policy_scrape.py`、`requirements.txt`、`policy_sources.json`、`site/`、`adapters/` 和隐藏的 `.github/`。
2. 打开 GitHub 仓库的 **Actions**，选择现有工作流 `Wind policy & industry monitor — collect and deploy`。
3. 手动运行时先选 `provincial`，观察国内政策及北极星抓取。
4. 完整运行结束后下载 `wind-policy-backend-diagnostics`，检查 `diagnostics/network35_runtime_report.csv`、`site/data/policy_site_acceptance.csv` 等逐站结果。
5. 网站部署继续按原 Pages 设置进行；不要另建相同的并行工作流。

## 测试与验收范围

- 本次重新执行 `python -m unittest discover -s tests -p 'test_policy_*.py' -q`：116项测试通过。
- 本次重新执行两套 Node 前端测试：全部通过。
- V7 原前端6个文件与本版逐字节相同；21个海外站点适配器与 V7 基线逐字节相同。
- **离线测试通过不代表全部国内网站在线抓取成功。** 特别是连接失败的官网，备用目录可能仍受 GitHub 网络限制。请以安装后真实运行报告为准。

## 其他说明

需要查看细节，可读项目内：
`README_V7_1_DOMESTIC_TARGETED.md`、`README_V7_2_DOMESTIC_REMAINING_CN.md`、
`README_V7_3_NETWORK35.md`、`diagnostics/network35_source_actions.csv`。

本整合版没有另改国外抓取规则、网站前端布局或功能。
