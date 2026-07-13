---
name: prd-product-requirement-clarifier
description: "将模糊需求澄清为可落地 PRD（场景、目标、用户、功能、前后端技术、数据库 schema、验收标准）。Use when you need PRD clarification, platform data product requirement definition, database schema draft, or MVP scope split."
argument-hint: "可选参数: product_name=<name>, domain=<industry>, stage=0|1|2, depth=lite|standard|deep, language=zh|en|bilingual, stack_preference=python|typescript|java|go|dotnet, db=postgresql|mysql|mongodb|mixed"
user-invocable: true
disable-model-invocation: false
---

# PRD Product Requirement Clarifier

## Purpose
把一句话或一段模糊业务诉求，澄清并固化为一份可交付给产品、设计、前后端和数据团队共同执行的 PRD。

## When To Use
- 你正在做平台型数据产品，但需求还停留在想法层。
- 你需要一次性补齐 PRD 的关键章节：场景、目标、人群、功能、架构、技术栈、数据库 schema、验收标准。
- 你希望先做 MVP，再规划迭代路线图。

## Inputs
- 原始需求描述 (required): 用户给的一句话或业务背景。
- product_name (optional): 产品名。
- domain (optional): 行业/业务域，例如汽车、金融、零售、制造。
- stage (optional, default 0):
  - 0 = 从零澄清
  - 1 = 已有部分 PRD，需要补全
  - 2 = 已有 PRD，需要技术深化
- depth (optional, default standard):
  - lite = 快速草案
  - standard = 标准 PRD
  - deep = 含详细数据模型、接口和非功能细化
- language (optional, default zh): zh | en | bilingual
- stack_preference (optional): python | typescript | java | go | dotnet
- db (optional): postgresql | mysql | mongodb | mixed

## Output Contract
每次执行必须输出以下结构（不得缺项）：
1. 需求摘要 (Problem Statement)
2. 业务场景与使用目的
3. 目标用户与角色分层
4. 用户旅程与关键任务流
5. 功能范围 (MVP / V1 / V2)
6. 非功能需求 (NFR)
7. 信息架构与核心页面/模块
8. 系统架构与前后端框架建议
9. 前后端技术栈与语言建议（含推荐理由）
10. 数据模型与数据库 schema 初稿
11. API 合同草案（核心接口）
12. 指标体系与埋点需求
13. 安全、权限与合规要求
14. 风险清单与约束条件
15. 里程碑计划与资源估算
16. 验收标准 (UAT + 技术验收)
17. 待确认问题清单 (Open Questions)

## Procedure
1. 识别需求完整度并打分（0-100），判断缺口位置。
2. 先提出 8-15 个高价值澄清问题，覆盖：业务目标、角色、流程、数据、集成系统、SLA、安全合规、上线边界。
3. 基于已知信息生成 PRD V0.1，并对未确定项显式标注 "Assumption"。
4. 输出两套可落地技术方案（Conservative / Progressive）：
   - 方案 A：保守、低风险、快上线
   - 方案 B：扩展性优先、长期可演进
5. 对两套方案进行加权评分：开发效率、维护成本、扩展性、团队匹配度、性能、安全。
6. 给出推荐方案与理由，并补充迁移路径。
7. 产出数据库 schema：
   - 核心实体表
   - 主键/外键
   - 索引策略
   - 约束条件
   - 审计字段 (created_at, updated_at, created_by, updated_by)
8. 补充 API 草案：REST 风格优先，定义核心 endpoint、请求/响应、错误码。
9. 产出 MVP 验收清单，确保可测试、可演示、可度量。

## Clarification Question Bank (Starter)
优先提问以下问题（按需裁剪）：
1. 这个平台数据产品最核心的业务决策是什么？
2. 第一优先服务的用户是谁？谁付费或承担 KPI？
3. 当前流程里最痛的环节在哪里？耗时和错误率是多少？
4. 你希望替代旧系统，还是叠加在现有系统之上？
5. 数据从哪些源头来？批处理、流式还是混合？
6. 数据刷新频率与实时性要求是什么？
7. 是否存在多租户、组织隔离、行列级权限要求？
8. 需要对接哪些外部系统（CRM/ERP/埋点/消息系统）？
9. 峰值并发、数据量级、响应时间目标是多少？
10. 可接受的数据延迟和数据质量下限是什么？
11. 合规边界是什么（个人信息、跨境、审计留痕）？
12. MVP 上线时间与团队配置如何？
13. 哪些功能必须首发，哪些可延后？
14. 失败回滚和灾备恢复目标是什么？
15. 成功指标如何定义（业务和技术）？

## PRD Skeleton Template
```markdown
# <Product Name> PRD

## 1. 需求背景与目标
- 问题定义:
- 业务目标 (OKR/KPI):
- 预期收益:

## 2. 使用场景
- 场景 A:
- 场景 B:
- 触发条件:
- 失败场景:

## 3. 用户与权限
- 角色列表: Admin / Operator / Analyst / Viewer
- 角色权限矩阵:

## 4. 功能范围
- MVP:
- V1:
- V2:
- Out of Scope:

## 5. 交互与页面模块
- 页面/模块清单:
- 关键用户流程:

## 6. 技术方案
- 前端框架:
- 后端框架:
- 前端语言:
- 后端语言:
- 服务拆分:

## 7. 数据模型与数据库 Schema
- 实体关系概览:
- 表结构草案:
- 索引与约束:

## 8. API 草案
- 鉴权方式:
- 核心接口:
- 错误码规范:

## 9. 非功能需求
- 性能:
- 可用性:
- 安全:
- 可观测性:

## 10. 验收标准
- UAT 场景:
- 技术验收:
- 指标验收:

## 11. 里程碑与风险
- 版本计划:
- 资源估算:
- 风险与缓解:

## 12. Open Questions
- Q1:
- Q2:
```

## PRD Table Template (Recommended)
```markdown
# <Product Name> PRD (Table Version)

## A. 需求概览
| 模块 | 内容 | 备注 |
|---|---|---|
| 产品名称 |  |  |
| 业务域 |  |  |
| 问题定义 |  | 当前痛点和损失 |
| 目标指标 |  | 例如时效、成本、转化 |
| 范围边界 |  | In Scope / Out of Scope |

## B. 使用场景与目标
| 场景编号 | 角色 | 触发条件 | 任务目标 | 当前做法 | 期望改进 |
|---|---|---|---|---|---|
| SC-01 |  |  |  |  |  |
| SC-02 |  |  |  |  |  |

## C. 用户与权限矩阵
| 角色 | 关键职责 | 查看权限 | 编辑权限 | 审批权限 | 数据范围 |
|---|---|---|---|---|---|
| Super Admin |  |  |  |  |  |
| Tenant Admin |  |  |  |  |  |
| Analyst |  |  |  |  |  |
| Operator |  |  |  |  |  |
| Viewer |  |  |  |  |  |

## D. 功能清单与版本规划
| 功能ID | 功能名称 | 用户价值 | 优先级(P0/P1/P2) | 版本(MVP/V1/V2) | 验收标准 |
|---|---|---|---|---|---|
| F-001 |  |  |  |  |  |
| F-002 |  |  |  |  |  |

## E. 页面与交互模块
| 页面/模块 | 入口角色 | 关键组件 | 关键操作 | 依赖接口 | 埋点事件 |
|---|---|---|---|---|---|
| 首页总览 |  |  |  |  |  |
| 指标中心 |  |  |  |  |  |

## F. 前后端技术方案
| 维度 | 方案A(保守) | 方案B(进取) | 选择建议 | 备注 |
|---|---|---|---|---|
| 前端框架 |  |  |  |  |
| 后端框架 |  |  |  |  |
| 前端语言 |  |  |  |  |
| 后端语言 |  |  |  |  |
| 网关鉴权 |  |  |  |  |
| 部署方式 |  |  |  |  |

## G. 数据模型与数据库 Schema
| 表名 | 用途 | 主键 | 关键字段 | 外键关系 | 索引建议 | 约束 |
|---|---|---|---|---|---|---|
| tenants | 租户主数据 | id | tenant_code, tenant_name, status | - | uniq(tenant_code) | NOT NULL |
| users | 用户主数据 | id | tenant_id, email, role | tenant_id -> tenants.id | uniq(tenant_id,email) | NOT NULL |
| metrics | 指标定义 | id | metric_code, metric_name, owner_id | tenant_id -> tenants.id | uniq(tenant_id,metric_code) | NOT NULL |
| metric_values | 指标事实 | id | metric_id, dt, dim_jsonb, value_num | metric_id -> metrics.id | idx(tenant_id,metric_id,dt) | 分区建议 |

## H. API 清单
| 接口ID | 方法 | 路径 | 用途 | 请求关键字段 | 响应关键字段 | 错误码 |
|---|---|---|---|---|---|---|
| API-001 | POST | /api/v1/auth/login | 登录 | email,password | token,user | 400/401 |
| API-002 | GET | /api/v1/metrics | 指标列表 | page,size,filters | items,total | 400/403 |
| API-003 | GET | /api/v1/metrics/{id}/values | 指标时序 | start_dt,end_dt,dims | series | 400/404 |

## I. 非功能需求(NFR)
| 维度 | 指标定义 | 目标值 | 测试方式 | 责任人 |
|---|---|---|---|---|
| 性能 | API P95 | < 2.5s | 压测 | 后端 |
| 可用性 | 月可用性 | >= 99.9% | 监控统计 | SRE |
| 安全 | 高危漏洞 | 0 | 安全测试 | 安全负责人 |
| 可观测性 | 覆盖率 | 日志/指标/链路全覆盖 | 运行检查 | 平台团队 |

## J. 里程碑与验收
| 里程碑 | 时间 | 交付物 | 进入条件 | 验收条件 | 风险 |
|---|---|---|---|---|---|
| M0 |  | 需求冻结 | 关键问题明确 | PRD评审通过 |  |
| M1 |  | MVP开发完成 | 核心功能联调完成 | UAT通过率>=95% |  |
| M2 |  | 生产上线 | 监控与回滚预案就绪 | 稳定运行2周 |  |

## K. Open Questions
| 编号 | 问题 | 影响范围 | 责任人 | 截止时间 | 状态 |
|---|---|---|---|---|---|
| Q-01 |  |  |  |  | Open |
| Q-02 |  |  |  |  | Open |
```

## Data Schema Output Example (SQL)
```sql
-- Example core tables for a generic platform data product
CREATE TABLE tenants (
  id BIGSERIAL PRIMARY KEY,
  tenant_code VARCHAR(64) UNIQUE NOT NULL,
  tenant_name VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id),
  email VARCHAR(255) NOT NULL,
  display_name VARCHAR(128) NOT NULL,
  role VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, email)
);

CREATE TABLE data_assets (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id),
  asset_name VARCHAR(128) NOT NULL,
  asset_type VARCHAR(64) NOT NULL,
  source_system VARCHAR(128),
  refresh_policy VARCHAR(64),
  owner_user_id BIGINT REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant_role ON users (tenant_id, role);
CREATE INDEX idx_assets_tenant_type ON data_assets (tenant_id, asset_type);
```

## Architecture Defaults (If User Gives No Preference)
- Frontend: Next.js + TypeScript + Tailwind CSS + ECharts
- Backend: FastAPI (Python) + SQLAlchemy + Pydantic
- Async Jobs: Celery + Redis
- DB: PostgreSQL
- Search/Analytics (optional): OpenSearch
- Deployment: Docker + GitHub Actions

## Guardrails
- 不把“假设”写成“既定事实”。
- 无法确认的数据量、并发、SLA 必须显式列入 Open Questions。
- 未经用户确认，不直接承诺特定云厂商或高成本组件。
- 功能描述必须可测试，验收标准必须可量化。

## Example Prompts
- /prd-product-requirement-clarifier 我想做一个面向销售管理层的多租户经营分析平台，请帮我把 PRD 完整化。
- /prd-product-requirement-clarifier product_name=Retail Insight Hub domain=retail depth=deep db=postgresql
- /prd-product-requirement-clarifier stage=1 language=bilingual stack_preference=typescript
