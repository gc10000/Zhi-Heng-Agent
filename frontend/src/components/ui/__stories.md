# UI 基础组件库 Stories（T3.1）

> 全部组件零依赖手写（cva + 语义 CSS 变量，参照 shadcn-vue 模式）。样式只引用 `tokens.css` 变量，双主题自动适配。

## Button.vue

主操作按钮。variant 四种、size 两档。

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| variant | `default \| secondary \| ghost \| soft` | `default` | default=ink底bg字（主钮）；secondary=line2 边框；ghost=透明 hover panel；soft=panel 底 |
| size | `sm \| md` | `md` | sm=11.5px，md=12.5px |
| class | string | — | 追加类名（tailwind-merge 合并） |

用法：`<Button variant="default" @click="...">发送</Button>`；作为 RouterLink 时外层包 `<RouterLink>` 或用 ghost 变体。

## Badge.vue

状态徽标。用于任务状态、记录状态、VERIFIED 标记。

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| variant | `default \| success \| warning \| danger \| info` | `default` | success=ok 系（已确认/VERIFIED）；warning=warn 系（草稿）；danger=danger 系（失败）；info=accent 系（进行中/引用） |
| size | `sm \| md` | `md` | sm=10px 紧凑 |

## Card.vue / CardHeader.vue / CardContent.vue / CardFooter.vue

三段卡片：1px `--line` 边、10px 圆角、无阴影（v6 层级语言）。

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| class | string | — | 追加类名 |
| padded（Header/Content/Footer） | boolean | `true` | 关闭内边距用于自定义排版 |

用法：`<Card><CardHeader>标题</CardHeader><CardContent>…</CardContent><CardFooter>操作</CardFooter></Card>`，三段可独立使用。

## Input.vue

文本输入。聚焦光环 = `box-shadow: 0 0 0 3px color-mix(var(--accent) 12%, transparent)`（v6 composer 规范）。

| Prop | 类型 | 默认 | 说明 |
|------|------|------|------|
| modelValue | string | 必填 | v-model |
| type | string | `text` | password 等 |
| placeholder / disabled / required / maxlength / autocomplete | — | — | 原生透传 |

## ThemeToggle.vue（Phase 0 已建）

分段开关（☀ 亮 | ☾ 暗）。选中段 = `--ink` 底 `--bg` 字。内部走 `useTheme()`。

## BrandMark.vue（Phase 0 已建）

L2 水平仪 Logo。`size` prop（默认 30）。气泡 fill=var(--accent) 随主题变色。
