# Scoop 原生代码编辑器的 Monaco 基础功能清单

2026-11-26。对照 Monaco Editor **0.58.0** 的公开声明、默认入口登记的 64 个模块，以及该版本使用的核心命令和视图实现。Scoop 的交付状态以编辑器主分支 `f069315` 为准。下表按用户能执行的操作合并方向、平台快捷键和命令别名。文末附 64 个模块的去向，便于按名称查漏。[Monaco 版本与对应源码提交][release] · [独立组件功能入口][features] · [公开 API][api] · [Scoop 组件合同](https://github.com/scoop-lang/scoop-code-editor/blob/f069315/docs/SPEC.md)

**建议把“基础功能做全”分两批验收。** 第一批要让人只用键盘和鼠标就能完整地编辑一份源码。第二批要让宿主能为同一组件提供折叠、着色、字体和代码旁的交互内容。两批都属于编辑器组件范围。语言分析器可以独立选择。

## 第一批　日常编辑

| 能力 | Scoop 当前可用 | 建议验收的范围 |
| --- | --- | --- |
| 文档与批量编辑 | **已有**。UTF-8 piece tree、按行和范围读取、固定版本快照、原子批量替换、位置映射、变更事件、显式转换 LF／CRLF。两个视图可共享同一文档 | 所有改写命令复用编辑事务，按编辑结果恢复选区。覆盖混合换行、尾部空行、跨片段编辑及过期版本 |
| 光标移动与选择 | **已有常用操作**。字素、词、视觉行首尾、逻辑行首尾、上下移动、翻页、文档两端、Shift 扩选和全选。垂直移动保留目标横坐标。Home 可切换到首个非空白，Esc 可取消组字、清除次光标或收起主选区 | 补键盘逐次扩选整行。分别验收逻辑行、折行后的视觉行、混排双向文字及反向选区 |
| 鼠标与列选 | **部分**。点击定位、拖选、Shift 点击、双击选词、三击或点行号选行、Alt 点击加光标 | 补按词／整行拖选、拖出视口自动滚动，以及键盘和鼠标的矩形列选。矩形按屏幕列命中，覆盖 Tab、宽字符、长短行混排 |
| 多光标与多个选区 | **部分**。保存主次、方向和视觉偏向，去重并合并重叠选区。可批量键入、删除，从当前词或选区追加上／下一个匹配、跳过当前项或选择全部匹配 | 补上方／下方加光标、选中各行末尾加光标。验证矩形选区转成各行选区后，每条文本命令仍可一次撤销 |
| 键入、删除与输入法 | **已有**。插入、覆盖选区、Enter、前后删除字素、按词和行边界删除。普通键入作用于所有选区，原生组合编辑跟随主选区 | 保留组合串更新、提交、取消及候选窗定位。覆盖 emoji、组合字符、中日韩输入和多行粘贴。主选区跨行时输入法上下文覆盖这些逻辑行。超长单行单独测量 |
| 剪贴板 | **已有**。系统剪切／复制／粘贴同时支持纯文本与保留多选区的片段。空光标按整行操作。多光标可逐段分发或在每处粘贴全部内容 | 验收外部纯文本、多段各自含换行、末行无换行、同一行有多个光标，以及粘贴后一次撤销 |
| 撤销与重做 | **已有共享历史栈**。连续键入或同向删除可合并，粘贴和组合提交有各自的边界。撤销恢复交互选区，新编辑截断重做分支。菜单可查询 `canUndo`／`canRedo` | 移动行、块缩进、多光标替换和全部替换均按命令撤销和重做。验证两视图共享历史并各自保有选区 |
| 整行与选区命令 | **已有**。上移／下移行块、向上／向下复制行、复制选区、删除整行、在上方／下方插入空行、合并行 | 空选区取当前行。多个选区命中同一行只处理一次。覆盖反向选区、文末无换行及移动后的光标位置 |
| 行缩进与块缩进 | **已有基础缩进**。可设置缩进宽度、Tab 显示宽度及写入空格或 Tab，支持按制表位进退、块缩进／反缩进、Enter 继承缩进和 Tab／空格转换 | 在混合换行中选中两行且末端落到第三行行首，块缩进只作用于前两行。语言规则驱动的增减缩进见第二批 |
| 文档内查找与替换 | **已有**。选中文字发起查找、双向循环、大小写、Unicode 全词、正则、选区内查找、匹配序号与总数、当前／全部替换以及编号和命名捕获组 | 无效表达式给出反馈，零宽匹配可继续遍历，替换全部可整笔撤销。折叠接入后，定位到隐藏匹配应展开对应范围 |
| 定位、视口与阅读位置 | **部分**。行号、软换行、横纵滚动、可见范围、`revealRange`、光标矩形和各视图独立的滚动状态 | 补拖动滚动条、转到行／列、按行／页只滚动视口、居中显示光标行，以及切换文档时保存和恢复视图状态。跳转后键盘焦点回到正文 |
| 命令、快捷键与菜单 | **已有统一入口**。内置动作有稳定 ID，可列举、查询可用性、改键或解绑。原生文字命令、编辑器右键菜单、宿主菜单与快捷键复用动作 | 新增动作沿用这一入口。验收移动／选区、只读、输入法组字、焦点切换，以及重绑后旧快捷键的行为 |
| 原生输入与无障碍 | **已有 macOS 验证**。正文由自绘 Element 接收原生输入。辅助技术可读取全文、设置选区并发起编辑。Tab 可切换插入或焦点遍历 | 验收查找框与嵌入的 Lens 按钮能用键盘进入和退出，返回正文后仍能继续组字。Windows、Linux 按各自原生输入及辅助技术验证记录交付 |

Monaco 的 `cursorColumnSelectDown` 向下扩展列选，`editor.action.insertCursorAbove` 在上一行加光标，`editor.action.selectHighlights` 选中所有匹配，`editor.action.moveLinesDownAction` 将行块下移。Scoop 可在已有选区与事务上实现这些操作，并让宿主和默认快捷键调用同一个入口。[Monaco 核心命令][core] · [多光标命令][multi] · [行操作][lines] · [查找与替换][find] · [Scoop 文字命令](../src/edit/commands.scoop) · [原生命令分发](../src/input/navigation.scoop) · [鼠标与键盘入口](../src/input/events.scoop)

### 容易漏掉的命令

| 操作 | 两批交付内 | 可独立追加的 Monaco 动作 |
| --- | --- | --- |
| 选行与选词 | 键盘逐次扩选整行，双击选词后按词拖动，三击或点行号后按整行拖动 | 单独指定上一个或下一个词的词首／词尾，删除光标所在词，按驼峰子词移动。[整行选择][expand-line] · [词操作][word] · [子词操作][word-part] |
| 多光标 | 上／下加光标、各选中行末加光标、追加／跳过匹配、矩形扩选 | 一次向文件首尾加光标、把焦点轮换到上一／下一光标，只撤销光标移动。[多光标命令][multi] · [核心命令][core] |
| 缩进与注释 | 行／块进退一个缩进级，沿用缩进及根据规则增减，切换行注释与块注释 | 按规则重排整个文件或选中行的缩进，自动探测缩进，独立“添加行注释”和“移除行注释”。[缩进命令][indent-actions] · [注释命令][comment-actions] |
| 括号与折叠 | 跳转／选择至配对括号，手动设置与移除折叠区，当前、递归、全部折叠／展开 | 移除匹配的括号对、按嵌套深度给括号着色、跳到父折叠／相邻折叠、按级别或标记折叠。[括号命令][brackets] · [折叠命令][folds] · [编辑器选项][options] |
| 滚动与导航 | 翻页移动光标，独立按行／页滚动视口，转到行列并定位，恢复阅读位置 | 水平步进滚动、只把视口移到文档顶端／底端。这些动作可共享同一滚动状态。[核心命令][core] |

### 同一条命令在不同状态下的行为

这些行为分布在模型、视图选项和命令执行接口中，只看默认功能模块容易漏掉。

| 验收什么 | 本项目的取舍 |
| --- | --- |
| 只读与共享文档 | 第一批必需。在只读视图可移动光标、扩选、复制和查找。键入、剪切、粘贴、替换和撤销应按只读状态禁用。另一可写视图改动正文后，只读视图同步显示新内容。[Monaco 只读选项][readonly] · [Scoop 事务用例](../tests/transactions.scoop) |
| 逻辑行、视觉行与列 | 第一批必需。软换行后，上下键和鼠标命中沿视觉行移动，整行移动、注释、缩进和行号仍按源码逻辑行。字符、UTF-8 字节列、Tab 展开列和像素横坐标分别有自己的用途。固定列折行、折行附加缩进、光标外形及滚动留白可按宿主需求追加。[Monaco 折行选项][wrapping] · [核心移动命令][core] |
| 键入、覆盖选区与改写模式 | 第一批保留普通键入替换非空选区。单独切换的改写模式会在空光标处替换后面的字符，作为可选动作。选区数量、每处替换范围和撤销分组可用同一套事务表达。[Monaco 改写模式选项][overtype] · [Scoop 编辑合同](SPEC.md#编辑与选区) |
| 视图、订阅与文档的寿命 | 第一批已有共享文档和独立视图。关闭一个视图及其监听后，另一视图还能读取、编辑和撤销。第二批扩展也应能单独移除自己的装饰、Lens 和提示。文档版本可用于剔除过期结果，文件路径、保存和未保存提示由宿主管理。[Monaco 模型与释放约定][concepts] · [Scoop 扩展用例](../tests/extensions.scoop) |

## 第二批　代码编辑视图与扩展

| 能力 | Scoop 当前可用 | 组件应提供什么，宿主应提供什么 |
| --- | --- | --- |
| 代码输入规则 | **待补**。Enter 已沿用当前逻辑行的换行符并继承缩进 | 组件执行括号／引号自动闭合、跳过已生成的闭合符、成对删除、用括号包围选区，以及切换行／块注释。宿主声明词边界、注释符、配对符、回车及缩进规则。先用一份 Scoop 配置验收 |
| 折叠 | **待建**。现有软换行仅处理一行文字的换行显示 | 支持缩进范围、手动选择范围和宿主提供的嵌套行范围。边栏与键盘都能折叠／展开当前层、子层或全部，折叠处显示占位提示。折叠状态属于视图，导航、命中、滚动和查找跳转共用可见行映射 |
| 范围装饰与交互高亮 | **部分**。文档级／视图级前景、背景、下划线、边栏颜色标记随编辑移动。查找匹配已有高亮 | 增加当前行、选区同文匹配、配对括号高亮与跳转／选择至括号、整行装饰。让匹配括号、查找和普通范围着色可同时辨认。语义引用高亮可由宿主提供范围 |
| 语法着色与主题 | **仅有着色原语**。宿主可手工标范围设颜色 | 组件接收行内 token 区间与样式类别，主题解析为颜色、粗体、斜体等。首个词法着色器可按行传递状态，让多行注释在编辑后正确更新。语义 token 以后从外部叠加 |
| 整体字体与范围字体 | **部分**。`CodeEditorOptions.text` 控制整视图的字体族、回退、字号等。同一行内的范围目前只可局部设色 | 组件让不同范围设置字体族、字号、字重和斜体。改变字宽或行高要重新排版受影响的行，绘制、光标、点击、选择和候选窗共用实测字形位置。正文可与提示文字选用不同字体 |
| 视口排版与长行 | **已有可见行排版**。常规绘制排版可见及临近逻辑行，并复用布局。约 300 KB 的单行仍会整行排版 | 折叠、混排字体及行内提示都接入同一套模型位置到视图位置的映射。用相同字节数的十万短行和单条长行分别验证键入、滚动、选择及命中，比较接入扩展前后的实测成本 |
| 可读性与边栏 | **部分**。已有可开关的绝对行号、可配置配色、Tab 展开、行号位置的颜色标记 | 补缩进引导线、空白／控制字符可视化、列标尺和可点击的边栏图标。主题可切换深浅和高对比。宿主决定具体配色及图标操作 |
| 内容控件、浮层与行间空间 | **已有三种原语**。位置锚定控件、视口浮层、按高度占位的行后控件。`CodeLineNote` 已能展开批注 | 补行前锚点（含第一行上方）和需要时的重新测量。扩展可沿用已有的可见范围事件，还需能查询命中位置及正文／边栏／控件目标 |
| 行间 CodeLens | **仅有行间控件**。可做行后批注，尚无批量提供 Lens 的入口 | 宿主给出源码锚点、标题和动作，组件将同一行的多个动作排在目标行上方，管理占位、点击、焦点、滚动与折叠。可先接静态数据。引用计数等需要计算的标题可在可见时解析 |
| 行内提示（inlay hints） | **待建** | 在指定偏移之前／之后插入仅用于显示的短文本，参与字形排版、折行和点击。组件规定两侧可停靠的光标位置。文档偏移、复制和撤销继续以原文为准。宿主提供类型名、参数名等内容 |
| 诊断标记与悬停 | **仅有装饰和浮层** | 宿主按来源提交范围、严重程度与消息。组件显示波浪线／边栏标记、悬停说明、前一条／后一条。范围随编辑移动，分析结果按快照版本更新。首个使用者可直接提交一条诊断 |

Monaco 为这些能力提供了不同的数据入口。语言配置描述符号和编辑规则，token provider 产生词法区间，folding provider 返回行范围，CodeLens 返回命令信息。它还在范围装饰中公开字体属性和注入文本。本组件可沿用这些职责，以 Scoop 的 `Utf8Range`、`TextLayout`、`View` 和可关闭的登记表达。[语言配置][language] · [词法接口][tokens] · [范围字体和装饰][decor] · [折叠实现][folds] · [CodeLens 接口][lens] · [Lens 行间布局][lenswidget] · [行内提示实现][inlay] · [Scoop 装饰](../src/extensions/decorations.scoop) · [Scoop 控件](../src/extensions/widgets.scoop)

共享文档的两个视图可复用同一版本的 token、折叠候选范围和诊断，各自保存实际折叠状态、几何和焦点。宿主用快照、正文变更和可见范围事件交付数据。异步结果应对应请求时的文档版本，关闭登记时一并清除其展示内容。[Scoop 视图状态](../src/view/state.scoop) · [现有长行测量](PERFORMANCE.md)

## 值得沿用的 API 设计

| 关注点 | Monaco 的公开入口 | Scoop 的落点 |
| --- | --- | --- |
| 文档存储 | `ITextModel.createSnapshot`、按行／范围读取、`getOffsetAt`、`getPositionAt`。Piece tree 属于内部实现 | `CodeDocument` 按 UTF-8 字节范围编辑，`CodeSnapshot` 提供固定版本的只读片段。两个视图可共享正文和历史。公开坐标保留 Scoop 的零起点字节列，接入使用 UTF-16 的宿主时在边界转换。视觉列和像素坐标来自实际排版。[模型接口][model] · [Monaco piece tree][piece] · [Scoop 坐标约定](SPEC.md#文档) |
| 编辑命令 | `ICommand.getEditOperations` 描述修改，`computeCursorState` 计算新选区。`executeEdits` 和 `pushUndoStop` 提供执行及撤销边界 | 在旧版本上生成一批替换，一次提交，用 `CodeEditMap` 计算各选区的新位置。纯导航只改视图。键入、菜单、宿主动作遵守相同的只读和历史规则。[命令接口][command] · [编辑器执行接口][execute] |
| 视图与事件 | `getSelections`、`saveViewState`／`restoreViewState`、`getVisibleRanges`、`getTargetAtClientPoint`，以及正文、选区、滚动和布局事件 | 视图拥有主次选区、折叠和阅读位置。可见行排版应同时服务绘制、鼠标命中、键盘列选、辅助技术和候选窗。滚动、改宽、变字体或显示 Lens 后查询同一已呈现帧。[可见区域和控件接口][geometry] |
| 高亮和控件 | `createDecorationsCollection` 提交可追踪的范围。`addContentWidget` 锚定正文，`addOverlayWidget` 锚定视口，`changeViewZones` 改变行间布局 | 查找用范围着色，查找面板用浮层，CodeLens 用行前占位加原生按钮，inlay 用参与字形排版的虚拟文本。单纯改色只需重绘，影响字形或行高的样式还要重排。[装饰选项][decor] · [视图控件][geometry] |
| 数据提供与生命周期 | 语言配置、tokens、folding ranges、CodeLens、inlay hints 和按来源设置的 markers 有各自的入口。状态监听及多数登记可释放 | 直接用一份 Scoop 配置、内存行范围、一条诊断和一个“运行测试”按钮即可验收。外部分析器可以随后接入相同接口。文档、快照版本和可见范围决定结果发给谁、何时采用。[语言配置][language] · [诊断接口][markers] · [Lens 接口][lens] |

**原生输入法上下文以主选区为中心。** Monaco 的浏览器 `EditContext` 从主选区首行行首取到末行行尾，普通光标因此只有一行。它的 `textarea` 路径另有策略，例如关闭读屏支持时，macOS 的空选区可只取光标前的词或字符。Scoop 正文从自绘 `Element` 接入原生输入，在本地片段与文档之间映射范围。现有同为 299,999 字节的样本中，十万短行首次聚焦送出 2 字节，单条长行送出 299,999 字节。全文选区和辅助技术读取全文分别验收。[Monaco EditContext][ime-native] · [textarea 路径][ime-textarea] · [Scoop 原生实测](PERFORMANCE.md)

**实现依赖。** 文档快照、选区和事务足以支撑整行命令、行块缩进、剪贴板、查找替换和共享撤销。折叠、范围字体、行内提示和行间 Lens 则先要统一三种位置的换算，即源码偏移、折行或折叠后的位置、窗口中的像素位置。否则一个 Lens 就能把下一行的鼠标命中和输入法候选窗一起推错。先用两个独立视图、一段大字号正文、一条折叠范围及首行上方的按钮验收这套换算，再接提供真实结果的语言服务。[视图 API][geometry] · [Scoop 排版设计](DESIGN.md#4-可见行排版与绘制)

## 其余 Monaco 能力的取舍

| 建议 | 覆盖的能力 | 原因与接入点 |
| --- | --- | --- |
| 做成可选编辑动作 | 驼峰／子词移动与删除、光标位置撤销／重做、设置选择锚点、扩大／缩小选择、改写模式、字符互换、排序／倒序／去重行、大小写和命名风格转换、清理行尾空白、插入末尾换行 | 多数可复用选区、事务和动作。按结构扩大选区时可由宿主给父范围 |
| 按需补输入体验 | 选中文字拖放移动／复制、带格式复制、特殊粘贴、粘贴后重缩进、自动侦测缩进、查找保留大小写、缩放与相对行号 | 有具体宿主需要时补。特殊粘贴交付一笔编辑，默认纯文本路径仍可独立工作 |
| 做成可选的编辑器界面 | 文档内命令面板／帮助、链接、颜色选择器、只读提示、空文档占位、悬浮动作、Unicode 易混淆字符与异常行终止符提示 | 可复用动作、装饰、命中及浮层。打开链接、执行外部操作由宿主决定 |
| 保留语言数据接入点 | 补全列表／行内补全、片段与占位符、参数提示、格式化、快速修复、重命名、联动编辑、文档大纲、定义／引用和 Peek | 由功能扩展按需提供文本编辑、范围或候选项。普通输入、折叠、着色、Lens 均可用内存数据独立验收。接 LSP、Tree-sitter 或自有分析器由宿主选择 |
| 单独评估显示功能 | Minimap、overview ruler、Sticky Scroll、章节标题、并排／行内 Diff 和差异导航 | 各自引入额外布局、索引或第二份文档。先交付单编辑视图。后续以独立选项或组件复用模型和绘制 |
| 沿用原生平台能力 | 浏览器 DOM／CSS、浏览器键盘和 iPad 网页输入适配、Web Worker、浏览器 GPU 调试、图标字体及 token 检查工具 | Scoop UI、Graphics 与 Window 已提供原生控件树、字体排版、绘制和输入接口。保留用户可见的编辑行为，平台集成按原生 API 实现 |

这些取舍来自 standalone 的功能登记和公开编辑器选项。它们也给第二批划出了边界，例如行间 Lens 的展示可以直接验收，计算“几处引用”可以留给语言扩展。[Monaco 功能登记][features] · [编辑器选项][options] · [模型与编辑器概念][concepts]

### 按上游模块复核覆盖

默认入口有 64 个模块。核心方向键等命令在 `coreCommands` 中，软换行、字体、滚动条和 minimap 等还须查公开选项。一个模块可能含有不同优先级的操作；下表按其主要用途归档。[默认入口][features] · [核心命令][core] · [编辑器选项][options]

| 项目取舍 | 上游模块名 | 本项目关注的边界 |
| --- | --- | --- |
| 日常编辑（11） | `codeEditor`、`clipboard`、`contextmenu`、`find`、`gotoLine`、`indentation`、`lineSelection`、`linesOperations`、`multicursor`、`toggleTabFocusMode`、`wordOperations` | 两批清单所列基础动作为必需。按词首／词尾分别扩选、将光标加到文件首尾、轮换多光标焦点、排序行等细分动作可另外登记 |
| 代码视图与数据展示（12） | `bracketMatching`、`codelens`、`comment`、`folding`、`gotoError`、`hover`、`inlayHints`、`longLinesHelper`、`semanticTokens`、`toggleHighContrast`、`tokenization`、`wordHighlighter` | 基础范围、排版、跳转和样式属于组件。按级别折叠、跳到父折叠和只折叠注释可继续加动作。长行采用原生测量，语义颜色和悬停说明可由宿主提供 |
| 可选手势和编辑动作（10） | `anchorSelect`、`caretOperations`、`cursorUndo`、`dnd`、`fontZoom`、`inPlaceReplace`、`insertFinalNewLine`、`middleScroll`、`smartSelect`、`wordPartOperations` | 包括左右平移选中文本、光标历史、拖放、中键滚动、子词移动、按结构扩大选择、把当前位置换成上／下一个值。需要结构或候选值的动作消费宿主数据 |
| 可选编辑器界面（10） | `colorPicker`、`floatingMenu`、`inlineProgress`、`links`、`placeholderText`、`quickCommand`、`quickHelp`、`readOnlyMessage`、`unicodeHighlighter`、`unusualLineTerminators` | 在现有命令、装饰和控件之上增加界面。只读约束和可访问焦点本身已计入第一批 |
| 按需接入的扩展（13） | `codeAction`、`documentSymbols`、`dropOrPasteInto`、`format`、`gotoSymbol`、`inlineCompletions`、`linkedEditing`、`parameterHints`、`quickOutline`、`referenceSearch`、`rename`、`snippet`、`suggest` | 宿主可实现代码操作、片段、补全、格式化、文档符号和特殊粘贴。编辑结果走普通事务，列表和提示可沿用视图控件 |
| 独立显示功能（4） | `diffEditor`、`diffEditorBreadcrumbs`、`sectionHeaders`、`stickyScroll` | 单独评估双文档比较、区段标记和置顶上下文。Minimap 和 overview ruler 同属后续显示选项 |
| 浏览器实现与开发工具（4） | `codicon`、`gpu`、`inspectTokens`、`iPadShowKeyboard` | Scoop 用原生图标、绘制以及窗口输入协议。Token 检查器按调试需求决定 |

## 验收样例

初始基线 `3aff516` 在 macOS arm64 通过了 21 项常规测试和 1 项 AppKit 原生输入及无障碍协议测试。行操作、查找、剪贴板与原生动作随后分别合入 `536b669`、`8ce7696`、`f069315`。已有混合换行、反向选区、捕获组、零宽匹配、分段粘贴和命令可用性的专测。下面五个场景用来判断两批能力能否配合工作。[行操作用例](../tests/lines.scoop) · [查找用例](../tests/find.scoop) · [剪贴板和动作用例](../tests/clipboard.scoop) · [原生验证入口](../validation/appkit.sh)

1. **用多个光标改源码。** 从当前词连续选中两处，再在下一行加光标。一次键入同时修改三处。撤销恢复三组原选区，重做恢复修改。另测矩形选区跨 Tab 和汉字时的逐行粘贴。
2. **移动和缩进一块代码。** 在含 CRLF 的文档中选两行，选区末端落到第三行行首。缩进、下移、复制行块时只操作前两行，每个动作均可单独撤销。切换到空格缩进再按 Enter 时继承正确层级。
3. **两个视图共享折叠区内的正文。** 左边折叠函数，右边保持展开并编辑函数体。左边的行号、光标及 Lens 跟随新位置。查找命中隐藏文本时左边展开并定位，右边保留自己的视图状态。
4. **第一行同时展示 Lens 和行内提示。** 在首行函数上方显示可聚焦、可点击的“运行测试”，在实参前显示参数名提示。切换部分正文的字体／字号并缩窄视口后，点击、选择、输入法候选窗和折行仍对准字形。复制函数得到原始源码。
5. **替换与着色分别生效。** 在选区内用含捕获组的正则一次替换多个匹配，撤销后文本和选区恢复。改变多行注释的起始符会更新后续行的词法高亮。主题或诊断变化只更新显示。

[release]: https://github.com/microsoft/monaco-editor/blob/v0.58.0/package.json
[features]: https://github.com/microsoft/monaco-editor/blob/v0.58.0/src/features/register.all.ts
[concepts]: https://github.com/microsoft/monaco-editor/blob/v0.58.0/README.md#concepts
[api]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts
[core]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/coreCommands.ts
[multi]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/multicursor/browser/multicursor.ts
[lines]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/linesOperations/browser/linesOperations.ts
[find]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/find/browser/findModel.ts
[options]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L3209
[readonly]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L3334
[wrapping]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L3498
[overtype]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L3418
[language]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L7038
[tokens]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L6755
[decor]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L1684
[folds]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/folding/browser/folding.ts
[lens]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L8599
[lenswidget]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/codelens/browser/codelensWidget.ts
[inlay]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/inlayHints/browser/inlayHintsController.ts
[model]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L2026
[piece]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/common/model/pieceTreeTextBuffer/pieceTreeBase.ts
[command]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L2546
[execute]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L6329
[geometry]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L6383
[markers]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L1044
[ime-native]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/controller/editContext/native/nativeEditContext.ts#L496
[ime-textarea]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/controller/editContext/textArea/textAreaEditContext.ts#L209
[expand-line]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/lineSelection/browser/lineSelection.ts
[word]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/wordOperations/browser/wordOperations.ts
[word-part]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/wordPartOperations/browser/wordPartOperations.ts
[indent-actions]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/indentation/browser/indentation.ts
[comment-actions]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/comment/browser/comment.ts
[brackets]: https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/bracketMatching/browser/bracketMatching.ts
