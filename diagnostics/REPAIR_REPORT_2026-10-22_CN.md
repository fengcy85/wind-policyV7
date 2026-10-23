# 风电法规抓取修复与失败站点诊断（2026-10-22）

## 结论边界

本次上传的 GitHub Actions 日志在“离线后端/前端测试”阶段就因断言失败退出，因此 **2026-10-21 那次任务没有进入正式法规抓取步骤**。仓库内可用于分析失败站点的最近一次抓取状态是：

- `last_run`: `2026-10-19T09:51:25+00:00`
- 配置来源：139 个
- 本轮实际尝试：118 个（省级范围；海外 21 个为 `not_tested`，不是失败）
- `blocked`: 13
- `connection_error`: 33
- `timeout`: 4
- `needs_adapter`: 11
- `ok_no_recent`: 40
- `ok_with_results`: 17

因此下面的 61 个失败/待适配状态，是对 2026-10-19 状态快照的诊断，不应误认为 2026-10-21 的新抓取结果。

## 已直接修复

### 1. 离线测试被正式重试队列污染

`tests/test_policy_v6.py` 和 `tests/test_policy_v61.py` 的临时数据目录没有同时 patch `DETAIL_QUEUE`，导致测试读取正式的 `site/data/policy_detail_retry_queue.json`。

已将 `DETAIL_QUEUE` 一并指向临时目录，并把旧测试名中的 `138` 改为当前真实来源数 `139`。这不是把断言 139 改成 138，而是修正测试隔离。

### 2. 防止爬虫整体崩溃后仍部署旧数据

原 `update.yml` 对主法规抓取步骤使用 `continue-on-error: true`。这会掩盖整个 `policy_scrape.py` 进程级崩溃。

已取消该容错，并新增 `policy_run_guard.py`。Guard 检查：
- 本次 crawl 的 `last_run` 必须晚于本 job 的开始标记；
- `policy_sources.json` 与 `policy_source_status.json` 的来源集合一致；
- `configured_source_count` 与实际来源数一致；
- `attempted_source_count > 0`。

单站失败仍由爬虫内部记录并继续，不会因为某个站点 403/超时就拖垮全部来源。

### 3. `update.yml` 稳定性加固

已完成：
- GitHub 官方 actions 升级到当前 Node 24 代际版本；
- Python 依赖启用 pip cache；
- 周一至周六跑省级，周日只跑一次全量，去掉原来周日两次相隔约 14 分钟的重复 crawl；
- 长任务中间 checkpoint push 前执行 `pull --rebase`；
- Pages 部署拆成独立 `deploy` job，只有 update 成功后才部署；
- update job 只授予 `contents: write`，Pages 的 `pages/id-token` 权限只放在 deploy job。

### 4. 吉林省人民政府入口已修

旧入口 `https://xxgk.jl.gov.cn/szf/gkml/` 在历史运行中只解析出“公开指南/制度/年报”等导航项。

已切换到：
`https://www.jl.gov.cn/zcxx/zfwj/wap.html`

该公开页面存在真实政府文件标题和完整发布日期。已同步修改：
- `policy_sources.json`
- `site/data/policy_sources.json`
- `adapters/sites/cn_fcdd8a95a7df.py`
- 回归测试

## 失败站点的四类根因

### A. `blocked`：13 个

典型为天津、安徽、河南、湖北、云南、甘肃的部分政府站，返回 HTTP 403/412。

这通常不是 CSS selector 问题，而是执行网络/WAF 条件。正确做法不是模拟浏览器身份强行绕过，而是：
1. 保留原站被拒状态；
2. 寻找同机关官方公报、政府文件库等备用公开渠道；
3. 需要时用合规的中国区域/自托管 Runner 对同一官方 URL 做网络复核。

### B. `connection_error`：33 个

河北、山西、江西、山东、湖南、广西、海南、重庆、四川、陕西、青海等出现成片连接/DNS/TLS失败。多个同省不同机关同时失败，更符合 GitHub 海外 Runner 到目标网络的链路问题，而不是 33 套解析器同时损坏。

建议先用另一执行网络做 A/B；TLS 错误不要通过 `verify=False` 解决。

### C. `timeout`：4 个

浙江省政府及部分浙江发改/能源栏目、西藏经信厅。

建议针对单来源做有限的更长 timeout、降低同站并发，或换更轻量的官方列表入口；不建议把所有 118 个国内来源的全局超时大幅提高。

### D. `needs_adapter`：11 个

这类才是优先值得改解析器的：
- 国家标准全文公开：入口是导航，真正标准结果表有“标准号/名称/发布日期”；
- 辽宁省政府、辽宁省政府办公厅：官方页面明确存在“成文日期”和“发布日期”两列，当前历史运行却识别为 0 日期，说明行级字段关联仍需针对实际 DOM 固化；
- 吉林省政府：已修入口；
- 吉林发改：需换真实政策列表；
- 吉林能源：已有真实条目，但列表日期不足，应优先从详情页取明确发布日期；
- 山东工信：当前落在导航/清理栏目；
- 西藏政府：真实详情链接存在，但列表日期没绑定；
- 新疆政府：动态公开壳层，需稳定列表/检索结果；
- 中国能源报：媒体 selector 过宽；
- 风能产业网：真实文章多，但列表日期不足且 60 条详情重试过重，应只处理近期高相关候选并限制预算。

逐站明细见 `diagnostics/failure_remediation_20261022.csv`。

## 不建议采用的“修复”

为了法规监测数据可审计，本项目应继续避免：
- 伪造浏览器指纹去绕 403/412；
- 关闭 TLS 证书校验；
- 从 URL 中的数字直接当发布日期；
- 因备用来源成功就把原官方来源标记为“已验证成功”；
- 把主爬虫 `continue-on-error` 打开来隐藏进程崩溃。

## 验收

修复包本地回归目标：
- Python policy tests：158 个全部通过；
- 前端 policy test：通过；
- 前端 news test：通过。

上传 GitHub 后，第一轮真正需要观察的是 `Verify crawl produced fresh state` 通过，以及吉林省政府是否从 `needs_adapter` 转为 `ok_no_recent` / `ok_with_results`。网络/WAF类站点不会因为本次代码修复自动全部变绿；它们需要执行网络或官方备用入口方案。
