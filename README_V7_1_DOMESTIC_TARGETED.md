# V7.1 国内政策来源定向修复（不改网站，不改国外爬虫）

## 修订范围

本版**只动国内抓取入口和6个有公开文章样本支持的抓取路径规则**。原有139个来源中，118个中国来源（含北极星）仍按原计划监测；21个国际来源配置及其 adapter 文件完全不变。网站的HTML/JS/CSS和原工作流 `update.yml` 也没有改。

**注意：源网站“官方栏目可找到”不等于“GitHub Actions 已成功抓取”。** 当前交付环境尝试 HTTP 请求时出现 DNS 解析失败，因此不能宣称6个专站或全部118个中国来源已在实际执行端通过抓取测试。本版离线测试用于防止解析误判，线上验收仍以 GitHub Actions 的 `site_probe_github.json` 和 `province_coverage.csv` 为准。

## 已依据可公开检索的真实页面编写定向规则

| 来源 | 来源ID | 实际公开的政策目录/文章证据 | 修复点 |
|---|---|---|---|
| 贵州省能源局 | cn_61f329f622c8 | https://nyj.guizhou.gov.cn/zwgk/xxgkml/zdlyxx/xnygl/index.html | 保留普通文件目录，新增新能源与可再生能源目录备用入口；两类文章路径区分 |
| 上海市发改委能源栏目 | cn_c3d9397ca287 | https://fgw.sh.gov.cn/fgw_ny/20260805/27ca3c27046b414992b0182cf8ed47a8.html | 识别 `/fgw_ny/YYYYMMDD/{文章UUID}.html` 与日期字段 |
| 福建省发改委 | cn_b85a8fe9fba8 | https://fgw.fujian.gov.cn/zwgk/fgzd/sfgwgfxwj/202608/t20260805_7196169.htm | 识别真实政策文章路径；Vue 未完成分页不标记完整覆盖 |
| 内蒙古自治区能源局 | cn_eb58eb83050f | https://nyj.nmg.gov.cn/slh/zfwj/202609/t20260908_2951227.html | 识别政策举措目录文章路径、单行发布日期；不混淆成文日期 |
| 山西省能源局 | cn_0cedc4affbe8 | https://nyj.shanxi.gov.cn/zfxxgk/fdzdgknr/sjwj/202610/t20261016_10236977.shtml | 识别最新文件路径。原入口在公开检索环境不可直接访问，**仍待实测** |
| 江苏省发改委 | cn_642f1102f38a | https://fzggw.jiangsu.gov.cn/art/2026/9/21/art_51007_11832455.html | 从官方法律规范文件目录严格识别 `/art/Y/M/D/art_...html`；避免聚合首页误判完整 |
| 北极星风力发电网 | cn_5555c1d4376e | https://fd.bjx.com.cn/zc/ 和 https://fd.bjx.com.cn/zc/2/ | 保留V7已建立的跨子域文章目录规则，补充正文返回WAF验证页面时的识别，保留媒体线索等待官方原文 |

每条规则只使用公开文章 URL 结构和本地 DOM 解析，不猜测隐藏 API，也不绕过站点访问限制。针对其他未逐站采样的中国政策站点保留现有规则、由实际运行结果指导后续修正，**绝不将它们标注为“已核验成功”**。

## 上线步骤（沿用 GitHub，不需要 Mac）

1. 备份当前 GitHub 仓库，特别是 `site/data/` 中的历史法规、重试队列及游标数据。
2. 从本压缩包根目录把文件**覆盖到现有 V7 仓库根目录**。若 GitHub 上已有更新的国外程序，先对照差异；不要用旧的压缩包覆盖新国外文件。
3. 在 GitHub Actions 手动运行现有 `update` 工作流，选择 `crawl_scope=provincial`，不要新增第二套工作流。
4. 运行完成后，从 `wind-policy-backend-diagnostics` 中下载 `site_probe_github.json`、`site_probe_github.csv`、`provincial_source_recovery.csv` 和 `province_coverage.csv`。
5. 一站一站验收：HTTP是否读到；目录行/日期数；真实下一页能否遍历；至少一条政策正文或附件；覆盖是否证明。网络无法连接时保持失败，并用正式官方备用来源/北极星找政策线索。媒体线索不升级为已核验法规。

## 隐私与授权

本版不涉及电脑定时任务、Mac服务器、自托管运行器和访问令牌配置。对于403、412、验证码、登录或受限制网站，程序记录原始拒绝证据，不绕过。中国大陆电脑若后续确实可以访问某个GitHub不可访问的政务网站，可作为针对**该站点**的备选执行方案，但本次没有增加这种复杂架构。

## 验收界限

- 离线 Python `unittest discover -s tests -p test_policy_*.py`：86项通过。
- 前端两套 Node 测试通过。
- 6个前端HTML/CSS/JS文件与V7原版逐字节一致；21个国外适配器及来源配置不变。
- **真实官网抓取成功率：尚未验证。** 测试与配置数量不等于实际抓取成功。
