# MsiBuilder v2.0.0

PyQt6 图形化 Windows MSI 安装包制作工具，内置 WiX Toolset 与 HTML Help Workshop，一键生成 MSI 安装程序。

## v2.0.0 更新内容

- 🐛 修复：生成MSI时缺少 `-ext WixUIExtension` 导致 LGHT0094 报错（WixUI_FeatureTree 无法解析）
- 🌐 新增：中文代码页支持（light -loc zh-CN.wxl + Codepage=936），中文产品名/制造商/路径可正确写入MSI
- 🎁 新增功能：**捆绑包制作**（WiX Burn）
  - 将多个MSI文件捆绑为一个安装exe，按顺序自动安装
  - 内置 Burn 引擎（burn.exe）
  - 支持中文捆绑包名称

## 功能清单

- 自定义 MSI 安装向导左侧 Banner 图片
- 导入产品文件夹/文件，自动打包进 MSI
- 自动扫描并解析目录内 `.reg` 注册表文件
- 独立【导入REG文件】按钮，自动转换为 WiX XML
- 图形化 CHM 帮助文档编辑器
- 复选框控制：是否将 CHM 打包进 MSI
- **捆绑包：多个MSI捆绑为一个exe安装器（新增）**
- 内置 WiX 工具集 + HTML Help Workshop
- 实时编译日志输出

## 系统要求

- Windows 10 / Windows 11（64位）
- 无需预先安装 Python、WiX、HTML Help Workshop

## 下载

- MsiBuilder.exe（单文件，内嵌全部工具）
- 完整源码见仓库 main 分支
