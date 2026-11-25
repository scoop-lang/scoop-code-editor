# 组件合同

## 文档

`CodeDocument(text)` 保存原始 UTF-8 字节。空文档有一行。LF、CRLF 和单 CR 分隔逻辑行，尾部换行产生空行。`version` 从零开始。所有位置和范围使用零起点，范围右端不包含在内。

`read(Utf8Range)` 只复制请求的正文。`lineRange(line, includeBreak)` 默认返回行内容，传入 true 时包括该行分隔符。`positionAt(offset)` 和 `offsetAt(CodePosition(line, column))` 在文档字节和行内字节列之间转换。CRLF 中间位置折合到前一行末。越界或切开 UTF-8 标量的请求抛出 IllegalArgumentException。

`snapshot()` 固定当前版本并封存追加块。不可变红黑树允许快照共享当时的根和片段描述，取得快照的耗时与文档长度无关。快照保留相同的读取与定位能力，`forEachChunk` 按正文顺序交付独立的字符串片段，允许调用方在遍历中修改实时文档。
