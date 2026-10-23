# 风电法规监测 V8｜国内滚动采集版（取消强制时间覆盖）

这份项目是**包含网站前端、139来源、国内外抓取程序、GitHub Actions和运行依赖的完整包**，不是补丁。它是在 V7.3 累积版基础上修改，仅改变国内数据源与抓取层的验收及必要配置。原有网站 HTML/CSS/JavaScript 和21个海外专站适配器保持字节一致。

## 一、按用户指定的五步修复

**1. 取消国内整月时间覆盖强制门槛**

- 国内来源固定从每天运行日期向前滚动30天抓取；可用环境变量 `POLICY_DOMESTIC_LOOKBACK_DAYS` 在7—120天内调整。
- 不再要求抓完每一页并证明时间边界才允许抓取详情或保存真实政策。**日期、分页缺陷仍记录为风险提示，不允许伪造“完全覆盖”。**
- 状态中区分 `listing_parse_ok`（真实目录是否读到）、`policy_records_found`（本轮发现政策/线索）、`full_text_records_found`（本轮取得正文证据）和 `listing_warnings`。
- 对国内来源 `coverage_complete` / `listing_coverage_complete` 设为 `null`，`date_coverage_required=false`；`last_verified_date` 旧值迁移至 `legacy_last_verified_date`，不再将旧游标误当新覆盖证据。
- 新的已保存正文不会被之后失败时的标题线索覆盖。不同入口以真实列表及独立发布日期质量优先，避免错误镜像覆盖已经解析正确的主目录。

**2. 重新清点已经保存的结果**

- `policy_saved_results_audit.py` 在每次 GitHub 抓取**前后**生成 `diagnostics/domestic_saved_records_before.csv`、`domestic_saved_records_after.csv`，分别统计每来源已入库政策、最近30天记录、正文证据和媒体线索；不覆盖原数据。
- `diagnostics/V8_PREVIOUS_PARTIAL32.csv` 专门标出2026-10-19旧日志里32个日期/分页覆盖不完整来源；其中6个旧日志曾报告找到候选，合计11条，但 **`+N` 不等于实际入库或已取得官方全文**。
- `diagnostics/V8_20261019_DOMESTIC_BASELINE_118.csv` 列出118来源旧状态、是否调整入口及后续网络验收限制。

**3. 修复旧日志9个 `needs_adapter` 来源的入口/规则**

- 广东省能源局：改成官方“通知公告”政策目录 `https://drc.gd.gov.cn/snyj/tzgg/index.html`，支持 `post_...html` 正文。
- 山东省政府：以 `https://gb.shandong.gov.cn/col/col314852/index.html` 官方规范性文件库作为主入口，允许公开的 `www.shandong.gov.cn` 政策详情；**该目录显示“发文日期”，不能直接宣称是发布日期**，已单独增加提示。
- 中央国务院及各部委：将 `https://www.gov.cn/zhengce/zhengceku/bmwj/home.htm` 国务院部门文件库设为主入口，原动态搜索只留备用。
- 国家能源局最新文件：添加国家能源局下属机构公开政策目录 `https://prpq.nea.gov.cn/zcfgx`；不冒称其覆盖整个国家能源局全部文件。
- 国家发改委文件库：增加该部委官方移动版文件目录，不再只依赖动态桌面检索。
- 辽宁省政府办公厅：独立识别“发布日期”和“成文日期”，不以成文日期冒充发布日期。
- 新疆“新政发”“新政办发”：增加分类查询及公开政府文件目录入口，无法核实分页时仅提示漏抓风险。
- 中国能源报·中国能源网：从新闻主页改为其公开 `https://www.cnenergynews.cn/search`，浏览器执行公开站内检索，**结果仍是媒体线索，并未实网证实此站在GitHub必然返回搜索结果**。
- 北极星风力发电网保留 V7 既有政策目录及翻页适配机制，详情返回访问验证页时仍只留待核验线索。

**4. 网络连接、访问受限、超时处理**

- 原有 `403 / 404 / 412 / 429 / DNS / TLS / Network is unreachable / timeout` 分类、单域限流、原站失败后官方备用目录补查机制全部保留。
- 网络层不可达不可能靠 CSS 适配解决。**2026-10-19旧日志31个连接失败、16个blocked、5个超时，本包未声称已恢复连接**。
- 如仍存在 `Network is unreachable`，可以仅在获准使用的中国大陆 Mac 上做**连接对照诊断**（不是让Mac承担正式抓取，也不用改你已成功的海外监测）：

```bash
python3 -m pip install requests
python3 policy_network_probe.py --region mainland-mac --provinces-first --limit 32 --timeout 7 --output diagnostics/network_mainland_mac.json
```

  下载本次GitHub Actions工件中的 `diagnostics/network_github_actions.json` 到相同位置，然后比较：

```bash
python3 policy_network_probe.py --compare diagnostics/network_github_actions.json diagnostics/network_mainland_mac.json --output diagnostics/network_comparison.json
```

  该工具只检查官网公开可达性，不登录、不绕过验证码或访问限制。如果两边访问结果不同，再决定是否有必要调整网络执行环境；不急于建立双端系统。

**5. 实际政策验收，而不是 `verified=True`**

- 重点看 `site/data/policy_site_acceptance.csv` 的“实际目录读取成功”“政策及线索数”“正文取得条数”“目录异常提示”。
- 还应核对前后入库审计的差异，查看真实发布日期、政策标题、发文机关和原文URL。
- 只发现标题和日期，标为“待核验政策线索”；媒体不是法规官方原文。
- 国内失败站点继续保留真实HTTP错误，备用渠道发现政策不等于原站恢复。

## 二、安装——完整包直接上传

如果仓库是**新建空仓库**：解压，打开最外层项目文件夹，把里面的全部内容复制进你克隆的 GitHub 仓库根目录（包括隐藏的 `.github`），GitHub Desktop `Commit to main` → `Push origin`。

如果已经在 GitHub 正常运行过（**更可能是你的情况**）：

1. 使用 GitHub Desktop 将仓库拉取到最新，**先备份本地仓库内的 `site/data` 整个文件夹**（尤其 `policies.json`、policy_source_checkpoints 和政策状态）。
2. 解压这个完整项目包，把最外层目录**内部全部文件**复制进GitHub Desktop克隆的仓库根目录；不要删 `.git` 目录。
3. **将步骤1备份的 `site/data` 覆盖回仓库 `site/data`**，保留你之后运行获得的新增政策及历史游标。本包自带 `site/data` 是老数据快照，不代表现在GitHub的最新数据。
4. 核对待提交文件，确认国外21个适配器和前端源码没有被误修改，然后 `Commit to main` → `Push origin`。
5. `GitHub → Actions → Wind policy & industry monitor — collect and deploy → Run workflow`，选择 `provincial`（优先国内与北极星）。**不要另建工作流**。
6. 等整条工作流跑完下载 `wind-policy-backend-diagnostics`，打开 `last_run_quality.md`、`domestic_saved_records_before.csv`、`domestic_saved_records_after.csv`、`network35_runtime_report.csv` 和 `site/data/policy_site_acceptance.csv`。

## 三、验收和局限

- 已离线运行 **130项 Python 回归测试及两套 Node 前端测试**，包含滚动时间窗、国内外不同游标、失败详情重试、国内日期识别、政策入库、官方媒体线索区分。
- 原网站前端6文件和海外21个适配器字节级一致。国外来源配置与海外定时抓取规则未更改。
- **本交付环境无法稳定通过网络直接访问中国政务网站，因此没有139站的真实网络实测成功报告。** 下一次GitHub运行才能证明这次修改实际改善了多少来源。
- 取消时间覆盖证明**不意味着绝不漏抓**；最近30天滚动补抓可降低遗漏风险，但站点仍可能因动态翻页、反爬或断网漏抓。请结合报告逐站补救，而不要只看日志颜色。
