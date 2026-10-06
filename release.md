# MsiBuilder v1.0.0

PyQt6 图形化 Windows MSI 安装包制作工具，内置 WiX Toolset 与 HTML Help Workshop，一键生成 MSI 安装程序。

## 功能清单

- 自定义 MSI 安装向导左侧 Banner 图片
- 导入产品文件夹/文件，自动打包进 MSI
- 导入文件夹时自动扫描并解析目录内 `.reg` 注册表文件
- 独立【导入REG文件】按钮，单独添加注册表项，自动转换为 WiX XML
- 图形化 CHM 帮助文档编辑器，可视化添加页面
- 复选框控制：是否将编译后的 CHM 打包进 MSI
- 内置 WiX 工具集（candle.exe / light.exe），目标电脑无需安装 WiX
- 内置 HTML Help Workshop（hhc.exe），直接编译 CHM
- 实时编译日志输出

## 系统要求

- Windows 10 / Windows 11（64位）
- 无需预先安装 Python、WiX Toolset、HTML Help Workshop

## 使用方法

1. 双击运行 MsiBuilder.exe
2. 产品信息页：填写产品名称、版本、制造商，可自定义安装向导图片
3. 文件导入页：导入需要打包的产品文件/文件夹
4. 注册表页：导入 .reg 文件（可选）
5. CHM帮助页：添加帮助页面，勾选打包进 MSI（可选）
6. 点击"生成MSI安装包"，选择保存位置

## 下载

- MsiBuilder.exe（单文件，内嵌全部工具）
- 完整源码见仓库 main 分支
