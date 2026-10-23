# V7.2：按 2026-10-18 旧日志定向处理尚未修复的国内来源

## 先看结论

本轮只针对 **用户提供的 `logs_105955481932.zip`（V7.1 修改前，wind-policyv4）** 工作流结果处理剩余国内来源，不重复改动 V7.1 已修好的贵州、上海、福建发改委、内蒙古能源局、山西能源局、江苏发改委及北极星专站规则。仍保留北极星风电政策栏目和已有补查能力。

这次是**新增 17 个来源 ID 的专用 HTML/文章地址/独立日期适配**，不是把 118 个国内来源宣称全部成功；GitHub 上真实 HTTP/覆盖结果尚待新一轮 Actions 验收。原来的 21 个海外适配器文件与前端页面不变。

| 旧日志范围 | 数量 |
|---|---:|
| 国内总来源 | 118 |
| 网络连接失败 `connection_error` | 35 |
| 日期与分页覆盖不完整 `partial_coverage` | 27 |
| HTTP/站点访问拒绝 `blocked` | 15 |
| 页面目录未识别 `needs_adapter` | 13 |
| 请求超时 `timeout` | 5 |
| 旧运行有结果 `ok_with_results` | 8 |
| 旧运行无近期政策 `ok_no_recent` | 15 |

本轮新增的 17 个专站适配针对上述 `needs_adapter` 中 9 个、`partial_coverage` 中 8 个。**35 个网络连接失败不应凭 CSS 修复声称已经恢复**；其余未处理项目也不应显示成功。

## 17 个剩余来源的定向规则

| 来源 | 旧状态 | 修改内容 |
|---|---|---|
| 吉林省发改委 | 覆盖不完整 | 识别官方公开目录的 `/zcbm/fgw/xxgkmlqy/YYYYMM/t...html`；分辨成文/发布日期 |
| 吉林省能源局 | 覆盖不完整 | 识别能源局 `/zwgk/tzgg/YYYYMM/t...html` 正式通知 |
| 辽宁省人民政府 | 覆盖不完整 | 政府文件真实 `index.shtml` 文章结构，发布日期取独立列 |
| 辽宁省政府办公厅 | 目录未识别 | 专用“辽政办发”路径与行发布日期 |
| 辽宁省发改委 | 覆盖不完整 | `/fgw/zc/zxzc/.../index.shtml` 专用路径 |
| 国家能源局浙江监管办 | 目录未识别 | 浙江监管官方网站可链接到 **国家能源局** `www.nea.gov.cn/YYYYMMDD/.../c.html` 的正式政策；允许已声明官方主机，拒绝其他主机 |
| 西藏自治区人民政府 | 目录未识别 | `/zwgk/zfxxgk/fdzdgknr/zc/xzgfxwj/YYYYMM/t...html` 正式规范性文件和行日期；静态分页仍需完整遍历 |
| 江苏省人民政府 | 目录未识别 | 省政府 `/art/YYYY/M/D/art_...html` 官方文件；仅该站启用浏览器读取同站 iframe 列表 |
| 江苏省工业和信息化厅 | 目录未识别 | 纠正错误名称“江苏省工信部”，工信厅 `/art/YYYY/M/D/art_...html`；同站 iframe 列表专项处理 |
| 广东省能源局 | 目录未识别 | `/gdsnyj/gkmlpt/content/.../post_...html` |
| 新疆自治区政府新政发 | 目录未识别 | `/xinjiang/c112543/YYYYMM/hex.shtml`；存在 JS 分页未遍历时不认证覆盖 |
| 新疆自治区政府新政办发 | 目录未识别 | `/xinjiang/c112545/YYYYMM/hex.shtml`；同上 |
| 山东省人民政府 | 目录未识别 | 识别带日期的政府正式文章 `/art/YYYY/M/D/art_...html` |
| 宁夏工信厅 | 覆盖不完整 | `/zwgk/fdzdgknr/zcfg/gxtwj/YYYYMM/t...html` |
| 宁夏发改委 | 覆盖不完整 | `/zcgh/fgwwj/YYYYMM/t...html`，日期与效力状态不混淆 |
| 西藏自治区发改委 | 覆盖不完整 | `/zwgk_1941/xzgfxwj/YYYYMM/t...html`，可解析 `26-10-08` 短日期 |
| 福建省工信厅 | 覆盖不完整 | 工信厅最新文件正文 `/zwgk/zfxxgk/fdzdgknr/gzdt/YYYYMM/t...htm`，缺出版日期/分页仍不得完成覆盖 |

**注意**：“真正的文章链接路径与列表日期可以从公开样本验证”不等于“本轮已从 GitHub Runner 抓取成功”；源站如返回 403、412、404 或无法建立连接，应以新一轮 HTTP 报告为准。

## 同时修复一个真实的发布故障

旧日志后段显示 `git commit` 已完成，但 `git pull --rebase origin main` 因仓库中其他未暂存修改失败，工作流以 exit code 128 结束；因此即使有部分政策被抓到，最后也可能无法提交并部署。

只把这一句改为 `git -c rebase.autoStash=true pull --rebase origin main`，保留其它 GitHub 工作流的抓取范围、定时和发布机制。该方式可暂时收起并恢复未暂存的跟踪文件修改；如果发生真正的合并冲突，仍会报错、应检查日志，不会偷偷抹掉数据。

## 安装方法：优先增量补丁

1. **等待当前 Actions 运行结束**，备份 GitHub 项目及 `site/data/` 政策历史数据。
2. 本补丁以 **已应用 V7.1 补丁的源码** 为基线。如当前仓库还是纯 V7，请先应用上一轮 V7.1 补丁再应用本补丁，或以本轮完整源码为参考逐项合并。
3. 将 `wind-policy-v7-2-domestic-remaining-PATCH.zip` 解压后的内容复制到仓库 **根目录**，替换同名文件；尤其不要漏掉 `.github/workflows/update.yml`。不要把项目再套一层文件夹。
4. GitHub Desktop 选择 Commit to main → Push origin。
5. 在 **Actions → Wind policy & industry monitor — collect and deploy → Run workflow** 中选择 `provincial`，等待 **全部步骤运行结束**（包括最终发布），再下载 `wind-policy-backend-diagnostics` 及查看 `site/data/`。
6. 对照 `diagnostics/baseline_20261018_domestic_118_by_source.csv`，逐条核对新版本的 `status`、抓到的政策标题/来源/发布日期、分页数量、HTTP 错误。**只有真实抓取并核验时间覆盖，才算修好**。

如果工作流还是 `Network is unreachable`，这表示 GitHub Runner 在获取 HTML 之前已经失败，解析规则尚无法执行。应优先核对官方入口和执行端网络，不应该盲目更改 `verified` 标志或者无限重试。在当前仓库不增加本地运行系统，也不修改国外爬虫。

## 工件/清单

- `diagnostics/baseline_20261018_domestic_118_by_source.csv`：118 来源旧状态、逐站诊断方向、V7.1 已处理/本轮新增/仍需现场核验。
- `diagnostics/baseline_20261018_summary_v72.json`：分组数量和明确的未实网验收标记。
- `policy_domestic_remaining.py`：17 个未修复国内站点的独立 URL/行日期解析，不触碰原先 7 个适配。
- `tests/test_policy_domestic_remaining_20261018.py`：回归测试包含两个日期列、iframe、跨官方主机、虚假文章链接、分页不完整、Git 提交等。

离线回归测试：**101 项 Python 测试与两套 Node 前端测试均通过**；中国大陆政务网站在 GitHub Actions 上的真实访问结果，必须以新的运行日志验证。
