# Agent Launcher 现代深色视觉重构规范

日期：2026-06-25  
目标分支：`feat/agent-launcher-adaptive-ui`

## 1. 设计目标

本轮只优化 Agent Launcher 主窗口的视觉表现与交互质感，不改变已确认的目录索引、收藏、最近目录、Claude/Hermes 启动、Terminal 外观事务和 Session Monitor 行为。

目标：

1. 消除当前深色界面中白色原生控件造成的割裂。
2. 建立统一的深蓝黑、紫蓝强调色和功能色体系。
3. 用完全自定义标题栏替代 Windows 原生标题栏。
4. 让紧凑模式更像快速启动器，展开模式更像完整控制台。
5. 提升目录浏览、当前项目、启动选项和外观设置的层级感。
6. 保持高 DPI、多显示器和 Windows 11 环境下的可用性。
7. 不以强烈霓虹、跳动阴影或大面积渐变牺牲可读性。

## 2. 已确认的视觉方向

- 风格：深色现代桌面工具风。
- 品牌色：紫蓝渐变。
- 标题栏：极简磨砂自定义无边框标题栏。
- 主体：磨砂背景 + 低亮度局部紫蓝光晕。
- 卡片：10–12 px 柔和圆角卡片。
- 图标：彩色功能图标。
- 字体：Segoe UI 为主，路径和快捷键可使用 Cascadia Code。
- 按钮：主按钮实色，次按钮幽灵样式。
- 目录行：双层信息行。
- 紧凑模式：搜索优先。
- 展开模式比例：左侧目录 45%，右侧控制面板 55%。
- 右侧：当前项目、启动选项、Terminal 外观三张纵向功能卡片。

## 3. 视觉令牌

### 3.1 基础颜色

```python
COLORS = {
    "window_bg": "#090B12",
    "surface_0": "#0D1019",
    "surface_1": "#121624",
    "surface_2": "#171C2C",
    "surface_hover": "#1C2234",
    "surface_selected": "#232A45",
    "border": "#252B3D",
    "border_hover": "#343C58",
    "border_focus": "#6D5DFB",
    "text_primary": "#F4F6FB",
    "text_secondary": "#AAB1C3",
    "text_muted": "#70788E",
    "text_disabled": "#4E5567",
    "purple": "#8B5CF6",
    "purple_light": "#A78BFA",
    "blue": "#4F7CFF",
    "blue_light": "#6EA0FF",
    "claude": "#46C878",
    "claude_hover": "#58D88A",
    "hermes": "#F2A45D",
    "hermes_hover": "#FFB671",
    "favorite": "#D8B45A",
    "danger": "#FF5D6C",
    "success": "#56D98A",
    "warning": "#F4BF62",
}
```

### 3.2 渐变

主品牌渐变：

```text
#8B5CF6 → #4F7CFF
```

只允许用于：

- 自定义品牌图标；
- 选中目录左侧 2 px 光条；
- 局部背景光晕；
- 极少数焦点描边。

禁止用于整张大卡片、整条标题栏或所有按钮。

### 3.3 透明与光晕

- 主窗口背景视觉透明度：约 92–96%。
- 卡片视觉透明度：约 96–100%。
- 紫色光晕：半径约 140–180 px，峰值不透明度不超过 14%。
- 蓝色光晕：半径约 120–160 px，峰值不透明度不超过 10%。
- 光晕只出现在标题区左上和当前项目区域附近。
- 光晕不可覆盖正文，文字区域必须始终保持稳定对比度。

Tk 本身不提供真正的高斯模糊。首版使用 Canvas 渐变椭圆或预生成渐变图层模拟低亮度光晕；不得通过大量逐帧重绘制造性能问题。

## 4. 字体系统

```text
窗口标题：Segoe UI Semibold 11–12
页面标题：Segoe UI Semibold 13–14
卡片标题：Segoe UI Semibold 10–11
目录主标题：Segoe UI Semibold 10
正文：Segoe UI 9–10
辅助文字：Segoe UI 8–9
路径：Cascadia Code 8–9
快捷键：Cascadia Code Semibold 8
```

规则：

- 不使用 Emoji 作为主要界面图标。
- 彩色图标优先使用 Segoe Fluent Icons / Segoe MDL2 Assets 字形。
- 若目标系统缺失指定图标字体，必须回退到简单 Unicode 符号，不得显示空方框。
- 所有文本适配 DPI 缩放，不写死像素字体大小。

## 5. 间距与几何

基础间距单位：4 logical px。

```text
窗口外边距：12
卡片间距：10
卡片内边距：12
标题栏高度：38
搜索框高度：40
目录行高度：44
主按钮高度：40
次按钮高度：32
卡片圆角：12
按钮圆角：8
输入框圆角：10
目录行圆角：8
边框宽度：1
选中左光条：2
```

紧凑模式目标尺寸：约 `380 × 420`。  
展开模式目标尺寸：约 `820 × 560`。

尺寸可随 DPI 缩放，并受当前显示器工作区限制。窗口左上角仍固定，展开时向右和向下增长。

## 6. 自定义无边框标题栏

### 6.1 外观

标题栏高度约 38 logical px。

左侧：

- 20 × 20 品牌图标；
- `Agent Launcher`；
- 图标与标题间距 8 px。

右侧：

- 最小化；
- 最大化/还原；
- 关闭。

按钮点击区域至少 42 × 36 logical px。

标题栏底部使用 1 px 半透明紫灰分隔线，不使用整条强渐变。

### 6.2 行为

- 标题栏空白区域支持拖动窗口。
- 双击标题栏切换最大化/还原。
- 最小化按钮最小化到任务栏。
- 关闭按钮沿用现有“隐藏到托盘”行为，而不是直接退出。
- 关闭按钮悬停时使用 `danger` 背景；其他标题按钮只轻微提亮。
- 最大化后再次拖动标题栏，应先还原再继续拖动。
- 支持多显示器移动。
- 窗口重新显示后恢复正确的无边框样式与圆角。
- `Alt+F4` 继续触发隐藏到托盘。
- 托盘“退出”才执行真正退出。

### 6.3 Windows 集成

实现层使用 Win32/DWM 适配：

- 无边框窗口仍保留任务栏图标；
- Windows 11 尝试启用 DWM 圆角；
- 无法启用时退化为普通直角，不阻止启动；
- 不使用会破坏托盘恢复、焦点或 DPI 的永久 `topmost` 技巧。

## 7. 主背景与局部光晕

窗口主体由背景 Canvas 和内容层组成：

1. Canvas 填充 `window_bg`。
2. 左上角放置紫色低亮度光晕。
3. 展开模式右侧当前项目卡片附近放置蓝色低亮度光晕。
4. 内容容器位于 Canvas 上方。
5. 窗口调整大小时只在动画结束后重新计算高成本光晕，不在每一帧重建图层。

紧凑模式只显示左上紫色光晕。展开模式可显示两处光晕。

## 8. 紧凑模式布局

```text
┌──────────────────────────────────────────┐
│ ◈ Agent Launcher                  — □ × │
├──────────────────────────────────────────┤
│ [⌕  Search projects or directories…] ↻  │
│                                          │
│ FAVORITES                                │
│ ▌ [folder] Project name              ★  │
│     D:\path\to\project                 │
│                                          │
│ RECENT                                   │
│   [folder] Another project           ☆  │
│     D:\path\to\another                 │
│                                          │
│ Current project                          │
│ Project name                             │
│ D:\path\to\project                     │
│ [ Claude Code ]        [ Hermes ]        │
│ Indexed 428 directories                  │
└──────────────────────────────────────────┘
```

规则：

- 搜索框紧贴标题栏下方，是第一视觉焦点。
- 刷新按钮作为搜索框右侧 36 × 40 幽灵按钮。
- 收藏和最近目录共享一个圆角列表卡片。
- 当前项目摘要与启动按钮固定在底部，不随列表滚动。
- 搜索时列表切换为 `SEARCH RESULTS`，底部不移动。
- 展开按钮放入标题栏左侧操作区或搜索栏右侧，不再使用突兀的白色按钮。

## 9. 展开模式布局

```text
┌────────────────────────────────────────────────────────────────────┐
│ ◈ Agent Launcher                                            — □ × │
├────────────────────────────────────────────────────────────────────┤
│ [⌕ Search projects…]  ↻                                           │
│                                                                    │
│ 45% DIRECTORY AREA              55% CONTROL AREA                   │
│ ┌──────────────────────┐       ┌───────────────────────────────┐   │
│ │ Favorites / Recent   │       │ Current Project               │   │
│ │ Search Results       │       │ name, path, open, copy        │   │
│ │                      │       └───────────────────────────────┘   │
│ │                      │       ┌───────────────────────────────┐   │
│ │                      │       │ Launch Options                │   │
│ │                      │       │ window/tab, permission, hide  │   │
│ │                      │       │ Claude / Hermes               │   │
│ │                      │       └───────────────────────────────┘   │
│ │                      │       ┌───────────────────────────────┐   │
│ │                      │       │ Terminal Appearance           │   │
│ │                      │       │ mode, opacity, cancel, apply  │   │
│ └──────────────────────┘       └───────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

- 左右比例使用 Grid 权重 45:55。
- 右侧三张卡片独立布局，不再把所有内容放在一张大面板中。
- 三张卡片高度随内容自然分配；窗口较矮时右侧允许滚动，但默认尺寸下不应出现滚动条。
- 右侧卡片之间间距 10 px。

## 10. 搜索框

### 10.1 样式

- 使用自定义深色输入容器，避免系统白色 Entry。
- 背景 `surface_1`。
- 默认边框 `border`。
- 聚焦边框 `border_focus`。
- 高度 40 px，圆角 10 px。
- 左侧搜索图标，右侧可显示清除按钮或快捷键提示。
- Placeholder：`Search projects or directories…`。

### 10.2 状态

- 默认：1 px 深灰边框。
- Hover：边框提亮。
- Focus：紫蓝描边 + 极弱外光。
- Disabled：降低文字和背景对比度。
- 输入清空后恢复收藏和最近目录。

## 11. 目录列表

### 11.1 双层目录行

每行高度约 44 px：

- 左侧 18 × 18 彩色文件夹图标；
- 第一行目录名；
- 第二行缩短路径；
- 右侧收藏星标。

主标题使用 `text_primary`，路径使用 `text_muted`。

### 11.2 状态

默认：

- 背景透明或与卡片一致；
- 无单独边框。

Hover：

- 背景 `surface_hover`；
- 文件夹图标略提亮；
- 星标提高对比度。

Selected：

- 背景 `surface_selected`；
- 左侧 2 px 紫蓝光条；
- 主标题保持白色；
- 路径提高到 `text_secondary`。

Favorite：

- 星标使用 `favorite`；
- 非收藏星标使用 `text_muted`；
- 星标 hover 时转为 `favorite`。

不可用目录：

- 行内容整体降低透明度；
- 路径显示 `Unavailable`；
- 禁止启动；
- 星标仍可取消收藏。

### 11.3 分组标题

- 大写字母；
- 字号 8；
- 字间距通过视觉留白模拟；
- 颜色 `text_muted`；
- 与第一行间距 6 px；
- 不使用粗分割线。

## 12. 卡片

卡片基础样式：

```text
背景：surface_1 / surface_2
圆角：12
边框：1 px border
内边距：12
```

Hover 卡片仅对可交互卡片生效：

- 背景轻微提亮；
- 边框转为 `border_hover`；
- 不改变大小；
- 不使用明显位移动画。

当前项目卡片可在背景加入极弱蓝色光晕，但文字区域保持实色底。

## 13. 按钮系统

### 13.1 Claude 主按钮

- 背景 `claude`；
- Hover `claude_hover`；
- 文字使用深色 `#08110C`；
- 高度 40；
- 圆角 8；
- 左侧绿色 Agent 图标；
- 按下时只降低亮度，不缩放布局。

### 13.2 Hermes 主按钮

- 背景 `hermes`；
- Hover `hermes_hover`；
- 文字使用深色 `#171008`；
- 其他规则同 Claude。

### 13.3 次按钮

适用于刷新、展开、复制路径、打开目录、取消预览：

- 背景透明或 `surface_2`；
- 文字 `text_secondary`；
- 边框 `border`；
- Hover 背景 `surface_hover`；
- Hover 边框 `border_hover`；
- 高度 30–32；
- 圆角 8。

### 13.4 Apply 按钮

- 紫蓝品牌实色或深紫底；
- 只有外观存在未应用修改时高亮；
- 无修改时进入 disabled 状态。

### 13.5 焦点

所有可键盘操作控件必须有可见焦点态：

- 1 px 紫蓝描边；
- 不依赖颜色之外的唯一提示；
- Enter/Space 行为符合控件类型。

## 14. 开关、单选与滑块

不使用系统默认白色 Radiobutton、Checkbutton 和 Scale 外观。

### 14.1 单选分段控件

`New window / New tab` 和 `Acrylic / Opacity / Solid` 使用深色分段按钮：

- 容器背景 `surface_0`；
- 当前项背景 `surface_selected`；
- 当前项文字 `text_primary`；
- 非当前项文字 `text_secondary`；
- 当前项底部或边缘使用紫蓝强调线。

### 14.2 Check 开关

使用自定义 Toggle：

- 轨道约 32 × 18；
- 关闭背景 `border_hover`；
- 开启背景 `purple` 或 `blue`；
- 圆形滑块 14 × 14；
- 150 ms 状态过渡。

### 14.3 透明度滑块

- 深色轨道；
- 已填充区使用紫蓝渐变；
- 滑块圆点使用 `purple_light`；
- 右侧百分比使用 Cascadia Code；
- Solid 模式下禁用并降低对比度。

## 15. 当前项目卡片

内容顺序：

1. 小型分组标题 `CURRENT PROJECT`；
2. 彩色项目图标 + 项目名；
3. 完整路径；
4. Open Explorer / Copy Path 两个幽灵按钮。

项目名最大一行，路径最多两行并允许中间省略。

无选择时：

- 项目名显示 `No project selected`；
- 路径显示 `Choose a project from the list`；
- 操作按钮 disabled。

## 16. 启动选项卡片

- 分段控件：New window / New tab。
- New tab 下方显示低对比说明：`Focus returns to the Terminal window, not a guaranteed tab.`
- 两个 Toggle：Skip permission confirmation、Hide Launcher after launch。
- Claude/Hermes 主按钮放在卡片底部并排。
- 紧凑模式底部按钮与展开模式卡片按钮复用同一视觉组件。

## 17. Terminal 外观卡片

- 三段模式控件：Acrylic / Opacity / Solid。
- 透明度滑块。
- 状态标签：`Previewing`、`Applied` 或 `No changes`。
- Cancel Preview 为幽灵按钮。
- Apply 为紫蓝强调按钮。
- 预览未应用时收起、隐藏、关闭必须回滚。

## 18. 状态栏

状态栏固定在窗口底部，单行显示：

- 普通：`text_muted`；
- 成功：`success`；
- 警告：`warning`；
- 错误：`danger`。

左侧可显示 6 px 状态点，右侧显示索引数量或快捷键提示。

成功消息约 3 秒后恢复默认状态。错误保持到下一次操作。

## 19. 滚动条

- 使用深色自定义滚动条。
- 轨道尽可能透明。
- Thumb 默认 `#30364A`，Hover `#444D6A`。
- 宽度 7–8 px。
- 不使用系统白色 ttk 滚动条。
- 内容不溢出时隐藏滚动条。

## 20. 动效

### 20.1 窗口展开

保持现有约 220 ms cubic ease-out。

- 左上角固定；
- 向右和向下展开；
- 内容不在动画中频繁销毁重建；
- 右侧卡片在尺寸达到可用阈值后淡入；
- 收起时先淡出右侧，再缩小窗口。

### 20.2 控件动效

- Hover 亮度：100–140 ms；
- Toggle：约 150 ms；
- 卡片选中背景：120 ms；
- 不使用弹跳、旋转或大幅缩放。

Tk 首版允许通过离散颜色插值实现轻量过渡；性能不足时必须退化为即时状态切换，而不是卡顿。

## 21. 可访问性

- 正文与背景对比度目标不低于 4.5:1。
- 辅助文字目标不低于 3:1。
- 重要状态不能只靠颜色表示。
- 目录选中同时使用背景、左光条和焦点框。
- 所有主操作支持键盘。
- 高对比模式下允许关闭背景光晕和透明效果。
- Windows 减少动画设置启用时，窗口和控件动画应缩短或关闭。

## 22. DPI 与多显示器

- 所有尺寸使用 logical px，再由现有 `scale` 转换。
- 自定义标题栏拖动必须正确处理不同 DPI 显示器。
- 最大化目标使用当前显示器工作区，不覆盖任务栏。
- 窗口从高 DPI 显示器移动到低 DPI 显示器后，应重新计算标题栏、圆角和光晕。
- 不使用固定 96 DPI 假设。

## 23. 模块影响

建议新增：

- `python/launcher_theme.py`：颜色、字体、尺寸和状态令牌。
- `python/launcher_chrome.py`：自定义标题栏、无边框窗口、拖动、最大化和 DWM 适配。
- `python/launcher_widgets.py`：圆角卡片、按钮、搜索框、Toggle、Segmented Control、Slider、Scrollbar。
- `python/launcher_background.py`：背景 Canvas 与局部光晕。

建议修改：

- `python/launcher_view.py`：重新组织紧凑和展开布局。
- `python/launcher_directory_row.py`：双层行、图标、星标、选中光条。
- `python/launcher_directory_list.py`：自定义滚动条和分组。
- `python/launcher_settings_panel.py`：拆分三张功能卡片。
- `python/launcher_runtime.py`：安装无边框窗口样式和关闭/隐藏行为。
- `python/launcher_animation.py`：加入右侧内容淡入淡出和减少动画设置。

不修改：

- `session_panel_*` 视觉与交互；
- `terminal_focus.py` 精确 HWND 逻辑；
- `directory_index.py` 搜索与索引算法；
- `launch_controller.py` 启动语义；
- `terminal_appearance.py` 事务语义。

## 24. 测试要求

### 24.1 纯逻辑测试

- 颜色令牌完整性；
- DPI 缩放尺寸；
- 颜色插值；
- 圆角路径生成；
- 标题栏拖动坐标计算；
- 最大化/还原状态机；
- 多显示器工作区边界；
- 减少动画时长计算；
- Segmented Control 和 Toggle 状态转换。

### 24.2 组件测试

使用假的 Tk 根或轻量真实 Tk：

- 标题按钮事件；
- 搜索框焦点态；
- 目录行 hover/selected/favorite；
- 卡片三态；
- Toggle、Segmented Control、Slider；
- 滚动条显示/隐藏；
- 紧凑和展开布局切换；
- 未应用外观回滚。

### 24.3 Windows 手工验收

1. 无原生标题栏，任务栏图标仍存在；
2. 标题栏拖动、双击最大化、还原、最小化正常；
3. 关闭按钮隐藏到托盘；
4. 托盘恢复后标题栏和圆角正常；
5. 高 DPI 下无模糊、错位和裁切；
6. 多显示器拖动和最大化工作区正确；
7. 所有原生白色输入框、按钮、滚动条和单选框已消除；
8. 紧凑模式搜索优先、底部操作区固定；
9. 展开模式左右比例约 45:55；
10. 右侧三张卡片层级清晰；
11. 目录行双层信息和选中光条正确；
12. Claude/Hermes 功能色清晰但不过亮；
13. Acrylic/Opacity/Solid 预览事务保持正确；
14. Session Monitor 不受影响。

## 25. 性能约束

- 空闲状态不持续高频重绘背景光晕。
- 窗口动画期间不重建目录列表。
- 单次 hover 不创建新线程。
- 自定义圆角组件优先复用 Canvas 项目，不重复销毁创建。
- 目录结果 30 项时滚动保持流畅。
- 视觉层不得拖慢后台索引或 Session Monitor 更新。

## 26. 完成标准

视觉重构完成必须满足：

- 无系统白色控件破坏深色主题；
- 自定义无边框标题栏功能完整；
- 主背景、卡片、按钮、列表、设置控件使用统一令牌；
- 紧凑与展开模式均符合已确认布局；
- 目录行为双层信息行；
- 展开模式右侧为三张卡片；
- 紫蓝光晕低亮度且不影响文字；
- Claude/Hermes 保持清晰功能色；
- DPI、多显示器、托盘恢复和键盘操作可用；
- 现有 44 个自动测试继续通过；
- 新视觉逻辑和组件测试通过；
- Windows 手工验收完成后才可声明视觉重构完成。
