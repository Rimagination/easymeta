# 数据质量与可重复性

本文件定义数据契约、质量门和 AI 审计要求。项目可以增加字段，但不得改变核心字段语义；任何字段迁移都要保留旧版本、转换脚本和变更说明。

## 目录

1. 数据对象与标识符
2. 分层保存与不可变性
3. 提取 CSV 契约
4. 数值与语义质量规则
5. 双人提取、核验与裁决
6. 自动校验器
7. 可重复分析包
8. AI 使用与可重复性
9. 发布前质量门

## 1. 数据对象与标识符

采用四层模型：

```text
record（数据库命中） -> report（可引用文献） -> study（独立研究） -> effect（可分析效应）
```

- `record_id`：每次导入的检索记录；同一报告可有多个 record。
- `report_id`：一篇文章、注册记录、报告或补充材料；同一 study 可有多个 report。
- `study_id`：同一受试者、样地或实验单元的研究实体。随访论文通常仍属同一 study。
- `effect_id`：分析表每行唯一且永不复用。建议 `<study_id>__<outcome>__<timepoint>__<contrast>`。
- `dependency_cluster`：标记共享受试者、对照、地点、物种或其他相关来源。它不能代替模型中的依赖处理说明。

标识符一经发布不因题名或作者更正而改变。合并或拆分研究时保留旧 ID、理由、操作者和时间。

## 2. 分层保存与不可变性

至少区分以下层，不用手工覆盖上游文件：

1. `raw`：原始导出、原文、作者回复；只读并记录来源、许可、获取日期和校验和。
2. `working`：去重、报告聚类、筛选和独立提取；保留事件历史。
3. `curated`：裁决后的研究主表、效应表、偏倚风险表和字段字典。
4. `analysis`：由代码从 curated 数据生成的派生变量和模型输入。
5. `release`：冻结的数据、代码、结果、日志、环境和报告版本。

敏感原文、个人数据或有许可证限制的全文不得因“可重复性”而公开。公开元数据、哈希、转换代码和受控访问说明通常足以证明来源链。

## 3. 两阶段 CSV 契约

始终分开保存“论文报告了什么”和“Meta 模型实际使用什么”。两个阶段均使用 UTF-8 CSV、唯一字段名和明确版本；不得把 `NA`、`NR`、`?` 混入数值字段。

### 3.1 `raw_extraction/1.0.0`

从 `assets/extraction_template.csv` 开始。每行声明 `schema_version=1.0.0`、`data_stage=raw_extraction`，保留 `study_id`、`report_id`、`effect_id`、问题定义、设计、方向、单位、独立性线索和来源定位。

原文若报告效应及 CI，可按原报告尺度填入 `effect_measure`、`effect_scale`、`effect_estimate`、`se`、`variance` 和 CI；若只报告四格表、均值/SD、相关、事件/人时等原始统计量，对应效应或不确定性字段可以为空。不得为了通过校验而在 raw 阶段制造一个尚未计算的效应。

`n_intervention`, `n_comparator`, `events_intervention`, `events_comparator`, `mean_intervention`, `sd_intervention`, `mean_comparator`, `sd_comparator` 用于重算和核验。配对/交叉连续资料、两组变化值、BACI 和已报告群集校正估计从 `assets/complex_effect_input_template.csv` 开始，并使用 `scripts/calculate_complex_effects.R`；其他复杂多组或重复测量设计应增加经审核的结构化表，不要压进独立两组模板。

运行：

```bash
python scripts/validate_extraction.py raw.csv --stage raw
```

### 3.2 `analysis_effect/1.0.0`

使用 `scripts/calculate_effect_sizes.R` 从冻结 raw 文件生成；结构示例见 `assets/analysis_effects_template.csv`。每行除 raw 字段外，还必须包含：

| 字段 | 规则 |
|---|---|
| `source_schema_version`, `source_data_stage`, `source_file`, `source_file_md5`, `source_row` | 可定位到具体 raw 文件和物理行；最终发布 manifest 另用 SHA-256 |
| `calculation_method`, `calculator_version`, `calculated_at_utc` | 明确计算入口、版本和 UTC 时间 |
| `yi`, `vi`, `sei` | 全部位于同一个 `analysis_scale`；有限，`vi>0`、`sei>0` 且 `vi ~= sei^2` |
| `measure`, `analysis_scale`, `display_transform` | 分析度量、模型尺度和展示反变换不得相互矛盾 |

同一个 analysis-effect 文件只能使用一个 `analysis_scale`。自然尺度 RR/OR/HR/IRR/ROM 必须先变换到 `log`；相关通常用 `fisher-z`；比例等按预先选择的度量记录 `logit`、`arcsine` 或其他明确尺度。

运行：

```bash
python scripts/validate_extraction.py effects.csv --stage analysis
```

### 3.3 共享受控值

- `effect_measure`：`MD`, `SMD`, `HEDGES_G`, `ROM`, `RR`, `OR`, `HR`, `IRR`, `RD`, `CORRELATION`, `FISHER_Z`, `PROPORTION`, `OTHER`。
- `effect_scale` 描述论文报告值；`analysis_scale` 描述 `yi/vi/sei`。二者不得互相代替。
- `direction`：`higher_favors_intervention`, `lower_favors_intervention`, `higher_favors_exposure`, `lower_favors_exposure`, `higher_is_harmful`, `higher_is_beneficial`, `not_applicable`。
- 自定义效应量使用 `OTHER`，并在 `notes` 和分析计划中给出定义、零效应、尺度及方差公式。

## 4. 数值与语义质量规则

### 4.1 基础不变量

- 所有数值必须可解析且有限；拒绝 `NaN`、`Inf` 和含单位的数值字符串。
- `se > 0`、`variance > 0`、`0 < ci_level < 1`、`ci_lower < ci_upper`、`ci_lower <= effect_estimate <= ci_upper`。
- 自然尺度的 `RR/OR/HR/IRR/ROM` 及其区间必须大于 0。
- 自然尺度的 `CORRELATION` 和 `RD` 位于 `[-1, 1]`；`PROPORTION` 位于 `[0, 1]`。
- 样本量为正整数；事件数、样本量和分组总数满足逻辑关系。
- 单位转换必须生成新字段或新版本，记录公式、常数、操作者和原值；不得只覆盖原值。

### 4.2 SE、方差与区间

raw 阶段的 `se`、`variance` 和 CI 只描述原文报告值及其 `effect_scale`；analysis 阶段的 `sei`、`vi` 只描述 `yi` 的 `analysis_scale`。两阶段不得混用。analysis 阶段强制 `vi ~= sei^2`；raw 阶段不要仅凭正态近似强制 CI 与 SE 完全一致，轮廓似然、精确区间、Bootstrap、Bayesian 区间和四舍五入都可能造成不对称。

### 4.3 多效应与独立性

同一 `study_id` 出现多行是常见而非自动错误，但必须触发审阅：

- 确认它们来自不同结局、时间、组别、地点或物种，而非重复录入。
- 填写 `dependency_cluster` 并在分析计划中选择效应、聚合、分层模型、多变量模型、稳健方差或其他处理。
- 另行声明 `independent_cluster_field`。它表示可独立提供信息的研究/抽样单元；小研究检验、Meta 回归信息量和 leave-one-out 必须按该字段计数，而不是按 CSV 行数。
- 共享对照组时不能把完整对照样本重复计入多个完全独立比较。
- 主分析与依赖处理敏感性分析应可从同一冻结数据重建。

## 5. 双人提取、核验与裁决

1. 先冻结提取表版本，在至少一项简单研究和一项复杂研究上试填。
2. 保留两份独立原始提取或逐单元审计记录；不要让第二人只看第一人的最终答案而无来源材料。
3. 比较程序应区分完全一致、格式差异、数值差异、解释差异和缺失差异。
4. 裁决记录包含两份原值、最终值、依据、裁决者和日期。作者回复与图形数字化数据标明来源类型。
5. 进入分析的数据状态至少为 `verified`；存在实质争议时为 `queried`，不得静默进入主模型。
6. 使用 `scripts/reconcile_extractions.py` 只做逐单元比较和裁决完整性检查。它不得根据多数、精度、显著性或提取者身份选择最终值；裁决仍由人完成。
7. 使用 `scripts/validate_study_map.py` 验证 report—study 映射和样本重叠处置。映射层问题必须先解决，不能靠模型中的 study 随机效应补救重复队列。

## 6. 自动校验器

运行：

```bash
python scripts/validate_extraction.py path/to/raw.csv --stage raw
python scripts/validate_extraction.py path/to/effects.csv --stage analysis
```

查看参数：

```bash
python scripts/validate_extraction.py --help
```

退出码契约：

| 退出码 | 含义 |
|---:|---|
| `0` | 无错误且无警告；或使用 `--allow-warnings` 接受了仅警告结果 |
| `1` | 至少一个数据验证错误 |
| `2` | 命令用法、文件读取、编码或 CSV 解析失败 |
| `3` | 无错误但存在警告，默认用于阻止无人审阅地继续分析 |

`--allow-warnings` 只改变“仅有警告”时的退出码，不隐藏警告，也不能放行错误。校验器是最低质量门，不替代来源核对、偏倚风险评价或统计审查。

## 7. 可重复分析包

每次可发布运行至少记录：

- 协议和分析计划版本、Git 提交或等价快照标识。
- 输入文件路径、字节哈希、行数、字段字典版本和校验结果。
- 操作系统、语言/运行时、包及精确版本；禁止只写“使用 R/Python”。
- 入口命令、参数、环境变量白名单、区域设置、时区和随机种子。
- 从原始效应到模型输入的转换代码，不手工粘贴分析数据。
- 每个模型的公式、估计方法、权重、方差/相关结构、缺失处理和软件调用。
- 输出文件哈希、生成时间、日志、警告和失败记录。

对 living guidance 和评价/报告工具，另从 `assets/guidance_manifest_template.csv` 建立版本账本，记录官方 URL、实际版本、更新时间/访问日、里程碑复查、更新信号、快照/哈希、影响分类、采用决定和协议偏离。运行：

```bash
python scripts/validate_guidance_manifest.py guidance_manifest.csv
```

该校验器不判定来源是否权威；权威性仍按 `source-registry.md` 人工确认。

使用 `assets/field_lineage_template.csv` 记录每个结构化输出字段的上游字段、转换和公式/代码位置，然后运行：

```bash
python scripts/build_lineage_manifest.py \
  --lineage field_lineage.csv \
  --input raw.csv --script analysis.R --output effects.csv \
  --artifact model.rds --artifact analysis.log \
  --seed not_applicable --manifest lineage_manifest.json
```

该工具要求所有结构化 `--output` 字段有且只有一条完整谱系，并为输入、脚本、结构化输出和任意文件型 `--artifact` 生成 SHA-256。`.rds`、日志和文本 manifest 作为 artifact 纳入哈希，但不能借此绕过结构化输出的字段谱系门。任何字节变化都产生不同 manifest。

另用 `assets/publication_integrity_template.csv` 记录 `paper`、`data`、`code` 对象的检查时间、状态、来源、处置与敏感性分析：

```bash
python scripts/validate_integrity.py publication_integrity.csv
```

`unknown`，或任何未处置的 correction/comment/expression-of-concern/retraction/withdrawal/version-update，均阻断正式合成。

随机种子只能控制支持确定性的环节；外部 API、滚动模型或数据库结果仍可能变化，必须保存原始响应或可合法保存的摘要、时间戳和版本。

## 8. AI 使用与可重复性（CEE 蒸馏）

CEE 将预测式和生成式 AI 在计划、检索、去重、筛选、评价、提取、合成和报告中的使用均纳入披露范围。对每一个 AI 系统建立独立 `ai_system_id`；同一系统跨多个工作流阶段使用时，再建立独立 `ai_stage_run_id`，因为筛选通过不证明提取、评价或合成也可靠。在 `analysis_plan_template.yaml` 中记录以下内容。

### 8.1 工具身份与用途

- 名称、开发者/提供者、产品版本、模型/快照版本、访问日期、接口和服务层级。
- 在工作流的哪里、如何以及为什么使用；属于自动、半自动还是仅建议。
- 对每个阶段分别记录输入单位、允许输出、系统能否作判断、人工复核范围和最终责任人；不要用“一般用于辅助综述”覆盖多个任务。
- 自定义训练、检索语料、阈值、温度、随机种子、系统提示、插件、后处理和其他参数。
- 已发表的外部验证及其适用性；协议中的计划和报告中的实际使用与偏离理由。

### 8.2 提示词、输入与代码

- 保存最终的精确系统提示词、用户提示词、模板变量、少样本示例和提示词选择理由。
- 为每次批处理记录 prompt ID、输入清单/哈希、运行时间、原始输出或受限输出位置、重试和后处理。
- 保存生成或分析结果所用的全部代码、脚本和参数。
- 若精确提示词嵌入受版权或隐私保护的全文，公开版保留提示结构、文献标识、哈希和访问条件；受控审计包保存依法可留存的完整内容。不能以可重复性为由再分发无权公开的材料。

### 8.3 项目—阶段内验证

- 在当前项目的主题、语言、文献类型、数据库来源、时间分布和具体任务阶段中建立独立人工金标准；避免用调参样本同时作最终验证。供应商基准、另一主题论文或同一模型在另一阶段的表现只能作背景，不能替代项目—阶段验证。
- 预先定义任务相关指标与通过阈值。筛选至少关注召回和漏纳类型；提取关注字段级准确性、数值错误与来源定位；判断任务记录人机一致性和分歧。
- 报告样本选择、样本量、盲法、人工复核者、结果和不确定性。未验证时说明原因，且不得让系统独立作高风险排除或最终判断。
- 模型/快照、提示、阈值、检索语料、前后处理、供应商行为、输入语言/文献类型或数据分布实质改变时重新验证。记录错误/误分类如何发现、纠正、是否追溯重跑先前批次，以及反馈到流程的版本。
- 若验证未达预设阈值，降级为人工主流程、扩大复核或停用该阶段；不得在看见最终综述结果后放宽阈值。

### 8.4 人工监督、偏差与责任

- 指定每个 `ai_stage_run_id` 的最终责任人和人工复核范围；“抽查”须给出抽样框、分层/随机规则、样本量和升级为全量复核的条件。
- 记录已知限制、幻觉、自动化偏差、语言/地域/发表类型偏差和潜在利益冲突，以及缓解措施和残余风险。
- AI 不列为作者，不作为事实或方法的一手来源。所有引用、数字、排除和风险判断回到原始材料核验。
- 披露与 AI 开发者/提供者有关的资金、财务利益、隶属或冲突。

### 8.5 隐私、保密与法律

- 在上传前分类数据：公开、许可受限、机密、个人数据、敏感个人数据。
- 记录传给第三方的字段、地区/管辖、传输与存储、保留期限、是否用于模型训练、访问控制、删除机制和适用法律/伦理审批。
- 默认不向未批准的外部 AI 服务上传个人数据、未公开稿件、同行评审材料、作者私信、受许可限制全文或机构机密。
- 评估来源/provenance、抄袭、版权、知识产权、许可证、保密、数据保护和研究完整性；隐私化不能消除版权或合同限制。

## 9. 发布前质量门

- 校验器退出 `0`，或退出 `3` 后每条警告有书面处置。
- 综合路由已保存，且只有 `runner_allowed=true` 的计划进入普通 `yi/vi` runner。
- raw 与 analysis-effect 两阶段分别通过校验；尺度、`yi/vi/sei` 和展示反变换一致。
- 所有主分析效应均为 `verified/adjudicated`，来源定位可回查，方向和单位明确。
- 研究多效应、共享对照和群集结构已在模型或选择规则中处理；所有信息量判断使用独立簇数。
- 论文/数据/代码完整性 ledger 通过校验；所有非 clear 状态已有处置和敏感性分析。
- 分析由干净环境从冻结输入一次性重跑，表、图和正文数字来自同一输出。
- 字段谱系完整，冻结输入、脚本和输出的 SHA-256 已生成并归档。
- 协议偏离、探索性分析、缺失数据和失败运行均未从审计轨迹删除。
- 每个 AI 系统—工作流阶段均有工具/模型快照、用途、精确提示词、项目—阶段验证、人工复核、偏差、错误纠正和隐私记录；报告披露与审计包一致。
- living guidance manifest 与 CEESAT/MATES ledger（若适用）分别通过 `validate_guidance_manifest.py` 和 `validate_review_appraisal.py`；评价结果未跨层级求和。
- 双人提取差异全部裁决；study—report 映射与样本重叠账本通过校验。
- 风险偏倚与证据可信度账本通过 `scripts/validate_appraisal.py` 的结构检查，但最终判断仍有可定位的人类评价与裁决。

官方来源版本和更新策略见 `source-registry.md`。
