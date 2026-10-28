# OpenJLPT 中文试点

此 fork 为 OpenJLPT 增加简体中文内容与数据质量检查。上游项目和数据来源的署名见 [NOTICE.md](NOTICE.md)。

当前中文正式稿覆盖 N5、N4 各 100 个词汇、各 15 个语法点；词汇例句中文 400 条、语法例句中文 89 条。按项目所有者 2026-10-28 的授权，由 Codex 审校后转为正式稿，页面标注“正式稿 · AI 审校”。这不是独立人工复核。其余内容仍显示英文，N5/N4 全量内容尚未完成。

## 数据与审核

- 原始词表和语法仍在 sources/ 中；稳定 ID 不因中文化而改变。
- sources/corrections/entries.json 保存按 ID 应用的纠错及依据。只接受记录中的旧值或新值；遇到不同的上游修改会报冲突，避免静默覆盖。
- sources/zh-CN/vocab.json 与 grammar.json 保存中文源内容、源哈希、参考说明及审核状态。
- 修改日文、读音、释义或例句会使中文状态变为 stale。页面、搜索、导出不使用过期中文，回退到英文；原中文源文件保留供复核。
- reviewed 必须记录 reviewer、review_method、reviewed_at 和 review_hash。中文释义、讲解、例句译文或参考资料改变后，旧审核指纹会使构建失败；须实际复核后更新指纹，或先降回 draft。重新计算哈希不代表已经完成内容审核。
- sources/quality/review-2026-10-28.json 记录本轮审核范围、逐条指纹与纠错决定；review-dictionary.json 保留所核对的 JMdict 释义摘录及下载文件校验和。中文由 Codex 原创，词典摘录不能视为独立中文验证。
- sources/quality/pilot.json 记录本轮样本。样本主要按读音顺序选择，并加入纠错案例，不能用于估计全库错误率。
- data/quality-report.json 记录覆盖率和待复核候选；同词典 ID 与读音的重复项可能是合理异体写法，不能自动合并。

本轮 200 个词的例句已全部翻译；其余词汇、汉字中文释义、完整中文界面与 N3–N1 内容属于后续范围。现有 Yomitan 导出是等级元数据词典，不包含释义；Anki 保留原有 note ID，增加双语内容。

## 本地验证

在仓库根目录执行：

```text
npm ci
npm run prepare:data
npm run check:data
npm run validate
npm run typecheck
npm test
npm run build:pkg
uv run --no-project --with pytest --with genanki python -m pytest -q
npm run audit:data
```

prepare:data 使用已提交的数据离线应用纠错、合并中文并重建 SQLite，无需下载完整语料。完整上游更新仍使用 npm run build，涉及上游网络下载及 tar/bzip2 工具。

JSON 的 zh 字段保留英文接口；CSV 追加中文字段；SQLite 的 vocab、grammar 表追加 zh JSON 列。Python 和 TypeScript 搜索支持中文释义。Python 返回条目的嵌套列表和中文字典拒绝普通修改，调用方如需编辑请显式转换为自有副本。

## 网站与部署

npm run build:site 会生成静态网站；通过 SITE_URL 指定正式域名。网站的 dataset/ 下载来自本次构建，避免下载到上游未修正的数据。使用以下命令补齐下载：

```text
uv run --no-project --with genanki python scripts/build_exports.py _site/downloads
```

CI 构建可追溯到提交的静态产物，包含网页、数据和下载包。VPS 仅需提供静态文件；此阶段未部署到 VPS。正式部署前确认域名、已有 Web 服务和资源负载，并重新生成匹配域名的产物。

GitHub 定时更新需要开启允许 Actions 创建 PR 的仓库设置。fork 已保持默认只读 token 权限；更新 workflow 单独请求写入权限。更新失败时保留数据产物供排查。

## 实施记录

- 上游基线：0d1d3410bec90bd4098a7c72de820543cb4f707c。
- 纠错累计覆盖 41 个词条：首轮 6 个，本轮新增 35 个，包含释义补全、例句替换、注音修复及缺失例句补充，不等同于发现 41 个错误词义。
- 本轮修复「五つ」误选地名例句、「いただきます」饭前用语与例句不一致、「上げる」缺少举起义，以及「以下／以上」英文遗漏包含端点等问题。
- 修复注音生成器将词典编号当读音的问题。试点中的 4 个相关条目已修复；全库扫描仍有 91 条非试点例句的注音待复核，列于 quality-report.json，未声称全库已校正。
- 受付的 receipt 并非无效词义，本次选择与例句一致的接待处义项；一日限定初学者卡片的时长义项。
- せっけん与石鹸暂保留原有两张卡片，避免破坏已有学习记录；合并需要单独的 ID 迁移方案。
- 新创作的日文例句不挂原 Tatoeba ID；仅修复注音的原例句保留署名。
- 完整上游刷新可能改变纠错字段并触发保护性冲突，须检查后调整记录；本轮验证的是已提交快照的离线重建和导出。
