# Scoop 原生代码编辑器

`scoop.ui.editor` 是可以嵌入 Scoop UI 布局的原生代码编辑器组件。正文、视图和编辑命令由组件拥有。一份文档可以供多个视图同时编辑。

[组件设计](docs/DESIGN.md) · [公开合同](docs/SPEC.md)

在仓库根目录用 `scoop test . --release` 运行本地 Cone 测试。

在 macOS 运行 `validation/appkit.sh` 可在同一套测试中启用 AppKit 协议探针，验证原生输入法和无障碍接口。脚本把探针编译在临时目录，组件库直接使用 Scoop Window 的平台后端。
