# Scoop Code Editor

`scoop:scoop.ui.editor` 是一个独立的 Scoop 库 Cone。`CodeDocument` 保存 UTF-8 正文和共享撤销历史，`CodeEditorState` 保存一个视图的选区与阅读位置，`codeEditor(state)` 返回可嵌入布局的 `View`。正文由自己的 `Element` 排版、绘制、命中并接收原生输入。

相邻目录的宿主 Cone 可这样声明依赖。

```toml
[dependencies]
"scoop:scoop.ui.editor" = { version = "0.1.0", path = "../scoop-code-editor" }
```

两个视图可以从同一份文档开始，各自拥有焦点、选区、滚动和扩展。下面的左侧视图支持用主修饰键加 F 打开查找面板。滚动条、查找和转到行列面板沿用宿主的 `ThemeSource`。独立挂载时使用内置浅色主题。使用 Scoop UI 控件的应用在 `context(themeSource) { Application().run(host) }` 中挂载。

```kotlin
import scoop.ui.*
import scoop.ui.component.*
import scoop.ui.editor.*

class SplitEditor(scope: ComponentScope) : Component(scope) {
    private val document = CodeDocument("val count = 1\n")
    private val left = scope.resource { CodeEditorState(document) }
    private val right = scope.resource { CodeEditorState(document) }
    private val find = scope.resource { CodeFind(left) }

    public override fun render(): View {
        val first = codeEditor(left)
        val second = codeEditor(right)
        return row {
            item(first) { grow = 1.0 }
            item(second) { grow = 1.0 }
        }
    }
}
```

文档可以脱离窗口使用。`document.applyEdits` 接受同一版本的一批 UTF-8 字节范围替换。视图操作通过 `executeEdits` 加入同一份撤销历史。宿主也可以登记动作、设置范围装饰，或安装跟随文档位置的控件和占据实际行高的批注。详见[公开接口约定](docs/SPEC.md)和[设计](docs/DESIGN.md)。

## 本地验证

本机验证使用包含 Scoop 主仓提交 `13a8be70b` 的工具链和 macOS GUI 组件。该工具链提供 `AXTextArea` 多行语义及自绘视口可用的主题滚动条。[原生无障碍接口](https://github.com/scoop-lang/scoop/pull/219) · [视口滚动条](https://github.com/scoop-lang/scoop/pull/222)

`validation/appkit.sh` 在当前 macOS 桌面会话中以前台应用运行测试，覆盖真实原生输入、拖选、窗口焦点和辅助技术。可按用例或测试容器名称筛选。性能测量为两种文档各启动三个新进程。[本机测量结果](docs/PERFORMANCE.md)

```sh
scoop check . --tests --release
./validation/appkit.sh
./validation/appkit.sh test NativePointerTests ViewportCommandTests
./validation/appkit.sh benchmark
```
