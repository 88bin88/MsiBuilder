# MSI Builder

Windows MSI安装包可视化生成工具，内嵌WiX Toolset，无需用户单独安装WiX即可生成MSI安装包。

## 功能特性

- ✅ 可视化配置产品名称、版本、制造商信息
- ✅ 自定义安装向导左侧banner图片
- ✅ 导入产品文件/文件夹，自动打包进MSI
- ✅ 自动识别导入目录中的.reg文件，自动转换为注册表配置
- ✅ 单独导入.reg文件按钮，可视化管理注册表项
- ✅ 内置CHM帮助文档编辑器，可视化添加页面
- ✅ 可选将CHM帮助文档自动打包进MSI
- ✅ 内嵌WiX工具集，目标电脑无需安装WiX
- ✅ 一键生成MSI安装包

## 开发环境准备

1. 安装Python 3.10 ~ 3.11（推荐64位）
2. 安装依赖：
   ```cmd
   pip install pyqt6 pyinstaller
   ```
3. 下载WiX Toolset v3.11：https://github.com/wixtoolset/wix3/releases
4. 将WiX的bin目录下所有.exe和.dll文件复制到 `wix/` 文件夹
5. 下载HTML Help Workshop，将hhc.exe等文件复制到 `hhc/` 文件夹

## 本地运行测试

```cmd
python main.py
```

## 打包成单exe

双击运行 `build.bat`，打包完成后exe在 `dist/MsiBuilder.exe`。

## 使用说明

1. **产品信息页**：填写产品名称、版本号、制造商，选择左侧banner图片
2. **文件导入页**：导入要打包的产品文件/文件夹，自动扫描.reg文件
3. **注册表页**：单独导入.reg文件，查看已解析的注册表项
4. **CHM帮助页**：添加CHM页面，勾选是否打包进MSI
5. 点击"生成MSI安装包"，选择保存位置即可

## 注意事项

- 仅支持Windows系统
- WiX v3依赖.NET Framework 3.5，部分精简版系统可能需要开启
- 不要将wix/和hhc/目录直接上传GitHub（版权问题），构建者自行下载放入
- 单exe体积较大，因为内嵌了WiX和HHW工具集
