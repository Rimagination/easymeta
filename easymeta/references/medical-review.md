# 医学证据综合：问题、研究设计、结局与效应量路由

> 用途：供另一个 Codex 在医学、公共卫生与医学生态学证据综合中选择方法。本文是操作规则，不替代临床、统计或主题专家判断。
>
> 资料核验日：2026-08-02。方法学会更新；执行项目前须按“来源与更新”复核版本。

## 目录

- [一、硬性原则](#一硬性原则)
- [二、从问题到方法的路由](#二从问题到方法的路由)
- [三、研究设计与纳入规则](#三研究设计与纳入规则)
- [四、医学结局的预设与提取](#四医学结局的预设与提取)
- [五、效应量选择](#五效应量选择)
- [六、能否合并及如何综合](#六能否合并及如何综合)
- [七、何时转向专门方法](#七何时转向专门方法)
- [八、不可自动化的判断与人工复核](#八不可自动化的判断与人工复核)
- [九、最小交付与审计记录](#九最小交付与审计记录)
- [十、来源与更新](#十来源与更新)

## 一、硬性原则

**就近依据：** [Cochrane Handbook current](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current)、[JBI Manual 2024](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true)、[PRISMA 2020](https://www.prisma-statement.org/prisma-2020)。

1. **先定问题，后看结果。** 在浏览研究结果前锁定问题类型、目标人群、暴露或干预、比较、结局、时间点、目标效应（estimand）、纳入设计和主要综合方法。任何事后改变均须标为方案偏离并说明原因。
2. **问题类型决定方法，论文自称的设计不决定方法。** 根据分配方式、时间顺序、抽样、比较组、随访和分析特征判定设计；不要只接受“队列”“病例对照”“真实世界研究”等标签。
3. **一个可评价结果的基本单位是**“研究 × 比较 × 结局定义 × 时间点 × 分析/效应量”。偏倚评价、效应提取和证据确定性须与该单位对齐。
4. **可合并不等于应合并。** 只有目标问题、结局构念、时间窗、比较、目标效应和设计足够相容时才进行定量合并；统计模型不能修复临床或因果问题不一致。
5. **患者重要结局优先。** 死亡、症状、功能、生活质量、严重不良事件和资源使用通常优先于替代结局。替代结局不得与患者重要结局混成一个结果。
6. **同时报告效应大小和不确定性。** 至少给出点估计与 95% CI；二分类结局通常同时给相对效应和基于明确基线风险、时间窗的绝对效应。不要用“有/无统计学显著性”代替解释。
7. **设计不同、调整程度不同的证据默认分层。** RCT 与非随机干预研究、调整后与未调整估计、不同因果目标通常分别综合；只有经方案预设且方法学理由充分时才联合建模。
8. **PRISMA 是报告规范，不是实施质量或偏倚工具。** 用 PRISMA 2020 及适用扩展检查透明报告，但不能据此证明检索完整、研究无偏或结论可信。
9. **不得编造或静默推断缺失数据。** 从图形数字化、单位换算、SD 推导、HR 重建或作者联系获得的数据都要记录来源、公式、假设和复核者。
10. **将偏倚与确定性路由到** [bias-and-certainty.md](./bias-and-certainty.md)；不要在效应模型中用任意“质量分数”替代正式判断。

## 二、从问题到方法的路由

**就近依据：** [Cochrane Ch.2](https://training.cochrane.org/handbook/current/chapter-02)、[Cochrane Ch.3](https://training.cochrane.org/handbook/current/chapter-03)、[JBI Manual 2024](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true)、[Cochrane DTA Handbook](https://www.cochrane.org/authors/handbooks-and-manuals/handbook-systematic-reviews-diagnostic-test-accuracy)、[Cochrane Prognosis tools](https://methods.cochrane.org/prognosis/tools)。

### 2.1 第一步：给问题分类

| 决策意图 | 推荐问题框架 | 首选/典型研究设计 | 主要结果 | 必须切换的专门路线 |
|---|---|---|---|---|
| 干预的获益或常见伤害 | PICO；补充时间点与目标效应 | 个体 RCT；按问题可纳入整群、交叉、阶梯楔形等随机设计 | RR/OR/RD、MD/SMD、HR、率比 | 非标准随机设计、网络 Meta、复杂干预、IPD |
| 罕见、迟发或长期伤害 | PICO/PECO | RCT 加前瞻性/回顾性队列、病例对照、监管或监测资料；各来源分层 | 风险、率、HR、OR；信号资料通常仅叙述 | 罕见事件、安全性监测、竞争风险 |
| 非随机干预效果 | PICO + 明确目标试验与 estimand | 有并行比较且可支持因果推断的 NRSI；优先调整后结果 | 调整后 RR/OR/HR/率比或目标试验效应 | ROBINS-I、因果推断；不能按普通队列质量表替代 |
| 环境、职业、行为或病因暴露 | PECO；明确暴露窗口、剂量和混杂结构 | 队列优先；病例对照适合罕见结局；分析性横断面仅支持同一时点关联 | 调整后 RR/HR/OR、剂量反应 | ROBINS-E/JBI 病因风险方法；**不得使用 ROBINS-I 评价纯暴露** |
| 诊断准确性 | participants–index test–target condition–reference standard；含阈值与用途 | 横断面或队列式准确性研究；避免把二门病例对照设计当等价证据 | 灵敏度与特异度联合、LR+/LR−；必要时 DOR | Cochrane DTA、QUADAS-3、双变量/HSROC、PRISMA-DTA |
| 检测策略对患者结局的影响 | PICO；检测—治疗路径视为干预 | 随机或合适的比较性非随机研究 | 患者重要结局的 RR/MD/HR 等 | **走干预效果路线**，不能只做准确性 Meta |
| 患病率或某时点比例 | CoCoPop（condition–context–population）并明确时间/地区/病例定义 | 有代表性的横断面调查或队列基线；概率抽样优先 | 患病率/比例及 CI | PERSyst/JBI 患病率方法；不能纳入病例对照估计患病率 |
| 发病率 | 人群–风险期–病例定义–随访窗口 | 封闭或开放队列、监测系统且分母/人时可定义 | 累积发病风险或发病密度 | 重复事件、动态人群、竞争风险方法 |
| 总体预后 | PICOTS；疾病起点、起始队列和预测时间窗必须明确 | 起始队列/临床队列，充分随访 | 指定时间风险、存活率、累积发生率 | Cochrane Prognosis；竞争风险与删失 |
| 预后因子 | PICOTS + index prognostic factor | 队列；优先多变量调整结果 | 调整后 HR/RR/OR，按时间窗与调整集分层 | QUIPS 与预后因子 Meta；不能与病因效应混称 |
| 诊断/预后预测模型 | 目标人群–结局–时间窗–使用场景；区分开发与验证 | 模型开发、外部验证、更新、影响研究分别处理 | 校准、区分度、总体性能、临床效用 | CHARMS、PROBAST+AI、TRIPOD-SRMA；通常需专门统计人员 |
| 测量工具性能 | 构念–人群–工具–测量属性 | 信度、效度、反应度等专门设计 | 依测量属性而定 | COSMIN；不能套普通干预 Meta |
| 体验、障碍、可接受性 | PICo（population–phenomenon of interest–context） | 定性研究 | 主题/发现而非数值效应 | JBI 定性综合或其他已选定框架；需要 ConQual 时按其规则 |
| 多种证据共同回答实施问题 | 分别构造定量与定性子问题 | 混合方法研究及相应单方法研究 | 分组件后整合 | JBI 混合方法；不得直接混合不可比数据 |
| 成本与资源配置 | 明确视角、时间范围、币值年 | 经济评价 | 成本、QALY、增量成本效果 | 专门经济证据综合 |
| 仅描绘概念、范围或证据缺口 | PCC（population–concept–context） | 多种证据类型 | 证据地图/描述 | Scoping review；不要默认进行效果 Meta 或 GRADE |

### 2.2 第二步：写出可执行问题卡

每个主要问题至少填写：

- `question_type`：上表中的一种；若有多个意图，拆成独立子问题。
- `population`：疾病阶段、严重度、年龄、合并症、地区/医疗场景和排除条件。
- `intervention_or_exposure`：强度、剂量、持续时间、实施者；暴露须写时间窗和测量方法。
- `comparator`：常规治疗、安慰剂、无暴露、替代检测或其他明确状态，不能只写“对照”。
- `outcome`：构念、操作定义、测量工具、方向、阈值、时间点和患者重要性。
- `estimand`：效应对象、比较条件、处理依从/交叉和并发事件的策略、总体层面的汇总量。
- `eligible_designs`：按实际特征定义，不只列标签；说明为何需要 NRSI。
- `synthesis_groups`：预先定义哪些研究可在同一分析中合并。
- `decision_thresholds`：无/微小、小、中、大效应或最小重要差异；无法预设时写明需临床/患者专家决定。

如果任何一项无法明确，Codex 只能生成“待决问题清单”，不得自动开始主分析。

## 三、研究设计与纳入规则

**就近依据：** [Cochrane Ch.23](https://training.cochrane.org/handbook/current/chapter-23)、[Ch.24](https://training.cochrane.org/handbook/current/chapter-24)、[Ch.25](https://training.cochrane.org/handbook/current/chapter-25)、[JBI etiology/risk guidance in Manual 2024](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true)。

### 3.1 干预问题

- 首选随机证据。准随机分配（生日、病历号、轮流分配等）不是 RCT，应按实际偏倚结构处理。
- 整群随机、交叉、阶梯楔形、析因和多臂试验可纳入，但须使用对应设计的偏倚工具和方差处理；未校正聚类的分析会夸大精度。
- 纳入 NRSI 的合理情形包括：无法或极难随机化、RCT 对目标人群/场景间接、长期或罕见伤害、随访不足。仅因“样本更大”不是充分理由。
- NRSI 必须具有明确比较、时间零点、干预分类、随访开始和混杂控制。单臂病例系列可用于信号发现或描述，不能自动估计比较性因果效果。
- RCT 和 NRSI 默认形成平行证据流：分别列特征、偏倚、效应和确定性；解释一致或冲突，不把两者简单平均。

### 3.2 暴露与病因问题

- 先画简化因果图或至少列出预先认定的混杂域、潜在中介、共同原因与选择机制。不要让数据驱动的逐步回归决定“充分调整”。
- 选取最接近预设调整集的模型。过度调整中介、碰撞变量或暴露后的变量可能引入偏倚。
- 队列最能建立暴露先于结局；病例对照的 OR 在合适抽样下可估计相应比值，但必须核对对照来源和抽样方案；横断面通常不能区分病因方向。
- 暴露定义、剂量单位、滞后期、累积窗口和参照水平不同，须先统一或分层；线性趋势不能未经验证外推到全剂量范围。

### 3.3 诊断、患病率与预后

- 诊断准确性研究须能构建与目标阈值对应的 2×2 数据或联合准确性估计，并核对参考标准、验证流程、阈值是否预设及排除无法验证者。
- 患病率研究须有可解释的目标总体与分母。便利样本、单中心转诊样本或仅阳性者样本不能被自动推广至一般人群。
- 发病率必须区分“指定期间新发人数/风险人群”与“事件数/人时”；反复发作不能当成独立个体。
- 预后研究须统一时间起点（如确诊、手术、出院）、预测时距和结局；开发模型、外部验证和影响研究不得混在一个性能汇总中。

## 四、医学结局的预设与提取

**就近依据：** [Cochrane Ch.3](https://training.cochrane.org/handbook/current/chapter-03)、[Ch.18 patient-reported outcomes](https://training.cochrane.org/handbook/current/chapter-18)、[Ch.19 adverse effects](https://training.cochrane.org/handbook/current/chapter-19)、[Ch.14 SoF outcomes](https://training.cochrane.org/handbook/current/chapter-14)。

### 4.1 结局地图

为每个结局建立以下字段：

| 字段 | 强制规则 |
|---|---|
| `domain` | 先定义构念，如全因死亡、疼痛、躯体功能、严重不良事件；不能先按量表名分组 |
| `definition` | 写明诊断标准、事件组成、严重度、是否首次/复发以及判定者 |
| `instrument` | 记录量表范围、方向、版本、语言与已知信效度；高分方向必须统一 |
| `metric` | 末值、基线变化、达到阈值、事件数、率或时间至事件，不得静默互换 |
| `timepoint` | 方案预设短/中/长期窗口及选点规则；同一研究多个时间点不能作为独立研究重复计权 |
| `importance` | critical / important / limited importance；应吸收患者、临床与政策相关者意见 |
| `threshold` | MID 或决策阈值及来源；无可靠阈值时明确标注不确定 |
| `hierarchy` | 同一域出现多个工具、评定者、定义或分析时的选择优先级 |

### 4.2 必须防止的结局错误

- 不依据效果大小或 P 值选择量表、时间点、亚组、阈值或分析。按预设层级选择，并记录所有可用候选。
- 不将替代结局直接解释为患者获益；单列并在 GRADE 中评价间接性。
- 不将组成不同或被常见轻微事件主导的复合结局视为等同；同时提取各组成项，检查定义与临床重要性。
- 不把“任何不良事件”“因不良事件退出”当作所有安全性的充分代表。严重、特定、罕见和长期伤害应分开。
- 不把“未报告事件”编码为“零事件”。区分已测量且为零、未测量、未报告和无法确定。
- 全因死亡通常比病因特异死亡更少受分类影响；若使用病因特异结局，核对盲法、判定委员会和竞争事件。
- 患者报告结局须核对工具有效性、最小重要差异、缺失模式和评定时是否知晓分组。

## 五、效应量选择

**就近依据：** [Cochrane Ch.6](https://training.cochrane.org/handbook/current/chapter-06)、[Ch.10](https://training.cochrane.org/handbook/current/chapter-10)、[Cochrane DTA Handbook v2.0](https://www.cochrane.org/authors/handbooks-and-manuals/handbook-systematic-reviews-diagnostic-test-accuracy)、[Cochrane Prognosis tools](https://methods.cochrane.org/prognosis/tools)。

### 5.1 通用选择表

| 数据/问题 | 首选候选 | 操作规则与禁忌 |
|---|---|---|
| 二分类事件 | RR、OR、RD | RR 易解释；病例对照或逻辑回归常给 OR。结局常见时不得把 OR 称为 RR。RD 与基线风险强相关。相对效应应配绝对风险差及明确时间窗 |
| 临床决策表达 | 每 1000 人绝对差、必要治疗/伤害人数 | 从合适的基线风险和相对效应推导；给 CI、时间范围和基线风险来源。不要跨人群搬用 NNT/NNH |
| 同一连续量表 | MD | 统一单位和方向；基线变化与末值可在适当条件下合并，但须核对量纲、相关性和分析策略 |
| 同一构念、不同量表 | SMD | 仅当工具确实测同一构念；统一方向。报告量表异质性，并尽可能换算到熟悉量表或 MID；SMD 受研究内 SD 差异影响 |
| 有序结局 | 比例优势 OR 或预设二分结果 | 使用比例优势模型前检查假设；事后选择切点会引入选择性报告 |
| 计数/复发事件 | 率比或能处理复发相关性的模型 | 区分事件数、发生过事件的人数和人时；不可把多次事件当独立患者 |
| 时间至事件 | HR 或指定时点风险/生存差 | 明确时间零点、删失与比例风险假设；HR 不是 RR。图形重建须注明算法和假设 |
| NRSI 因果效果 | 调整后 RR/OR/HR/率比等 | 优先提取最接近预设 estimand 与调整集的模型；记录所有调整变量。未调整与调整估计不在主分析中混合 |
| 患病率 | 比例及精确/合适 CI | 保留分子、分母、时间和病例定义；极端比例或小样本使用适合二项分布的模型，不机械依赖正态近似 |
| 发病率 | 累积风险或发病率 | 两者分母与含义不同，不能直接混合；动态队列通常报告人时率 |
| 诊断准确性 | 灵敏度与特异度联合；LR+/LR− | 阈值必须对齐。预测值随患病率改变；不应分别做普通单变量 Meta 后忽略相关性/阈值效应；DOR 不足以单独支持临床解释 |
| 总体预后 | 指定时点风险、生存率或累积发生率 | 有竞争风险时优先累积发生函数等合适估计；简单 Kaplan–Meier 可能高估目标事件风险 |
| 预后因子 | 调整后 HR/RR/OR | 按时间窗、尺度（每单位/每 SD/分类）和调整集分层；不能把 HR、OR、RR 当同一量直接平均 |
| 预测模型 | 校准 O:E、校准斜率、C-statistic/AUC、Brier 等 | 校准和区分度回答不同问题；指定时间窗与验证类型。性能汇总通常需要专门变换和多层模型 |

### 5.2 换算与方向

- 比值效应在 Meta 中通常用自然对数尺度；保存 `log(effect)` 和 `SE`，回报时再反变换。
- 单位换算只能用于同一物理量；若量表构念或版本不同，不能因数值范围相似而合并。
- 所有效应方向须在数据字典中固定，例如 RR < 1 是否有利、MD < 0 是否有利。森林图与文字必须一致。
- 从 CI 推算 SE、从 P 值推算统计量、从中位数估均值、从图形读数均属于派生数据；做敏感性分析并由第二人复算。
- 零事件处理依事件稀有度、组间平衡和方法假设决定。不得默认给所有格子加 0.5；双零研究对 RR/OR 的相对效应不提供方向信息，但仍可提供绝对发生信息。

## 六、能否合并及如何综合

**就近依据：** [Cochrane Ch.10](https://training.cochrane.org/handbook/current/chapter-10)、[Ch.12 other synthesis methods](https://training.cochrane.org/handbook/current/chapter-12)、[Ch.15 interpretation](https://training.cochrane.org/handbook/current/chapter-15)。

### 6.1 定量合并前的六道门

每个综合组逐项回答；任一关键项为“否”时先分层或不用 Meta：

1. **同一决策问题：** 人群、干预/暴露、比较和使用场景足够一致。
2. **同一 estimand：** assignment、adherence、as-treated、总效应或直接效应没有混淆。
3. **同一结局构念与时间窗：** 定义、阈值和测量方法可解释地相容。
4. **效应量可交换：** 数学换算合法，且换算后临床含义一致。
5. **设计与偏倚可解释：** 研究不是因不同设计机制而估计不同量；严重偏倚不会被平均掩盖。
6. **统计依赖已处理：** 多臂、整群、交叉、重复时间点、多部位或多结局相关性不会造成重复计权。

### 6.2 模型与异质性

- 固定效应与随机效应是关于真实效应分布的假设，不是由异质性检验 P 值自动选择。
- 随机效应结果须报告 `tau²`，研究数和数据允许时报告预测区间；汇总均值的 CI 不能表示研究间效应分布宽度。
- `I²` 受研究精度和数量影响，不得用单一阈值决定合并、降级或模型。结合效应方向、大小、CI 重叠、`tau²`、预测区间和临床/方法差异判断。
- 研究很少时，异质性方差、预测区间和小样本校正不稳定；必须降低解释强度并由统计人员复核方法。
- 亚组和 Meta 回归应基于少量、预设、具机制依据的效应修饰因素；比较“一个亚组显著、另一个不显著”不是交互证据。
- 敏感性分析至少覆盖高偏倚研究、派生数据、效应量选择、相关系数/ICC、零事件方法和固定/随机效应等关键判断；不得用反复试模寻找满意结论。

### 6.3 不应强行 Meta 的情形

- 只有一个研究，或研究估计的不是同一问题/效应。
- 结局定义、阈值、时间零点或随访时距不可调和。
- 严重临床异质性或因果结构差异使“平均效应”没有决策含义。
- 数据不足以重建正确方差、聚类或配对结构。
- 偏倚机制和方向在研究间根本不同，合并会掩盖问题。

不用 Meta 时，采用结构化的其他综合方法：按问题和设计制表，报告每项效应与 CI、偏倚和证据缺口，明确综合规则；禁止只做“多少项显著”的投票计数。

## 七、何时转向专门方法

**就近依据：** [Cochrane Handbook topic index](https://training.cochrane.org/handbook/current)、[Cochrane DTA](https://www.cochrane.org/authors/handbooks-and-manuals/handbook-systematic-reviews-diagnostic-test-accuracy)、[Cochrane Prognosis](https://methods.cochrane.org/prognosis/tools)、[JBI current appraisal tools](https://jbi.global/critical-appraisal-tools)、[PRISMA extensions](https://www.prisma-statement.org/extensions)。

出现以下任一触发器，Codex 应停止套用普通两组干预 Meta 模板，输出转向建议并请求相应专家复核：

本技能提供三个边界明确的 specialist runner，详见 `specialist-medical-models.md`：单阈值诊断准确性双变量模型、带显式采样协方差的两阶段线性剂量—反应，以及连通对比网络的一致性模型。它们不是完整 HSROC/非线性剂量—反应/网络排名平台；超出输入契约时继续停止并请求专家复核。

| 触发器 | 转向 |
|---|---|
| 同时比较三个及以上干预，需间接比较或排名 | 网络 Meta；先验证传递性、网络连通和不一致，配置 NMA 统计专家 |
| 诊断准确性、多个阈值、配对检测比较 | Cochrane DTA v2.0；双变量/HSROC；QUADAS-3；PRISMA-DTA |
| 总体预后、预后因子、预测模型 | Cochrane Prognosis；分别使用相应设计、RoB 和 GRADE 路线；模型用 CHARMS/PROBAST+AI |
| 患病率/发病率或比例接近 0/1、强抽样差异 | PERSyst/JBI 专门方法；抽样、病例定义、设计效应与代表性优先 |
| 暴露—健康结局，尤其环境/职业暴露 | PECO + ROBINS-E/JBI 病因风险；剂量反应、混杂和滞后期专家 |
| 测量属性、PROM 工具选择 | COSMIN；不要把信度、效度、反应度混成一般效应 |
| 罕见事件、药物警戒、零事件多 | 安全性/罕见事件方法；区分信号检测与风险量化 |
| IPD、个体层效应修饰或统一重分析 | IPD Meta；需数据治理、去标识化、缺失数据和分层模型专长 |
| 中断时间序列、受控前后、阶梯楔形、交叉或整群设计 | 对应设计的效应提取、方差和 RoB 变体；不能按独立个体平行 RCT 处理 |
| 剂量反应、非线性暴露、复杂干预组成 | 剂量反应/组件模型或复杂干预方法；预设节点和机制 |
| 竞争风险、多状态过程、重复事件 | 生存/事件史专门模型 |
| 定性、混合方法、经济评价、范围综述 | JBI 对应章节或其他预先选定的专门手册；不要强行生成效应量 |
| 聚合数据不足、需可靠亚组交互或统一时间结局 | 评估 IPD 可行性；不能用研究间亚组差异冒充个体层交互 |

## 八、不可自动化的判断与人工复核

**就近依据：** [Cochrane Ch.4](https://training.cochrane.org/handbook/current/chapter-04)、[Ch.5](https://training.cochrane.org/handbook/current/chapter-05)、[Ch.7](https://training.cochrane.org/handbook/current/chapter-07)、[JBI Manual 2024](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true)。

### 8.1 必须由人作最终决定

- 问题是否对应真实临床/政策决策，以及比较、时间范围和目标效应是否正确。
- 哪些结局对患者至关重要，MID/决策阈值是多少，替代结局是否足够可信。
- 研究在临床与因果上能否交换，是否存在不能被统计模型消除的异质性。
- 暴露/干预问题的关键混杂域、中介、碰撞变量、并发干预和偏倚可能方向。
- 从多个模型、时间点、阈值或量表中选择哪个结果最符合方案，而非最有利。
- 是否应合并、是否应解释亚组/剂量反应、以及结果能否外推到目标人群。
- 偏倚判断、GRADE 各域、升级/降级和最终确定性；详见配套文件。
- 临床意义、收益—伤害平衡和实践建议。系统综述本身通常提供证据，不应越权生成指南推荐。

### 8.2 强制人工复核点

至少两名人员独立完成或逐项核验以下高风险环节，并保留分歧解决记录：

1. 研究筛选与同一研究多报告的链接/去重。
2. 主要结局、主要比较、关键时间点和数值提取。
3. 单位换算、SE/SD 推导、图形数字化、HR 重建及多臂/聚类校正。
4. NRSI 的目标试验、混杂域和所选调整模型。
5. RoB、GRADE 及任何从算法建议作出的人工改判。
6. 主分析代码、数据行数、效应方向、反变换和关键图表。
7. 摘要、结论与数值表的一致性，特别是伤害、绝对效应和不确定性。

自动化可做去重候选、格式校验、公式复算和异常值提示，但不得自动裁决以上事项。AI 参与过筛选、提取、翻译或判断时，应记录模型/版本、提示词用途、人工监督和错误处理流程。

## 九、最小交付与审计记录

**就近依据：** [PRISMA 2020 checklist](https://www.prisma-statement.org/prisma-2020-checklist)、[PRISMA extensions](https://www.prisma-statement.org/extensions)、[Cochrane reporting guidance](https://training.cochrane.org/handbook/current/chapter-iii)。

每个完成的医学证据综合至少保存：

- 已注册/带日期的方案及所有修订。
- 问题卡、结局地图、效应量字典和综合组定义。
- 检索日期、完整策略、数据库/注册平台、去重和筛选日志。
- study–report 映射，避免同一队列或试验重复计权。
- 原始提取值、派生公式、单位、方向、调整变量、数据来源位置和双人复核状态。
- 每个分析的数据集、代码、软件/包版本、随机种子及可复现输出。
- 不合并理由、排除研究理由、偏倚表、GRADE Evidence Profile/SoF 与脚注。
- PRISMA 2020 流程图和清单；若适用，加 PRISMA-DTA、PRISMA-IPD、PRISMA-S 等正式扩展。不要使用仍“在开发中”的扩展作为已发布标准。

## 十、来源与更新

以下均为本文件规则的主要来源；内容是蒸馏而非原文复制。

| 来源/机构 | 适用范围与本文件用途 | URL | 版本/状态（核验时） | 访问日期 | 更新提醒 |
|---|---|---|---|---|---|
| Cochrane Handbook for Systematic Reviews of Interventions，Cochrane | 干预综述全流程；问题、结局、效应量、Meta、解释、伤害、NRSI、非标准设计、IPD | [当前手册](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current)，重点：[Ch.3](https://training.cochrane.org/handbook/current/chapter-03)、[Ch.6](https://training.cochrane.org/handbook/current/chapter-06)、[Ch.10](https://training.cochrane.org/handbook/current/chapter-10)、[Ch.15](https://training.cochrane.org/handbook/current/chapter-15)、[Ch.19](https://training.cochrane.org/handbook/current/chapter-19)、[Ch.23](https://training.cochrane.org/handbook/current/chapter-23)、[Ch.24](https://training.cochrane.org/handbook/current/chapter-24)、[Ch.26](https://training.cochrane.org/handbook/current/chapter-26) | 主页面 Version 6.5 (2024)；在线章节可能有后续局部更新 | 2026-08-02 | 每次新综述核对主版本及目标章节“last updated”；版本变化时复核规则 |
| JBI Manual for Evidence Synthesis，JBI | 综述类型路由；有效性、病因/风险、定性、混合方法、经济和范围综述 | [2024 current PDF](https://jbi-global-wiki.refined.site/download/attachments/355599504/JBI%20Manual%20for%20Evidence%20Synthesis%20Nov%202024.pdf?download=true)；[JBI appraisal tools](https://jbi.global/critical-appraisal-tools) | 2024 版手册；部分量化 appraisal tools 已在 2025–2026 更新 | 2026-08-02 | 启动项目前、投稿前及至少每 6 个月检查手册与 appraisal tools；不要沿用旧附录表替代新版工具 |
| Cochrane Handbook for Systematic Reviews of Diagnostic Test Accuracy，Cochrane Screening and Diagnostic Test Methods Group | 诊断准确性问题、2×2 数据、双变量/HSROC、异质性 | [官方手册页](https://www.cochrane.org/authors/handbooks-and-manuals/handbook-systematic-reviews-diagnostic-test-accuracy) | Version 2.0，updated July 2023 | 2026-08-02 | 诊断项目启动时核对手册版本；RoB 工具另查 QUADAS-3 当前版 |
| Cochrane Prognosis Methods Group，Cochrane | 总体预后、预后因子和预测模型的专门方法与工具路由 | [Tools](https://methods.cochrane.org/prognosis/tools)；[FAQ](https://methods.cochrane.org/prognosis/faq) | 在线资源持续更新；部分 handbook chapters 仍为 draft/建设中 | 2026-08-02 | 每次预后综述核对 tools/FAQ；不要把干预综述模板直接套用 |
| PERSyst（JBI Scientific Committee 在 2024 Manual 的 External Methodological Guidance 中采用） | 患病率、发病率及比例综述方法 | [PERSyst](https://persyst.group/) | 持续发展；PRISMA-Prev 与 GRADE prevalence 等项目仍在推进 | 2026-08-02 | 项目启动时核对发布物；PRISMA 官网仍将 prevalence extension 列为开发中时，不称其为正式扩展 |
| PRISMA Executive | 系统综述报告；正式扩展路由 | [PRISMA 2020](https://www.prisma-statement.org/prisma-2020)、[Checklist](https://www.prisma-statement.org/prisma-2020-checklist)、[Extensions](https://www.prisma-statement.org/extensions)、[PRISMA-DTA](https://www.prisma-statement.org/dta) | PRISMA 2020；扩展列表动态更新 | 2026-08-02 | 投稿/发布前重新检查扩展状态；PRISMA 2020 正在规划 AI 相关部分更新 |
| GRADE Working Group | 效应阈值、证据确定性与结果表达；具体规则见配套文件 | [GRADE Book](https://book.gradepro.org/) | 官方 Book 持续补章，计划于 2026 年底完全替代旧 Handbook | 2026-08-02 | 每次 GRADE 前检查目标章节最近修改日期，并与配套文件同步 |
| ROBINS-E Development Group / riskofbias.info | 环境、职业、行为等非随机暴露研究偏倚路线 | [ROBINS-E](https://www.riskofbias.info/welcome/robins-e-tool) | Version 24 March 2024，follow-up studies | 2026-08-02 | 确认研究设计是否在工具范围；新版本出现时更新路由 |
| COSMIN Initiative | 测量工具/患者报告结局测量属性综述 | [COSMIN systematic review guideline](https://www.cosmin.nl/tools/guideline-conducting-systematic-review-outcome-measures/)；[PRISMA-COSMIN](https://www.prisma-statement.org/cosmin) | COSMIN Manual v2；PRISMA-COSMIN for OMIs 2024 | 2026-08-02 | 测量学项目启动时核对工具和手册版本 |

### 更新触发器

若出现以下任一情况，先更新本文件再执行新项目：Cochrane 主手册/目标章节换版；JBI 发布新版 Manual 或目标设计新版 appraisal tool；GRADE Book 目标章节新增/换版；PRISMA 扩展转为正式发布；DTA/预后/患病率方法或工具更新；分析软件默认方法发生实质改变。
