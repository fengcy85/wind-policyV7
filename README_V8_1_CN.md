# 风电政策监测 V8.1｜国内逐站修复与“发现即展示”版本

## 本次修复依据

来自用户上传的 GitHub Actions 日志 `logs_106259942717.zip`，其中本轮执行 118 个国内来源：

- 13 个报告发现政策、38 个成功读目录但没有近期结果；
- 12 个使用旧版 `partial_coverage` 代码、1 个 `needs_adapter`；
- 33 个 `connection_error`、16 个 `blocked`、5 个 `timeout`。

**这些是旧运行结果，不能被解释为本次新代码已经真实抓通。** 本次仍需下一次 GitHub Actions 实际运行验收。

## 一、关于您的本地“梯子”

GitHub Actions 托管运行器是在 GitHub 管理的远端云环境执行，通常不使用您 Mac 电脑的网络出口。除非显式配置了代理、私有网络或自托管运行器，您 Mac 上的 VPN 开关不会造成 GitHub 执行器返回 403 / 412 或 `Network is unreachable`。

`blocked` 只说明访问被拒绝，实际需看原始 HTTP 状态码；`connection_error` 可能涉及 DNS、TLS、TCP 路由等，修改 CSS 规则不能修复网络层错误。

## 二、已修改内容

1. **取消国内目录时间覆盖强制判定**：有带发布日期、政策标题及可追溯链接的记录即可进入候选详情抓取。仍保留分页/日期风险报告，但不因整月分页没有证明而屏蔽成功结果。对国外保持原有独立游标和覆盖规则。
2. **修复已经抓到但未显示的问题**：放宽对“新能源机制电价、绿电、并网运行、电力辅助服务”等正式政策的识别；无“风电”字样、但可能适用风电的官方文件会显示“风电适用性待核对”。无关煤矿行政处罚、展会、招聘及日常新闻仍排除。
3. **仅有官方目录线索也可展示**：允许来源可信、标题与发布日期明确、URL有效的政策目录条目进入前端；正文不完整时在列表中标明“正文待补充”，不可冒充已核实全文。北极星风力发电网仍作为媒体线索，不冒充官方法规。已识别到防护验证页时，不把 WAF 脚本当作政策摘录。
4. **对已公开核实的目录实现来源专用规则**：国家发展改革委“通知”公开目录 `https://www.ndrc.gov.cn/xxgk/zcfb/tz/wap_index.html`；辽宁省政府“辽政发 / 辽政办发”按独立发布日期（不是成文日期）取数；国家能源局浙江监管办公室“通知公告” `https://zjb.nea.gov.cn/dtyw/tzgg/`，支持正式文件文章路径和行日期。必须再次声明：目录及样本在公开网页检索中能够核对，但本环境不能替代 GitHub 真实抓取。
5. **为访问受限来源补充已确认的官方公开渠道**：天津市发改委、天津市工信局发生故障时尝试 `https://www.tj.gov.cn/zwgk/szfwj/`；内蒙古政府、发改委对应来源发生故障时尝试 `https://nyj.nmg.gov.cn/tzgg/`。其他部门网站的文件只作为补查，不能虚报原发布机关站点已经恢复连接或覆盖完整。
6. **逐条展示审计**：自动生成 `site/data/policy_display_decisions.csv`，列明每条历史政策为何被显示或排除；自动生成 `diagnostics/source_failure_diagnosis.csv`，根据本次运行原始HTTP/DNS/TLS/超时/解析状态逐站报告故障与下一步。
7. **修正界面误导性状态文字**：来源状态“已核实发现候选”改为“已发现政策或线索”，历史 `partial_coverage` 改为“日期/分页待补查”，原先误将尚未实测来源计入失败源的状态也已调整。原网页结构、页面布局、排序和筛选功能没有变动。

## 三、完整项目直接上传（推荐创建新仓库）

- 解压 ZIP，打开 `wind-policy-monitor-V8.1` 文件夹，把**里面的全部内容**复制到 GitHub Desktop 新仓库根目录，确保 `.github/workflows/update.yml` 位于仓库根目录对应位置。不要把整个解压目录套进项目根目录。
- Commit to main → Push origin；GitHub 仓库 Settings → Pages → Source 选 GitHub Actions。
- Actions 页面使用自带工作流，首次运行选择 `provincial`（仅国内及北极星）。确认整个运行结束后，在 `wind-policy-backend-diagnostics` 工件中下载 `source_failure_diagnosis.csv`，以及前端构建阶段保存在 `site/data/policy_display_decisions.csv` 的每条入库报告。
- 最新政策保存于 GitHub 仓库里的 `site/data/`，无需让 Mac 常年开机。

### 更新已有仓库时必须先保留数据

完整包中附带的 `site/data/` 是历史数据快照。**如果覆盖一个已经运行的仓库，先备份现有 `site/data/`，上传代码后恢复您仓库内更新的政策数据和游标**，否则会失去后续抓到的新记录。

## 四、边界和下一步

- 146 项 Python 离线测试和两套 Node 前端测试通过，确认规则行为正确；不是 118 站均已在 GitHub 真实抓通。
- GitHub 网络 `Network is unreachable` 的政务网站，仍可能因执行节点跨境访问受到阻碍。这次不会宣称更换 CSS 就能解决。
- 33 个连接错误、16 个拒绝访问、5 个超时应以**新的** `source_failure_diagnosis.csv` 为证据，逐站找到能在 GitHub 网络出口访问的正式文件库；如果官方跨站渠道同样不可达，才考虑用 Mac 做**一次性网络对照诊断**（不是必须双机抓取）。
- 12 个旧 `partial_coverage` 不再作为强制覆盖失败，但如果某站确实没有解析出标题、发布日期或政策详情，仍如实归为专站规则未完成。
- 仍然无法获取正文的媒体线索或官方目录条目，不应宣传成已核验、现行有效的正式法规。

## 需要打开的诊断文件

- `diagnostics/V81_previous_118_site_actions.csv`：最新日志逐站基线、是否修改和后续注意事项。
- `diagnostics/V81_previous_run_summary.json`：最新旧日志汇总。
- `site/data/policy_display_decisions.csv`：为何一条已经抓到的政策能否进入网站列表。
- `diagnostics/source_failure_diagnosis.csv`：新一轮 GitHub 执行后每站真实网络/解析错误。

**请以新一轮 GitHub 真实成功抓取到的政策、发布日期及链接验收，而非仅以 Actions 绿色、源码测试通过或 `verified` 布尔值验收。**
