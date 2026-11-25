# Scoop 原生代码编辑器组件设计

2026-11-26 · 设计草案。文中的 `CodeDocument`、`CodeEditorState` 和 `codeEditor` 等名称均为拟议接口。

宿主创建一份文档，可以把它放进两个编辑视图。左边编辑时，右边看到同一笔正文变化，两个视图各自保留选区和阅读位置。宿主还可以只用公开接口添加查找框、匹配高亮和“全部替换”。这两个场景决定首版需要怎样的存储、绘制、命令和扩展接口。

参考版本为 Monaco Editor 0.58.0。它公开文档模型、独立的编辑器视图、范围编辑和视图扩展点。下文链接的编辑器源码来自该版实际使用的提交。Scoop 采用自己的 UTF-8 坐标、原生文本输入和 `View` 生命周期。[Monaco 版本与核心提交](https://github.com/microsoft/monaco-editor/blob/v0.58.0/package.json) · [对应的公共 API](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts)

## 1. 组件边界与所有权

建议用一个普通库 Cone `scoop.ui.editor` 承载组件。**正文编辑区从 `scoop.ui.Element` 起独立实现**，自有文档、视图、编辑命令和输入法适配器。宿主提供初始文本，决定文件读写和文档身份。`codeEditor(state)` 返回可放进任意布局的 `View`。首版提供原生文本编辑、行号、水平滚动、可选软换行、多选区批量操作、撤销重做、范围装饰和查找替换。Diff、折叠、Minimap 和语言服务留给后续独立需求。

| 对象 | 拥有的状态 | 生命周期 |
| --- | --- | --- |
| `CodeDocument` | 已提交的 UTF-8 正文、行索引、正文版本、共享撤销历史、文档级装饰 | 宿主持有，可在没有窗口时创建、编辑和测试 |
| `CodeEditorState(document)` | 一个视图的方向选区与主选区、阅读锚点、折行设置、动作与视图级装饰 | 绑定一份文档，可跨卸载保留。两个视图各建一个 state。`close()` 解除它的文档订阅和登记 |
| 已挂载的编辑器 `Element` | 焦点、输入法连接与局部输入片段、滚动视口、当前排版、已呈现的屏幕几何和子 View | 随挂载建立与释放。重新绑定 state 时先结束原输入会话，再接入新文档 |

宿主嵌入双视图的拟议写法如下。每个视图各有一份 `CodeEditorState`，同一 state 同时只挂载一处。

```kotlin
class SplitEditor(scope: ComponentScope): Component(scope) {
    private val document = CodeDocument("val count = 1\n")
    private val left = scope.resource { CodeEditorState(document) }
    private val right = scope.resource { CodeEditorState(document) }

    public override fun render(): View = row {
        item(codeEditor(left)) { grow = 1.0 }
        item(codeEditor(right)) { grow = 1.0 }
    }
}
```

正文使用 `scoop.graphics.text` 做字形排版与命中，使用 UI 的滚动、焦点和 `InputArea` 路由，在获得焦点的编辑视图上直接接收 `scoop.window` 文本输入批次。`Input`、`Textarea`、`TextEditHost` 和 `TextEditorState` 均不参与正文的存储、排版或输入，也不需要隐藏文本框转发按键。查找面板里的搜索框可以像其他普通 UI 一样使用现成控件。[UI 分层](https://github.com/scoop-lang/scoop/blob/main/docs/ui/DESIGN.md) · [Window 文本输入类型](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.window/src/text/types.scoop)

## 2. 文档存储与读取 API

### 2.1 UTF-8 piece tree

文档使用按正文顺序排列的红黑树。每个片段（piece）只记录一个缓冲块及其字节起止位置。打开文档时顺序读取原文、分块并建立行索引。键入的字节写入当前追加块，块满后换块。插入时拆开命中片段并接入新片段，删除时移除所覆盖的片段。同块连续字节可合并为一个片段。块边界落在 UTF-8 标量边界，已写入的字节保持稳定。这样在文件开头插字也能复用后面的存储。[Monaco piece tree](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/common/model/pieceTreeTextBuffer/pieceTreeBase.ts) · [Scoop String 的 UTF-8 表示](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-SPEC.md#114-string)

块保存换行位置，树节点汇总子树字节数和逻辑换行数。正文原样保留 LF、CRLF、单 CR 及混合换行。合并相邻子树时，左侧末字节为 CR 且右侧首字节为 LF，要把两次计数合为一次。拆分、拼接和撤销都按这条规则更新受影响的树路径。按行或偏移定位先下降树，再查块内索引。读取长范围的成本还包括遍历所跨片段和输出这些字节。

| 拟议入口 | 约定 |
| --- | --- |
| `byteLength`、`lineCount`、`version` | 空文档有一行。尾部换行产生最后一个空行。正文成功变化一次，版本推进一次，包括撤销和重做 |
| `read(range)`、`lineRange(line, includeBreak)` | `Utf8Range` 是半开字节区间。`lineRange` 可取行内容或连同行尾。只物化调用方请求的范围 |
| `positionAt(offset)`、`offsetAt(position)` | 模型行号与行内字节列均从 0 开始，UI 行号显示时加 1。行末指向分隔符之前。CRLF 两字节中间的偏移转为逻辑位置时收敛到前一行末，精确读取和替换仍可按原始字节边界进行 |
| `snapshot()` | 按需取得固定版本的只读快照，支持范围读取与分片顺序遍历。创建时封存当前追加块，复制片段描述并保留块引用，成本随片段数增长。后续编辑继续写新块，已取得的快照仍可读取 |
| `onChange(listener)` | 可关闭的订阅。事件给出旧版本、新版本、旧坐标中的范围替换、对应的新范围和编辑类别。仅移动选区、滚动或重新着色时，正文版本保持原值 |

文档树直接从键入范围生成变更，按需构造公开快照或整份 `String`。历史只保留还原编辑所需的片段和选区。树、历史及快照直接持有使用中的块，最后一个引用释放后由 GC 回收。块大小和树节点均为库内实现细节。

### 2.2 位置与选区

文档读取和替换要求 UTF-8 标量边界。交互选区有 anchor 和活动 cursor，两端保存 `TextPosition` 的视觉偏向。水平移动、退格和点击遵循扩展字素边界，CRLF 作为一个换行移动。按 Enter 时沿用所在行的行尾序列，末行沿用上一行，单行文档默认用 LF。软换行的上一视觉行末和下一行首可以对应同一字节偏移，由 `TextAffinity` 区分。矩形、像素 x 和字形数只参与视图计算。[文本位置与导航](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-GRAPHICS-TEXT-SPEC.md#6-文本位置命中与替代文字)

每个视图至少有一个选区，并标记其中一个为主选区。`state.setSelections(selections, primaryIndex)` 合并相交的非空范围、去除同点的重复光标。非空选区覆盖的空光标归入该选区，两个相邻的非空选区保持独立。原主选区所在组保留主身份，相邻两组选区共享原主光标位置时选从该处开始的一组。非空主选区保留方向，其他组合沿用首个非空范围的方向。用户可以以单光标编辑，也可以添加光标或选择下一个匹配项后同时替换。

## 3. 编辑命令、事务与历史

### 3.1 一个修改入口

`CodeEdit(range, text)` 表达一次替换。`document.applyEdits(expectedVersion, edits)` 接受宿主修改。`state.executeEdits(expectedVersion, edits, selectAfter)` 供交互命令调用，额外处理视图只读状态与编辑前后选区。只读视图继续观察共享正文，也可以查找、选择和复制。二者共用同一文档事务。`selectAfter` 可省略，默认把原选区映射到新正文。命令可以通过它读取各项替换得到的新范围，明确选择插入文本或把光标移到末尾。Monaco 的 `getEditOperations` 和 `computeCursorState` 解决的是同一个问题。[Monaco 编辑命令](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L2470) · [缩进命令实例](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/common/commands/shiftCommand.ts)

1. 全部范围引用同一份编辑前正文。先检查版本和字节边界，再按旧起点排序并检查范围冲突。相邻替换合法。同一位置的多次插入、与另一替换同起点的插入，以及位于另一替换内部的插入由调用方先归并。插入若只与前一替换的终点重合，结果排在前一替换之后。
2. 根据旧范围和插入字节数构造本次位置映射。`insertedRange(i)` 以调用方传入顺序返回第 `i` 项在新正文中的范围。纯插入点可选向前或向后黏附。非空替换的两个旧端点对应新范围的两个端点，内部被删位置按黏附方向收敛到一端。相邻替换的共同端点对应两段新内容之间。此处的黏附描述编辑时如何跟随字节，与排版的 `TextAffinity` 分开。
3. 确定最终选区并检查候选端点，再一次发布正文、历史和各视图的映射结果。`selectAfter` 是同步的只读计算。只读视图返回 `ReadOnly`，版本过期返回 `Stale`，范围非法或选区计算出错时整批失败。等值替换保留范围内部的位置。整批正文相同时可更新显式选区，返回 `Unchanged`。有实际修改才记历史、清除旧 redo、发出一次带新版本的正文事件，返回 `Applied`。事件只含实际变化，按旧起点升序排列。

对于被动接收变化的视图，空光标默认跟到插入文本之后。非空选区两端默认排除恰在边缘插入的字节，保留方向和原来选中的内容。自定义装饰可以分别指定两端的黏附方向。

例如，`a中\r\nb` 的 UTF-8 长度为 7。在同一批把 `[0, 1)` 替换为 `xy`、把 `[6, 7)` 替换为 `字`，得到 `xy中\r\n字`。两处新范围分别为 `[0, 2)` 和 `[7, 10)`。命令直接取 `insertedRange(1).end` 就能把光标放在 `字` 后。另一个视图也只收到一次变化。

### 3.2 动作与撤销边界

动作是可命名的用户操作。`state.addAction(id, label, shortcut, enabled, run)` 返回可关闭的登记，快捷键可省略。`enabled` 读取当前视图的焦点、选区和只读状态。快捷键沿已有焦点和 `ShortcutScope` 路由，菜单或宿主按同一 id 触发相同的 `run`，执行前再判断可用性。同一视图中的动作 id 唯一。纯导航动作只改视图，文本动作准备 `CodeEdit` 后提交。多行缩进先对逻辑行去重，多光标删除先归并相交的删除范围。[Scoop 快捷键与输入](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-WINDOW-SPEC.md) · [Monaco 复制行的命令组](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/linesOperations/browser/linesOperations.ts#L63)

一次命令中的批量替换默认形成一个撤销项。连续键入或同方向删除，仅在同一视图、选区连续且编辑种类一致时合并。移动选区、切换焦点、粘贴、组合输入提交和独立动作均划分历史边界。每条记录保存正向与反向编辑，以及交互命令的前后选区。任一可写视图调用 `undo()` 都撤销文档最近一项。执行撤销的视图恢复记录的前选区，重做恢复后选区，其他视图按相应变更映射。纯文档修改没有交互选区时，各视图都按映射更新。焦点留在执行动作的视图。

反向编辑中的范围以修改后的正文为准。如果相邻删除在逆向时落到同一个位置，按原文顺序拼回所删字节并归为一次替换。例如从 `ab` 分别删掉 `[0, 1)` 和 `[1, 2)`，撤销时在偏移 0 插入 `ab`。正向命令仍能分别查询两项的结果范围。

## 4. 可见行排版与绘制

从文档到屏幕要经过三种坐标。**文档位置**用于编辑和装饰。**视觉行及行内位置**由 Tab 展开、输入法临时文本和软换行决定。**视口几何**再计入行号栏、滚动、裁剪和行间控件的高度。点击按相反方向映射。查找、光标和扩展控件均使用同一份映射。[Monaco 视觉行映射](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/common/viewModel/viewModelLines.ts) · [主文本的视口绘制](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/viewParts/viewLines/viewLines.ts)

| 步骤 | 原生实现 |
| --- | --- |
| 找到可见内容 | 用 `ScrollViewport` 管理两个轴。纵向以逻辑行组织高度，先估计未测行，再用实际段落高度和行间占位更新。以视口首个可见正文位置及其屏内 y 为阅读锚点。编辑或重测发生在它上方时校正滚动，让同一内容停在原处 |
| 排版 | 只取视口及邻近逻辑行，按每行内容和局部样式构造 `StyledText`。关闭折行时用 `layoutUnwrapped()` 并允许水平滚动，开启时按正文宽度排版。一个逻辑行内的字形、连字、字体回退和双向文字由同一 `TextLayout` 处理 |
| 命中与导航 | 点击从 `TextLayout.hitTest` 映射回文档。caret 和选区调用同一布局的 `caret`、`selection`，保留双向文本产生的多个矩形。上下移动保留偏好 x，遇到折行或下一逻辑行时在实际排版中定位 |
| 绘制与发布 | 行号栏用首个视觉片段显示逻辑行号。正文区域依次呈现范围背景、选择、文字、下划线和光标，行间子 View 参与正常布局。只有与当前文档及视图设置匹配的 Accepted 帧向输入法和外部查询提供屏幕几何 |

Tab 默认每 4 个逻辑列设一个制表位，从逻辑行首计算，软换行沿用同一计数。含 Tab 的行在显示投影中展开为空格，保存原 Tab 两端与显示区间的对应。普通字素按簇内最大的 `unicodeScalarWidth` 计列，至少一列。实际像素仍由文字排版决定。点在展开区内取较近的端点，复制、删除和撤销操作原始 `\t`。所需的字素分段与字符宽度已有库入口。[Unicode 查询](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.charset/src/unicode.scoop) · [TextLayout 几何](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.graphics.text/src/layout.scoop)

行布局复用依据是该行的正文和显示投影、影响排版的样式、字体集合版本及折行宽度。在前面插一行只改变后续行的文档定位，可继续复用其文字布局。选区背景变化与光标闪烁只失效绘制。当前 `ItemExtentIndex` 支持估算高度、记录实测值和按 y 查行，行数在构造后固定。行数变化时可新建稀疏索引，迁移仍保留且有效的可见行测量，用阅读锚点校正。无需按全文行数创建子 View。未折行的水平范围取已测最大宽度，显露指定位置时先测目标行。单条超长行仍可能需要整行 shaping，其成本单独测量。[高度索引](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.ui.component/src/virtual/extent.scoop) · [UI 布局与帧发布](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-UI-SPEC.md#6-重建布局与呈现)

## 5. 原生输入与无障碍

### 5.1 编辑器给输入法的文本

获得焦点的编辑器自己构造**局部输入文档**。主选区在一行内时，只取该逻辑行的正文。跨行时，从主选区起始行的行首取到结束行的内容末尾，保留中间原有的换行符。软换行、滚动和次选区都不扩大这段上下文。适配器直接用 `lineRange` 和 `read` 从 piece tree 取范围，将片段文本、片段内的方向选区及标记范围交给 `Window.publishTextInputState`。Window 继续处理 AppKit、TSF 和 GTK 的原生输入协议。候选窗位置取当前视图的 caret 屏幕几何，经 `publishTextInputCaret` 单独更新。[窗口输入合同](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-WINDOW-SPEC.md#5-输入与文本) · [快照发布入口](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.window/src/input/text_snapshot.scoop)

Monaco 0.58.0 的浏览器 `EditContext` 路径采用上述整行范围，并把主选区换算为片段内偏移。它的 `textarea` 路径另有策略，例如在 macOS 已关闭读屏支持且选区为空时，可只提供光标前的词或字符。Scoop 借鉴主选区决定上下文的做法，直接接入原生窗口。[Monaco EditContext 的范围计算](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/controller/editContext/native/nativeEditContext.ts#L460) · [Monaco textarea 的上下文选择](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/controller/editContext/textArea/textAreaEditContext.ts#L190)

适配器保留片段起点在 `CodeDocument` 中的 UTF-8 字节偏移。原生侧以片段为自己的坐标空间，AppKit 和 TSF 的 UTF-16 单位由窗口后端转换。举例说，文档 `一\r\nA🙂B\r\n末` 中第二行的起点是字节 5。该行里的 `🙂` 对应原生 UTF-16 范围 `[1, 3)`，窗口交付片段内 UTF-8 范围 `[1, 5)`，适配器据此替换正文 `[6, 10)`。片段以外的显式查询或编辑按窗口原有的越界语义处理。普通的行首退格仍由编辑器删除正文中的上一个换行。[AppKit 范围查询](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.window/native/darwin/text.m) · [TSF 文本范围](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.window/native/windows/text_store.cpp) · [GTK 周边文本](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.window/native/linux/ime.c)

### 5.2 组合输入与切换片段

- 组合开始时记录主选区的原始替换范围、文档版本和片段起点。preedit 只改变活动视图的临时文本。组合串可变长，也可以包含换行，期间维持同一坐标原点。`Commit` 或接受标记文本的 `ClearPreedit` 只提交一次，空 preedit 取消并恢复原选区。
- `TextInputBatch` 中的操作按顺序引用**该批前一步产生的临时片段**。适配器先在局部解释整批，再把已提交的替换映射回旧正文并形成一次可撤销编辑。普通 `CurrentSelection` 键入可以应用到多个选区。组合、显式原生替换和删除周边文本只操作主选区，其他选区随提交映射。
- 切换逻辑行或主选区时，即使新旧行的文字相同，也要为新的坐标映射推进输入 revision。确认原生批次时，先用原片段解释结果并确认 `origin`，随后换片段作为独立的上下文更新。若还有输入可能指向已失效的位置，或另一视图在组合期间修改了共享文档，按已有输入会话重启流程撤下旧投影、重新发布上下文。普通滚动只更新几何。[Window 批次语义](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-WINDOW-SPEC.md#5-输入与文本) · [输入会话路由](https://github.com/scoop-lang/scoop/blob/main/sysroot/src/scoop.surface/src/shared/input/focus.scoop)

### 5.3 辅助技术读取的文档

每个自绘视图通过 `SemanticsHandle.update` 发布可聚焦的多行 `TextField` 语义。读屏端读取该视图的完整编辑内容与主选区，选区使用完整文档坐标，辅助编辑走同一命令入口。查找浮层和批注各自按子 View 发布语义。原生无障碍接口若需要完整 `String`，其物化成本单独测量。精确跨行范围几何待 UI 文本语义接入多份可见布局后另行验收。[UI 文本无障碍接口](https://github.com/scoop-lang/scoop/blob/main/docs/specs/SCOOP-UI-ACCESSIBILITY-SPEC.md#5-文本编辑宿主)

## 6. 扩展点与第一个使用者

扩展使用普通 Scoop 对象。`document.onChange` 订阅正文变化，`state.onSelectionChange` 与 `state.onViewportChange` 分别订阅选区及可见位置变化。登记返回 `Closeable`，由建立登记的组件作用域持有。文档与视图在 owner 线程修改，扩展可以在回调中读取已发布状态，下一次同文档编辑在本次通知结束后发起。异步结果应用前核对文档对象和版本。

| 扩展入口 | 所有权与行为 | 首个用途 |
| --- | --- | --- |
| `document.decorations()`、`state.decorations()` | 得到支持 `set`、`clear`、`close` 的范围集合。文档集合见于所有视图，视图集合仅见于自己。每端可选插入时的黏附方向。事务用同一位置映射更新范围。支持文字前景、背景、下划线与行号栏标记。同一属性先取视图样式，同作用域按登记顺序取最后一个，交互选区使用主题的选择色 | 共享批注标记、各视图独立的查找高亮 |
| `state.addAction`、`state.runAction(id)` | 动作按当前上下文启用，视图关闭或登记关闭后注销 | 查找下一个、替换当前、全部替换 |
| `state.addContentWidget(position, view)` | 文本位置跟随编辑与滚动。只在锚点有已呈现几何时显示，浮在正文上方，不占行高 | 在批注位置显示提示 |
| `state.addOverlayWidget(corner, view)` | 固定在视口一角，独立于正文滚动，可接收焦点和输入 | 查找替换面板 |
| `state.addViewZone(afterLine, view)` | 创建时把逻辑行末转换为随编辑移动的锚点。在该逻辑行最后一个视觉片段后，按子 View 实测高度占位，影响滚动和揭示位置。删除整行时随锚点黏到存留行，登记方可随批注删除它 | 展开一条行间批注 |
| `state.visibleRanges()`、`caretRect(position)`、`revealRange(range)` | 读取最近一次匹配的已呈现几何。离屏或已过期的 caret 返回 `None`。显露请求滚动到目标并在实际排版后校正 | 查找下一个时定位，宿主锚定菜单 |

范围装饰和三种控件位置分别对应 Monaco 的 decorations、content widget、overlay widget 和 view zone。首版用 Scoop 的类型化样式与 `View` 表达它们。宿主可以直接提交一批带前景色的范围，语言查询的接口随实际使用者增加。[Monaco 范围装饰](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/monaco.d.ts#L2793) · [三种视图扩展](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/browser/editorBrowser.ts)

**查找替换作为普通扩展随组件交付。** 首版按非空、区分大小写的字面串查找。扩展从固定快照分片顺序读取，保留跨片段的匹配状态，得到按文档顺序排列的非重叠范围。搜索框使用 overlay，结果保存在视图装饰集合。“下一个”更新主选区并显露目标，到末尾从头继续。“全部替换”把同一快照的匹配一次交给 `executeEdits`，一次撤销恢复整批。查询为空时清除高亮。正文或查询改变时撤下旧结果并重新查询，仅接收文档、版本和查询串仍匹配的结果。焦点移入查找框后，面板仍可调用关联视图的动作，关闭时用 `state.requestFocus()` 恢复正文焦点。[Monaco 查找与替换命令](https://github.com/microsoft/vscode/blob/c132f72ae9f5ff80093e7d722c36f03755865b20/src/vs/editor/contrib/find/browser/findModel.ts)

下面是扩展内“全部替换”的调用。`findLiteral` 属于查找扩展，返回快照中的 `Utf8Range` 列表，空查询返回空列表。编辑器负责只读判断、版本检查、位置映射和撤销。

```kotlin
fun replaceAll(state: CodeEditorState, query: String, replacement: String): CodeEditResult {
    val snapshot = state.document.snapshot()
    val matches = findLiteral(snapshot, query)
    val edits = matches.map { range -> CodeEdit(range, replacement) }
    return state.executeEdits(snapshot.version, edits)
}
```

## 7. 实施顺序与验收

每批实施前先将该批公开合同纳入组件所属规范。只有实际调整底层公开接口时才同步 Window、Graphics 或 UI 规范。以下是拟验收场景。

| 批次 | 可使用的结果 | 关键验证 |
| --- | --- | --- |
| 1. 文档与事务 | 无窗口创建文档，按行或范围读取、批量修改、撤销重做 | 用朴素字节串对照组合编辑。覆盖空文件、尾部换行、跨块拼成或拆开 CRLF、中文与 emoji、相邻替换、冲突整批失败、快照在编辑后稳定及第 3 节的偏移示例 |
| 2. 可编辑视口 | 两个视图编辑同一文档，支持滚动、软换行、键鼠选区、剪贴板、原生输入与基本无障碍动作 | 在左侧键入后从右侧撤销，检查折行、阅读锚点、Tab、字素和双向命中。原生窗口检查普通光标只发布一行、跨行主选区包含完整范围、组合中换行、相同内容的两行切换、迟到批次及另一视图修改时的取消。读屏读取范围继续覆盖文档 |
| 3. 公开扩展 | 查找替换和可展开的行间批注只引用公开接口 | 验证跨 piece 匹配、过期结果、只读视图、批量替换一次撤销、两视图高亮隔离。滚动、改宽、删除锚点所在行、关闭登记后，提示、占位及命中随之更新 |

普通行为用所属 Cone 的 `scoop.test` 覆盖，原生输入、辅助技术和 Accepted 几何用真实窗口验证。性能取十万短行和字节数相近的单条长行，记录打开、键入、滚动、中文组合输入、整批替换及撤销的耗时与峰值内存。对同样的当前行和主选区，增加远处的行数后，传给 IME 的文本字节数应保持相同。超长单行或选区覆盖全文时，片段本身可能很大，这两种情况与完整无障碍值的发布分别测量。
