# MsiBuilder v3.0.0

PyQt6 图形化 Windows MSI 安装包制作工具，内置 WiX Toolset 与 HTML Help Workshop。

## v3.0.0 更新内容

- 📝 **CHM帮助页支持正文编辑**：选中左侧页面即可直接在右侧编辑标题和正文内容
- 🖼️ **CHM支持插入图片**：一键选择本地图片插入正文，图片自动编译进CHM文件
- 🧪 **CHM单独编译测试按钮**：不生成MSI也能单独编译CHM并打开预览
- 🗑️ **CHM页面删除按钮**：可删除不再需要的帮助页
- 🐛 修复：标签页重复显示CHM帮助页的bug
- 🎨 CHM页布局改为左右分栏（页面列表 + 编辑区）

## 功能清单

- 自定义 MSI 安装向导左侧 Banner 图片
- 导入产品文件夹/文件，自动打包进 MSI
- 自动扫描目录内 `.reg` 注册表文件
- 独立【导入REG文件】按钮，自动转 WiX XML
- 图形化 CHM 帮助文档编辑器（标题+正文+图片，v3新增）
- 复选框控制：是否将 CHM 打包进 MSI
- 捆绑包制作（WiX Burn）：多个MSI捆绑为一个exe安装器
- 中文产品名/路径完整支持
- 内置 WiX 工具集 + HTML Help Workshop
- 实时编译日志输出

## 系统要求

- Windows 10 / Windows 11（64位）
- 无需预装 Python、WiX、HTML Help Workshop
