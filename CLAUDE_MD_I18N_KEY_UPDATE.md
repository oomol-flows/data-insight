# CLAUDE.md i18n Key 命名规范升级指南

## 问题背景

在之前的 CLAUDE.md 版本中，i18n key 的命名示例不够清晰，导致 AI 在生成 task 时会产生错误的 key 命名方式：

**问题示例**：
- 旧 prompt 示例：`title: "%process-images-to-markdown%"`
- 这会让 AI 误以为应该用**功能描述**生成 key，而不是使用**任务目录名**

**实际正确格式**：
- 应该基于任务目录名：`tasks/chart-recommender/` → `%chart-recommender-title%`
- 而不是功能描述：`%process-images-to-markdown%`

## 修改内容

### 位置
文件：`/root/.claude/CLAUDE.md`
章节：`## 🔧 Task Block Configuration` → `### task.oo.yaml Structure`
行号：约 351-386 行

### 修改前（旧版本）

```markdown
⚠️ **Title/Description - Two Valid Approaches**:

1. **Plain English** (single language):
   ```yaml
   title: "Process Images to Markdown"
   description: "Convert images using OCR"
   ```

2. **i18n Keys** (multi-language):
   ```yaml
   title: "%process-images-to-markdown%"
   description: "%convert-images-using-ocr%"
   ```
   **MUST also add translations to `oo-locales/en.json` and `oo-locales/zh-CN.json`**
```

### 修改后（新版本）

```markdown
⚠️ **Title/Description - Two Valid Approaches**:

1. **Plain English** (single language):
   ```yaml
   title: "Process Images to Markdown"
   description: "Convert images using OCR"
   ```

2. **i18n Keys** (multi-language):
   ```yaml
   title: "%{task-name}-title%"
   description: "%{task-name}-description%"
   ```

   **Naming convention**: Use `{task-folder-name}-{field}` format where `{task-folder-name}` is the directory name under `tasks/`

   **Example** (for task in `tasks/chart-recommender/`):
   ```yaml
   # task.oo.yaml
   title: "%chart-recommender-title%"
   description: "%chart-recommender-description%"
   inputs_def:
     - handle: data_table
       description: "%chart-recommender-data-table%"
   ```

   ```json
   // oo-locales/en.json
   {
     "chart-recommender-title": "Chart Recommender",
     "chart-recommender-description": "Recommend chart types based on data",
     "chart-recommender-data-table": "Data table to analyze"
   }
   ```

   **MUST add translations to both `oo-locales/en.json` and `oo-locales/zh-CN.json`**
```

## 改进说明

### 1. 明确命名规则
- **旧版**：只给出示例 `%process-images-to-markdown%`，没有说明规则
- **新版**：明确指出格式为 `{task-folder-name}-{field}`

### 2. 使用真实案例
- **旧版**：使用虚构的 `process-images-to-markdown`（看起来像功能描述）
- **新版**：使用实际存在的 `chart-recommender`（明确来自目录名）

### 3. 完整示例对照
- **旧版**：只展示 YAML 中的 key
- **新版**：同时展示：
  - YAML 中的 key：`%chart-recommender-title%`
  - JSON 中的翻译：`"chart-recommender-title": "Chart Recommender"`
  - 完整的输入输出参数示例

### 4. 强化关键概念
- 明确说明前缀来自 `tasks/` 下的**目录名**
- 展示从目录名到 key 的转换路径：`tasks/chart-recommender/` → `chart-recommender-title`

## 正确的 i18n Key 命名规则

### 规则总结

```
{task-folder-name}-{field}
```

- `{task-folder-name}`: 任务目录名（在 `tasks/` 下）
- `{field}`: 字段标识符

### 字段标识符对照表

| 位置 | 字段标识符 | 示例 key |
|------|-----------|----------|
| Task title | `-title` | `chart-recommender-title` |
| Task description | `-description` | `chart-recommender-description` |
| Input handle | `-{handle_name}` | `chart-recommender-data-table` |
| Output handle | `-{handle_name}` | `chart-recommender-recommended-charts` |

### 完整实例

假设创建任务：`tasks/my-cool-task/`

**task.oo.yaml**:
```yaml
title: "%my-cool-task-title%"
description: "%my-cool-task-description%"

inputs_def:
  - handle: input_data
    description: "%my-cool-task-input-data%"
    json_schema:
      type: string
    nullable: false

  - handle: config_options
    description: "%my-cool-task-config-options%"
    json_schema:
      type: object
    nullable: true

outputs_def:
  - handle: processed_result
    description: "%my-cool-task-processed-result%"
    json_schema:
      type: string
```

**oo-locales/en.json**:
```json
{
  "my-cool-task-title": "My Cool Task",
  "my-cool-task-description": "Does something cool with your data",
  "my-cool-task-input-data": "Input data to process",
  "my-cool-task-config-options": "Optional configuration settings",
  "my-cool-task-processed-result": "Processed output result"
}
```

**oo-locales/zh-CN.json**:
```json
{
  "my-cool-task-title": "我的酷任务",
  "my-cool-task-description": "对你的数据做一些很酷的处理",
  "my-cool-task-input-data": "要处理的输入数据",
  "my-cool-task-config-options": "可选的配置设置",
  "my-cool-task-processed-result": "处理后的输出结果"
}
```

## 升级检查清单

升级另一个 agent 镜像时，请确认：

- [ ] 替换了旧的 i18n key 示例（删除 `%process-images-to-markdown%` 等）
- [ ] 添加了明确的命名规则说明：`{task-folder-name}-{field}`
- [ ] 使用真实的任务目录名作为示例（如 `chart-recommender`）
- [ ] 展示了 YAML 和 JSON 的完整对照关系
- [ ] 说明了目录名到 key 的转换路径
- [ ] 保持了 prompt 的简洁性（没有过度膨胀）

## 预期效果

升级后，AI 在生成新任务时会：

✅ **正确行为**：
- 看到任务目录名 `tasks/my-task/`
- 生成 `title: "%my-task-title%"`
- 在 `oo-locales/en.json` 中添加 `"my-task-title": "My Task"`

❌ **避免错误**：
- 不再根据功能描述生成 key（如 `%convert-and-process-data%`）
- 不再使用不一致的命名方式
- 不再产生 i18n key 与 JSON 键名不匹配的问题

## 验证方法

升级后，可以通过以下方式验证：

1. **创建测试任务**：要求 AI 创建一个新 task
2. **检查 key 格式**：确认 task.oo.yaml 中的 key 以任务目录名为前缀
3. **检查一致性**：确认 YAML 中的 key 与 JSON 中的键名完全匹配
4. **检查完整性**：确认 en.json 和 zh-CN.json 都有对应翻译

## 相关文件

- 主配置文件：`/root/.claude/CLAUDE.md`
- 英文翻译：`/app/workspace/oo-locales/en.json`
- 中文翻译：`/app/workspace/oo-locales/zh-CN.json`
- 任务定义：`/app/workspace/tasks/{task-name}/task.oo.yaml`

---

**更新日期**: 2026-01-22
**适用版本**: OOMOL AI Programming Assistant Prompt v2+
