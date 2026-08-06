# 论文级来源复现层

本层回答一个比“代码能运行”更严格的问题：在明确冻结的论文、数据、代码和环境上，EasyMeta 能否重建预先声明的统计量，并把不一致诚实地判为 `BLOCKED` 或 `FAIL`？它与 `tests/ecology_benchmark_scenarios.json` 的合成方法测试分开计数。

## 结论术语

- `exact_reproduction`：从声明的起点到终点完整执行原作者路线，并通过冻结数值 oracle。只复现一个模型时不得使用此词。
- `targeted_reproduction`：复现论文中一个预先界定、可定位的模型或结果表；必须写明没有覆盖的上游处理、其他模型和图表。
- `modern_reanalysis`：在冻结公开输入上按新假设或新环境重算；结果可通过自身 oracle，但不能冒充原论文结果。
- `blocked`：已发现数据—代码—论文冲突、许可不清、缺输入或缺不可恢复环境，无法诚实完成声明范围。
- `NOT_RUN`：所需外部文件或运行时未就绪；不能计作 PASS。

只有 `exact_reproduction` 或 `targeted_reproduction` 且 `verification_status=verified` 的案例计入 `verified_source_reproductions`。

## 三层制品

1. `tests/source_reproduction_cases.json` 冻结来源记录、版本、许可状态、文件大小、远端 MD5（若有）、本地 SHA-256、执行入口、环境和逐项数值容差。
2. `scripts/materialize_source_reproductions.py` 只在显式给出 `--download` 时联网；下载后先验哈希，不把第三方数据提交进仓库，并对 ZIP 做路径穿越检查。
3. `tests/run_source_reproductions.py` 先验输入字节，再执行小型论文适配器，最后按 JSON pointer 比较分析尺度上的数值 oracle；缺文件是 `NOT_RUN`，来源冲突是 `BLOCKED`，数值越界是 `FAIL`。

外部制品默认位于仓库的 `.local/source-reproductions/raw`，也可用 `EASYMETA_SOURCE_REPRO_ROOT` 指向项目自有的受控目录。`.local/` 不进入 Git；仓库只保存可审计清单、适配器和数值 oracle。

## 首批案例状态

| 案例 | 冻结来源 | 当前结论 | 复现边界 |
|---|---|---|---|
| Cheng et al. 2024 | Figshare `24953433` v1，CC BY 4.0；三文件 MD5 与 SHA-256 | `verified targeted_reproduction` | `code.R` 16–99 行：共享单作对照 `V`、all-invader NBE 主模型及论文直接报告的 warming/drought ΔNBE；不含全部约 3500 行模型/图表 |
| Gonçalves-Souza et al. 2025 | Zenodo `14885581` release 0.1.0，CC BY 4.0；ZIP MD5/SHA-256 和关键解包文件 SHA-256 | `verified targeted_reproduction` | 从 `processed_data/diversity_of_2.csv` 重建 all-pairs α/β/γ ROM 模型；不是 raw community matrix 全流程 |
| Keck et al. 2025 | Zenodo `14608770` v1.0，GPL-3.0；release ZIP MD5/SHA-256、数据、作者模型代码、session info 与许可证 SHA-256 | `verified targeted_reproduction` | 按 `PBL_stats.R` 重建 homogeneity、composition shift、local diversity 三个全局截距混合模型，共 22 项计数/数值/收敛 oracle；不是完整 `run_all.R` 或全部图表复现 |
| Atkinson et al. 2022 | OSF `4AUCP` file revision 1；许可未声明，外部文件不再分发 | `blocked modern_reanalysis` | 公开 v1 有 9 行疑似互换 reference SE/样本量，得到 730 个效应；论文和冻结 HTML 报 739，不能用公开 v1 冒充论文复现 |

机器清单是状态真源。上表用于解释范围，若二者不一致应停止并修复文档或清单。

## 数值 oracle 的规则

- oracle 必须定位到作者代码行、表、图或补充材料，并声明分析尺度。自然尺度百分比只能作为附加方向检查，不能与 log-scale SE/CI 混用。
- 精确计数可使用零容差；连续模型量使用事先冻结的绝对/相对容差。不得因为结果未通过而事后放宽。
- 只比较显著/不显著、效应方向或图形外观，不构成数值复现。
- 适配器可以避开安装、作图和无关模型，但必须保持目标模型的数据筛选、效应定义、`V`、随机结构、估计方法和因子编码；所有偏离写入 limitations。
- 冻结输出 SHA-256 是特定验证环境的审计收据。运行器默认要求逐字节匹配；只有显式给出 `--allow-output-drift` 时，跨环境复跑才可按逐项 oracle 判定，并把输出漂移标为 `numeric_oracle_only`。这种结果不能冒充字节一致复现。

## 执行

仅验证清单结构与本地外部文件：

```text
python scripts/validate_source_reproductions.py tests/source_reproduction_cases.json
python scripts/materialize_source_reproductions.py tests/source_reproduction_cases.json --case cheng-2024 --case goncalves-2025 --case keck-2025 --require-all
```

在用户明确同意获取公开制品后，可显式下载缺失文件；已有但哈希不符的文件不会被静默覆盖：

```text
python scripts/materialize_source_reproductions.py tests/source_reproduction_cases.json --download --require-all
```

运行已启用案例：

```text
python tests/run_source_reproductions.py tests/source_reproduction_cases.json --case cheng-2024 --case goncalves-2025 --case keck-2025 --require-all --require-frozen-output
```

Windows 下若 `Rscript` 或包库不在默认位置，先设置 `R_SCRIPT` 和 `META_TEST_R_LIBRARY`。默认完整回归只验证清单合同，不自动下载或运行第三方论文数据。

## 复现报告最小字段

报告至少给出：案例 ID、论文 DOI、数据/代码固定版本、许可状态、输入 SHA-256、适配器 SHA-256、R 与关键包版本、起止边界、每个 oracle 的 expected/actual/tolerance、输出 SHA-256、PASS/FAIL/BLOCKED/NOT_RUN、偏离和未覆盖范围。若原始来源存在冲突，应同时保留“论文 oracle”和“公开数据重跑结果”，不能用其中一个覆盖另一个。

## 已知边界

- Cheng 的 Figshare 没有 lockfile；当前通过的是冻结环境下的定向模型。作者用均值、SD、n 的数值组合生成共享对照 ID，这一做法只为忠实复现，不是 EasyMeta 的通用推荐。
- Gonçalves-Souza 的完整流水线依赖未被 `renv.lock` 全部覆盖；原始 taxonomy 的 4009 个唯一字符串与论文 4006 taxa 尚未解释，所以 full raw-to-paper claim 被禁止。
- Keck 的 release 没有 lockfile/container，论文写 R 4.0.3 而仓库 `session_info.txt` 记录 R 4.1.2；当前只验证三个作者公式。其模型未按抽样方差加权，不能因数值复现成功而升级为通用方法建议。论文把 homogeneity CI 的上下界次序印反，清单保留排序后的作者模型区间。
- Atkinson 的 OSF 是可变 project 而非 registration，且没有数据/代码许可；文件 revision 与哈希虽已冻结，仍只能外部引用。其冲突案例用于证明复现层会拒绝错误 PASS。
