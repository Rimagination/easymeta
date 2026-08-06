# 植物生态与生物多样性 Benchmark Casebook

本 casebook 把已核验的重磅论文转为能力测试，不把期刊声望当作方法正确性的证明。每次复现先读取论文、补充材料、数据和代码的实际版本；本文件只规定应检验的能力与失败条件。

## 目录

- [使用方法](#使用方法)
- [机器验收现状](#机器验收现状)
- [能力覆盖矩阵](#能力覆盖矩阵)
- [个案契约](#个案契约)
- [验收层级](#验收层级)

## 使用方法

1. 选择与目标数据层级最接近的基准。
2. 先独立填写 `synthesis_route_template.json`，再看原论文路线。
3. 冻结 estimand、独立单位、依赖和预期输出；不要用原论文结果反向调参。
4. 将测试标为 `exact_reproduction`、`conceptual_reimplementation`、`router_rejection` 或 `modern_reanalysis`。
5. 保存数据/代码版本、获取日期、许可证、校验和、运行环境和与原结果的差异。
6. 通过条件是方法契约和失败防护正确，不是必须复现相同显著性。

## 机器验收现状

`tests/ecology_benchmark_scenarios.json` 将首批 8 个案例族落实为 24 个机器场景，每族至少一个正向和两个拒绝案例。运行：

```text
python scripts/validate_ecology_benchmarks.py tests/ecology_benchmark_scenarios.json
python tests/run_ecology_benchmarks.py
```

当前 24 个场景均是 `synthetic` 的 `conceptual_reimplementation` 或 `router_rejection`：它们检验 CVR 数值、共享对照路由、原始生物多样性契约、析因交互、多功能性、纵向恢复、系统发育矩阵和二阶综合停止规则，但该合成套件内部的 `verified_source_replications=0` 必须原样报告。论文数据的来源复现另由 `tests/source_reproduction_cases.json` 管理；截至 2026-08-05，该独立清单有 Cheng 2024、Gonçalves-Souza 2025 与 Keck 2025 三个 `verified targeted_reproduction`，Atkinson 2022 因公开 v1 与论文 oracle 冲突而 `blocked`。两套计数不得相加后伪装成“28 篇复现”。

## 能力覆盖矩阵

| ID | 研究类型 | 首要能力门 | 当前能力形态 |
|---|---|---|---|
| `BENCH-CHEN-2025` | 已有 Nature 锚点 | 保持既有端到端基线 | regression anchor |
| `BENCH-KECK-2025` | Nature 全球人类压力综合 | α 与 composition/homogeneity 分流、空间配对依赖 | targeted reproduction + modern audit |
| `BENCH-SHAW-2025` | Nature 全球遗传多样性 Meta | 时间/指标桥接、多层依赖、因果语言 | modern audit |
| `BENCH-CHENG-2024` | 正式多层 Meta | 共享对照 `V`、差分效应 | conceptual + numerical |
| `BENCH-LI-2025` | 多维 β 多样性 Meta | 多变量、嵌套、RVE | specialist route |
| `BENCH-GONCALVES-2025` | 原始群落数据综合 | α/β/γ、Hill 数、稀释 | raw-data route |
| `BENCH-ATKINSON-2022` | 正式 Meta | `lnRR + lnCVR` | effect-size gate |
| `BENCH-HONG-2022` | 析因实验 Meta | 正式交互效应 | contrast gate |
| `BENCH-CROUZEILLES-2016` | 森林恢复 Meta | 空间伪重复、尺度、bootstrap | modern reanalysis |
| `BENCH-MORENO-2017` | 恢复生态 Meta | 派生恢复债、非线性、参考状态 | assumption gate |
| `BENCH-MORI-2020` | 分解 Meta | 共享处理、多结局依赖 | covariance gate |
| `BENCH-LEFCHECK-2015` | 跨实验综合 | 多功能性、多阈值 | estimand gate |
| `BENCH-ISBELL-2015` | 跨实验纵向综合 | AR(1)、抗性/恢复力 | router rejection |
| `BENCH-HOOPER-2012` | 跨 Meta/多分析综合 | second-order/cross-meta | router rejection |
| `BENCH-CARDINALE-2006` | 经典 BEF Meta | 多 estimand、非线性丰富度 | conceptual reanalysis |
| `BENCH-DUFFY-2017` | 观察性多地点综合 | 调整效应、混杂、关联边界 | causal-language gate |
| `BENCH-WAN-2020` | 多营养级 Meta | 多层、多响应、路径分析 | specialist route |
| `BENCH-DAINESE-2019` | 原始数据层级综合 | 路径模型，不误标普通 Meta | router rejection |
| `BENCH-VELLEND-2013` | 长期植物群落综合 | 时间变化率、长期重复样地 | longitudinal route |

## 个案契约

### BENCH-CHEN-2025：既有 Nature 锚点

- 来源：[Nature article](https://www.nature.com/articles/s41586-024-08407-8)；[Figshare data](https://doi.org/10.6084/m9.figshare.27316062)。
- 产品与目标：植物多样性对生产力的 Meta，且把净生物多样性效应分解为 complementarity 与 selection；这些分解项、时间趋势和功能/系统发育 moderators 是不同 estimand/层级，不是可自由堆叠的独立行。
- 依赖：实验、研究、时间、响应和同一分解恒等式产生的效应相关；必须先核对效应公式、方差和共享单作参照。
- 能力门：冻结 NBE/complementarity/selection 定义与方向；记录 richness、phylogenetic/functional diversity 的尺度支持；按独立实验而非效应行判断 moderator 信息量；机制语言与统计分解边界一致。
- 红旗：不得因 Nature 发表而继承模型默认；不得把 complementarity 和 selection 当独立复制，或从观察性 moderator 关系直接推出机制因果。数据版本变化时建立新 fixture，不覆盖历史基线。

### BENCH-KECK-2025：全球人类压力与生物多样性

- 来源：[Nature article](https://www.nature.com/articles/s41586-025-08752-2)；[Zenodo release](https://doi.org/10.5281/zenodo.14608770)。
- 产品与 estimand：跨生态系统综合，至少分开 local diversity、spatial homogeneity 和 composition shift；三者的零点、方向、样本支持和自然解释不同。
- 依赖与尺度：composition/homogeneity 来自站点间距离，pairwise distances 不是独立样本；压力、类群、研究类型与 spatial scale 共同影响外推。预计算距离效应仍必须触发 `community_composition`。
- 能力门：契约强制 component/dimension/metric、grain/extent、距离定义、站点布局、独立 study 和抽样协方差状态；现代审计比较加权与非加权、研究内异质性和 residual small-study-effect 路线。
- 红旗：原文平均每研究效应数较少不能证明研究内依赖可忽略；非加权混合模型不是生态 Meta 默认；funnel、fail-safe 或 P-curve 不能共同升级为“无发表偏倚”证明。
- 来源复现状态：`verified targeted_reproduction`。冻结 Zenodo `14608770` v1.0、Git commit `5acdbde`、release SHA-256 `63ee7b...e0d8`，从 `data/data.json` 执行 `PBL_stats.R` 的三个全局截距模型；3,667 个比较、2,133 篇文章和 22 项计数/估计/区间/收敛/Hessian oracle 全部通过。没有 lockfile/container，论文与仓库的 R 版本记录不一致，所以整篇和原环境 exact reproduction 仍为 `HOLD`。

### BENCH-SHAW-2025：全球遗传多样性变化

- 来源：[Nature article](https://www.nature.com/articles/s41586-024-08458-x)；[Zenodo data/code](https://doi.org/10.5281/zenodo.13903787)。
- 产品与 estimand：跨时间的种群内遗传多样性变化；必须保存原遗传指标、marker、估计方法、时间间隔、世代长度、物种/种群和 Hedges' g* 桥接依据。
- 依赖：paper、species、population、metric/marker 和重复时间比较可交叉；只加 paper 随机效应不能自动解决 species/phylogeny 与共享数据。保护措施 moderator 属研究间观察性比较。
- 能力门：验证年份→世代转换及不确定性、指标方向和尺度、极端值预设影响诊断、paper/species/phylogeny 候选结构、先验敏感性和 prediction target。
- 红旗：不得因为个案影响大就按结果删除；不得把弱信息先验、95% 区间不跨零或“未检出发表偏倚”当普遍稳健证明；管理行动关联不自动是干预因果效应。

### BENCH-CHENG-2024：共享对照与差分生物多样性效应

- 来源：[Nature Communications article](https://www.nature.com/articles/s41467-024-48876-z)；[data/code](https://doi.org/10.6084/m9.figshare.24953433)。
- 产品与数据单位：正式 Meta；实验/研究中的处理—共同单作对照比较。
- estimand：入侵抵抗 `NBE = ln(Xmono/Xmix)`，正值表示混合群落抵抗更强；环境变化的调节效应为 `ΔNBE = NBE_manipulated - NBE_ambient`。居民生产力等其他结局另行定义，不得混入。
- 依赖与模型：多个比较共享对照；需要非对角采样 `V`、研究/实验层级和多层 Meta 回归。
- 能力门：`effect_id` 对齐、`V` 对角一致、独立簇计数、leave-one-cluster-out、相关参数敏感性。
- 红旗：复制共同对照为独立信息；只加入 study 随机截距而不处理采样协方差。

### BENCH-LI-2025：多维 β 多样性

- 来源：[Nature Communications article](https://www.nature.com/articles/s41467-025-66574-2)；[code/data](https://doi.org/10.6084/m9.figshare.30304906)。
- 产品与数据单位：正式 Meta；研究内多个处理—对照比较和多个多样性维度。
- estimand：全球变化对分类、功能和系统发育 β 多样性的经小样本修正 LRR；冻结修正版本和二阶 Delta 方差方法。
- 依赖与模型：研究/对照嵌套、跨维相关；多变量多层模型与按独立研究聚类的稳健推断。
- 能力门：必须触发 `multidimensional_biodiversity`，保留维度身份、共享对照和 RVE 有效自由度。
- 红旗：分别拟合三个维度后用 CI 重叠声称维度差异；把效应行数当研究数。

### BENCH-GONCALVES-2025：碎片化景观中的 α/β/γ 多样性

- 来源：[Nature article](https://www.nature.com/articles/s41586-025-08688-7)；[GitHub](https://github.com/thiago-goncalves-souza/ms-biodiversity-loss-fragmented-landscapes)；[Zenodo](https://doi.org/10.5281/zenodo.14885581)。
- 产品与数据单位：原始群落矩阵综合，不是已计算 `yi/vi` 的普通 Meta。
- estimand：规定 grain/extent 下的 α、β、γ 多样性及 Hill 数；区分物种损失和周转。
- 依赖与模型：样地、研究、空间配对及同一矩阵生成的多个 q/分量相关。
- 能力门：必须触发 `raw_community_matrix`；验证 taxonomy、effort、稀释/覆盖度、空间对依赖和零值政策。
- 红旗：把所有空间配对当独立；在不同 effort 或 extent 下直接比较丰富度。

### BENCH-ATKINSON-2022：均值与变异性双路线

- 来源：[Ecology Letters full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9320827/)；[OSF data/code](https://doi.org/10.17605/OSF.IO/4AUCP)。
- 产品与数据单位：正式恢复生态 Meta；处理/恢复地点相对参考或受损状态的比较。
- estimand：生物多样性平均水平与相对变异性，分别用均值比和 CV 比路线。
- 依赖与模型：同研究多个结局/比较、参考状态和分类群。
- 能力门：`lnRR` 与偏倚校正 `lnCVR` 使用不同公式和方差；方向与自然尺度解释均可审计。
- 红旗：把 CV 变化全部解释为稳定性机制；均值跨零仍计算 `lnCVR`。

### BENCH-HONG-2022：生物多样性×环境变化交互

- 来源：[Ecology Letters full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9300022/)；[Figshare data](https://doi.org/10.6084/m9.figshare.16947451.v1)。
- 产品与数据单位：来自析因生物多样性实验的正式综合。
- estimand：环境变化前后的 `NBE_A/NBE_M` 及相关效应之差 `ΔNBE`；另有 BE 斜率和部分原始数据的 complementarity/selection 分解，必须分成不同估计量家族。
- 依赖与模型：四个析因单元、共享实验/区组、多个功能和时间点。
- 能力门：必须触发 `factorial_interaction`；把 `ΔNBE` 视为所选效应尺度上的交互/差分，传播相关效应之差的方差。只有获得四个原始析因单元时才使用通用四单元对比公式。
- 红旗：联合处理相对对照显著就称“协同”；遗漏一个析因单元仍构造正式交互。
- 来源复现状态：`HOLD/NOT_RUN`。Figshare v1 只有图 2–5 的结果/绘图表，没有论文核心 1997 个 NBE、469 个 BE slope、抽样方差或分析代码；可核对 `-0.222` 等结果表身份，但不能重新拟合核心模型。正文把 `e^0.360` 解释为增加 61%，而按其定义应约为 43.3%，该冲突必须保留。

### BENCH-CROUZEILLES-2016：森林恢复、空间尺度与 bootstrap

- 来源：[Nature Communications article](https://www.nature.com/articles/ncomms11666)；[Dryad data/code](https://doi.org/10.5061/dryad.k3479)。
- 产品与数据单位：森林恢复的全球 Meta；一个景观/研究可贡献多个比较。
- estimand：恢复相对参照/受损系统的生物多样性和生态系统服务响应。
- 依赖与模型：空间伪重复、景观尺度、同研究多个比较。
- 能力门：原研究因大量比较缺失方差而采用非加权综合和每次每景观抽一个比较的 bootstrap。现代重分析必须显式独立簇和空间尺度，但不得伪造缺失 SD 或假装可做逆方差加权。
- 红旗：把原文的非加权 bootstrap 升级为所有森林 Meta 的默认；删除零值而不记录 estimand 影响。

### BENCH-MORENO-2017：恢复债和参考状态

- 来源：[Nature Communications article](https://www.nature.com/articles/ncomms14163)；[Dryad data](https://doi.org/10.5061/dryad.t5c97)。
- 产品与数据单位：恢复生态正式 Meta，包含时间与参考生态系统。
- estimand：以参考生态系统为目标，根据线性或指数恢复轨迹的曲线下面积构造恢复债；不是普通 LRR。
- 依赖与模型：同研究多个属性、生态系统和时间；非线性时间关系。
- 能力门：触发 `derived_recovery_stability`；建立参考状态、零值、方向、方差重构和非线性外推假设账本。
- 红旗：短期数据外推完全恢复时间；把不同参考状态的百分比视为天然可比；正文与仓库研究计数不一致时必须保留版本和 provenance，不可静默挑一个。

### BENCH-MORI-2020：凋落物多样性与分解

- 来源：[Nature Communications article](https://www.nature.com/articles/s41467-020-18296-w)。
- 产品与数据单位：正式 Meta；混合凋落物与单种/处理比较，包含多个分解结局。
- estimand：混合凋落物相对单种凋落物的 Hedges' d；质量损失和分解常数是不同分析产品，不可自动合并。
- 依赖与模型：同一处理/对照被多个混合或时间点重复使用，比较嵌套于研究。
- 能力门：比较嵌套于处理、处理嵌套于研究；保留结局身份，并用“每处理抽一个比较”等敏感性检验残余 pseudoreplication。若改用显式共享处理 `V`，必须说明它是现代重分析而非原论文原样复刻。
- 红旗：把每个混合组合视为独立实验；质量损失和分解常数未经桥接直接合并。

### BENCH-LEFCHECK-2015：生态系统多功能性

- 来源：[Nature Communications article and supplements](https://www.nature.com/articles/ncomms7936)。
- 产品与数据单位：跨生物多样性实验的综合，单个实验测量多个生态功能。
- estimand：平均标准化功能，以及研究内最大值 1%–99% 阈值下达到的功能数。
- 依赖与模型：同一实验的函数与阈值曲线相关。
- 能力门：触发 `ecosystem_multifunctionality`；冻结方向、最大值缩放、函数集和阈值范围。原研究拟合一组相关 GLMM，不得虚构 `vi` 后转普通 Meta。
- 红旗：从多个阈值中选择最显著一个；函数数量充当样本量。

### BENCH-ISBELL-2015：气候极端下的纵向抗性

- 来源：[Nature article](https://www.nature.com/articles/nature15374)。
- 产品与数据单位：跨草地实验的重复年份综合，不是独立效应行的普通 Meta。
- estimand：由正常年、极端年和事件后年份生产力构造的 resistance `Ω` 与 resilience `Δ`，不是常规处理—对照 LRR。
- 依赖与模型：同一实验/样地跨年重复，时间自相关和派生抗性指标。
- 能力门：触发 `one_stage_longitudinal`；时间轴、基线、事件窗口、AR 结构和实验层级均明确。
- 红旗：每个年份独立；模型只因包含 AR(1) 就被视为可移植。

### BENCH-HOOPER-2012：跨 Meta 的全球驱动比较

- 来源：[Nature article](https://www.nature.com/articles/nature11118)；[NCEAS working-group data context](https://www.nceas.ucsb.edu/workinggroups/biodiversity-and-functioning-ecosystems-translating-results-model-experiments)。
- 产品与数据单位：一组 Meta 分析/跨综合比较，不是一个统一普通模型。
- estimand：生物多样性损失与其他全球变化驱动对生态系统过程的相对影响。
- 依赖与模型：不同综合之间可能共享研究、数据集、响应和权重。
- 能力门：触发 `second_order_meta`；建立一级研究重叠图和 estimand 对齐表。
- 红旗：将每个 pooled estimate 当独立观测；忽略不同驱动的效应量与基线定义。

### BENCH-CARDINALE-2006：经典 BEF 多 estimand

- 来源：[Nature article and supplementary data](https://www.nature.com/articles/nature05202)。
- 产品与数据单位：正式生物多样性—生态系统功能 Meta。
- estimand：`LR_meanmono`（最高丰富度混合群落相对平均单作）与 `LR_bestmono`（相对最佳单作），以及部分实验的 Michaelis–Menten 丰富度—功能曲线。
- 依赖与模型：同一实验多个丰富度、功能和比较；共享单作参照。
- 能力门：estimand 分流、非线性丰富度曲线、共享参照协方差和预测范围。
- 红旗：把相对平均单作和最佳单作效应混成一个总体；线性外推超出丰富度范围。

### BENCH-DUFFY-2017：野外生物多样性和观察性调整

- 来源：[Nature article](https://www.nature.com/articles/nature23886)；[Smithsonian dataset](https://repository.si.edu/items/a1fbb8e2-a736-41e0-bc8b-9199445e79d9)。
- 产品与数据单位：多地点野外观察研究的综合。
- estimand：野外生物多样性与生态系统功能的调整后关联，不自动等于操纵实验因果效应。
- 依赖与模型：同一研究多个功能、地点和调整模型；研究间混杂控制不同。
- 能力门：调整变量/模型规格登记、同构估计分层、多结局依赖和因果语言审计。
- 红旗：将调整系数与随机实验效应无条件合并；把“控制了一些协变量”称为无混杂。

### BENCH-WAN-2020：植物多样性与多营养级响应

- 来源：[Nature Plants article](https://www.nature.com/articles/s41477-020-0654-y)；[Dryad data](https://doi.org/10.5061/dryad.12jm63z03)。
- 产品与数据单位：多营养级正式 Meta，研究可贡献多个类群和生态过程。
- estimand：植物多样性对不同营养级/功能群及相关生态过程的响应。
- 依赖与模型：研究、比较、营养级、结局和可能的路径关系。
- 能力门：多层依赖、多响应异质性、路径分析与因果假设分离。
- 红旗：路径系数被当作随机实验因果证明；多个营养级效应按行数加权。

### BENCH-DAINESE-2019：原始农业生态数据与路径模型

- 来源：[Science Advances full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC6795509/)。
- 产品与数据单位：跨研究原始田块数据的层级/路径综合，不能仅因跨研究而称普通 Meta。
- estimand：研究内标准化的服务和产量指数，以及景观简化经丰富度、丰度或均匀度影响服务与产量的直接和间接路径。
- 依赖与模型：田块嵌套 study–crop–year，多响应贝叶斯层级路径模型。
- 能力门：router 应拒绝普通 `yi/vi`，转原始数据层级/结构方程或贝叶斯路径模型专项审查。
- 红旗：从路径模型输出抽取多个系数后当独立效应再 Meta；因果图和混杂假设缺失。

### BENCH-VELLEND-2013：长期植物群落变化

- 来源：[PNAS full text and Dataset S1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3845118/)。
- 产品与数据单位：长期重复样地研究的跨研究综合。
- estimand：`ES = t^-1 ln(SR_Y2/SR_Y1)`，其中 `t` 以十年计；其他多样性和均匀度指标另行分析。
- 依赖与模型：样地嵌套研究、不同监测长度和观测间隔、重复时间点。
- 能力门：触发纵向路线；验证单位时间 LRR、论文内嵌套数据、监测长度、时间非线性和贝叶斯多层/替代权重模型。
- 红旗：短序列和长序列给同等趋势信息；把不同起止年代视为同一目标时间分布。

## 验收层级

- `L0 source integrity`：论文、补充、数据和代码身份、版本、许可证与哈希明确。
- `L1 routing`：不会把原始矩阵、纵向、交互、多功能性或 second-order 问题误送普通 runner。
- `L2 estimand`：数学定义、方向、单位、参考状态和自然尺度解释一致。
- `L3 dependence`：独立单位、共享对照、时间/空间/多结局协方差和随机结构可审计。
- `L4 computation`：在冻结输入上结果与公开实现相容，或差异有可重复解释。
- `L5 robustness`：替代相关、效应定义、尺度、参考状态、偏倚风险和模型均有敏感性分析。
- `L6 interpretation`：结论不超出设计、时间、空间、分类群和观测支持。

合成 fixture 可以通过相应的 L1–L4 方法合同，但不能自动通过 L0 的论文源完整性，也不能替代 L6 的领域专家判断。`exact_reproduction` 和 `modern_reanalysis` 只有在来源版本、许可、输入 SHA-256、运行环境、逐项数值容差和差异说明均冻结后才能标为通过；缺失公开或授权输入时状态必须是 `NOT_RUN/pending`，不能算作 PASS。
