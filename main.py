import sys
import os
import re
import subprocess
import uuid
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton,
                             QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                             QFileDialog, QMessageBox, QTextEdit, QCheckBox,
                             QLineEdit, QGroupBox, QListWidget, QListWidgetItem,
                             QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QInputDialog)
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QPixmap

def get_resource_path(relative_path: str) -> str:
    """兼容源码运行 / PyInstaller打包后的资源路径"""
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.abspath(".")
    return os.path.join(base_dir, relative_path)


class RegParser:
    """解析.reg文件，转换为WiX注册表XML节点"""
    def __init__(self):
        self.entries = []  # list of {key_path, values: [{name, type, data}]}

    def parse_file(self, reg_path: str):
        # 自动检测编码：先尝试utf-16（Windows导出格式），失败则用utf-8
        try:
            with open(reg_path, 'r', encoding='utf-16') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(reg_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        return self.parse_content(content)

    def parse_content(self, content: str):
        lines = content.splitlines()
        current_key = None
        self.entries = []
        in_delete_key = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('//'):
                continue
            if line.startswith('Windows Registry Editor') or line.startswith('REGEDIT'):
                continue

            # 键路径行，例如 [HKEY_LOCAL_MACHINE\SOFTWARE\App] 或 [-HKEY_...]
            key_match = re.match(r'^\[(-?)(HKEY_[^\]]+)\]$', line)
            if key_match:
                delete_key = key_match.group(1) == '-'
                current_key = key_match.group(2)
                if delete_key:
                    self.entries.append({'key_path': current_key, 'delete_key': True, 'values': []})
                else:
                    self.entries.append({'key_path': current_key, 'delete_key': False, 'values': []})
                continue

            # 值行，例如 "ValueName"="string value" 或 "ValueName"=dword:00000001 或 "ValueName"=hex:xx,xx
            if current_key and '=' in line and line.startswith('"'):
                name_match = re.match(r'^"([^"]*)"(=)(.*)$', line)
                if name_match:
                    value_name = name_match.group(1)
                    value_data_str = name_match.group(3).strip()
                    vtype, vdata = self._parse_value_data(value_data_str)
                    if self.entries:
                        self.entries[-1]['values'].append({
                            'name': value_name,
                            'type': vtype,
                            'data': vdata
                        })
                continue

            # 默认值行，例如 @"value"  或 =dword:00000001
            if current_key and line.startswith('@='):
                value_data_str = line[2:].strip()
                vtype, vdata = self._parse_value_data(value_data_str)
                if self.entries:
                    self.entries[-1]['values'].append({
                        'name': '',
                        'type': vtype,
                        'data': vdata
                    })

        return self.entries

    def _parse_value_data(self, data_str: str):
        # 字符串: "xxx"
        if data_str.startswith('"') and data_str.endswith('"'):
            return 'string', data_str[1:-1].replace('\\', '\\\\').replace('"', '\\"')
        # DWORD: dword:00000001
        elif data_str.lower().startswith('dword:'):
            return 'dword', '0x' + data_str.split(':')[1].upper()
        # 二进制: hex:xx,xx,xx
        elif data_str.lower().startswith('hex:'):
            hex_data = data_str.split(':', 1)[1].replace(',', '')
            return 'binary', hex_data
        # 多字符串: hex(7):xx,...
        elif data_str.lower().startswith('hex(7):'):
            return 'multiString', data_str.split(':', 1)[1].replace(',', '')
        # 可扩展字符串: hex(2):xx,...
        elif data_str.lower().startswith('hex(2):'):
            return 'expandable', data_str.split(':', 1)[1].replace(',', '')
        else:
            return 'string', data_str.strip('"')

    def to_wix_registry_nodes(self):
        """转换为WiX <RegistryKey> XML节点字符串"""
        xml_parts = []
        hive_map = {
            'HKEY_LOCAL_MACHINE': 'HKLM',
            'HKEY_CURRENT_USER': 'HKCU',
            'HKEY_CLASSES_ROOT': 'HKCR',
            'HKEY_USERS': 'HKU'
        }
        for entry in self.entries:
            full_path = entry['key_path']
            # 分离hive和子路径
            parts = full_path.split('\\', 1)
            hive = hive_map.get(parts[0], parts[0])
            sub_path = parts[1] if len(parts) > 1 else ''
            action = 'delete' if entry.get('delete_key') else 'createAndRemoveOnUninstall'

            xml_parts.append(f'<RegistryKey Root="{hive}" Key="{sub_path}" Action="{action}">')
            for val in entry['values']:
                if val['type'] == 'string':
                    xml_parts.append(
                        f'  <RegistryValue Name="{val["name"]}" Value="{val["data"]}" Type="string" />'
                    )
                elif val['type'] == 'dword':
                    xml_parts.append(
                        f'  <RegistryValue Name="{val["name"]}" Value="{val["data"]}" Type="integer" />'
                    )
                elif val['type'] == 'binary':
                    xml_parts.append(
                        f'  <RegistryValue Name="{val["name"]}" Value="{val["data"]}" Type="binary" />'
                    )
                elif val['type'] == 'multiString':
                    # 多字符串简化处理
                    xml_parts.append(
                        f'  <RegistryValue Name="{val["name"]}" Value="{val["data"]}" Type="multiString" />'
                    )
                elif val['type'] == 'expandable':
                    xml_parts.append(
                        f'  <RegistryValue Name="{val["name"]}" Value="{val["data"]}" Type="expand" />'
                    )
            xml_parts.append('</RegistryKey>')
        return '\n'.join(xml_parts)


class ChmBuilder:
    """CHM帮助文档构建器，调用hhc.exe编译"""
    def __init__(self):
        self.pages = []  # list of {title, filename, html_content}
        self.tree = []  # 目录树结构

    def add_page(self, title: str, html_content: str = None):
        filename = f"page_{len(self.pages)+1}.htm"
        if html_content is None:
            html_content = f"<html><head><title>{title}</title></head><body><h1>{title}</h1></body></html>"
        self.pages.append({'title': title, 'filename': filename, 'html_content': html_content})
        self.tree.append({'title': title, 'filename': filename})

    def generate_project_files(self, output_dir: str, chm_name: str):
        """生成.hhp工程文件和html文件"""
        os.makedirs(output_dir, exist_ok=True)
        # 生成html文件
        for page in self.pages:
            with open(os.path.join(output_dir, page['filename']), 'w', encoding='gbk') as f:
                f.write(page['html_content'])

        # 生成hhp文件
        hhp_content = f'''[OPTIONS]
Compatibility=1.1 or later
Compiled file={chm_name}.chm
Contents file={chm_name}.hhc
Default topic={self.pages[0]["filename"] if self.pages else "index.htm"}
Display compile progress=Yes
Full-text search=Yes
Language=0x804 中文(简体)

[FILES]
'''
        for page in self.pages:
            hhp_content += f"{page['filename']}\n"

        hhp_content += f'''
[INFOTYPES]

[MAP]
'''
        for i, page in enumerate(self.pages):
            hhp_content += f"IDH_{i+1}=0{i+1:04d}\n"

        hhp_path = os.path.join(output_dir, f"{chm_name}.hhp")
        with open(hhp_path, 'w', encoding='gbk') as f:
            f.write(hhp_content)

        # 生成hhc目录文件
        hhc_content = '''<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<HTML>
<HEAD>
<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">
<!-- Sitemap 1.0 -->
</HEAD>
<BODY>
<OBJECT type="text/site properties">
</OBJECT>
<UL>
'''
        for page in self.pages:
            hhc_content += f'  <LI><OBJECT type="text/sitemap">\n'
            hhc_content += f'    <param name="Name" value="{page["title"]}">\n'
            hhc_content += f'    <param name="Local" value="{page["filename"]}">\n'
            hhc_content += f'  </OBJECT>\n'
        hhc_content += '</UL>\n</BODY>\n</HTML>'

        hhc_path = os.path.join(output_dir, f"{chm_name}.hhc")
        with open(hhc_path, 'w', encoding='gbk') as f:
            f.write(hhc_content)

        return hhp_path

    def build_chm(self, output_dir: str, chm_name: str):
        """调用hhc.exe编译chm"""
        hhp_path = self.generate_project_files(output_dir, chm_name)
        hhc_exe = get_resource_path(os.path.join("hhc", "hhc.exe"))
        if not os.path.exists(hhc_exe):
            raise FileNotFoundError(f"找不到hhc.exe: {hhc_exe}")
        result = subprocess.run(
            [hhc_exe, hhp_path],
            capture_output=True, text=True, cwd=output_dir
        )
        chm_output = os.path.join(output_dir, f"{chm_name}.chm")
        if not os.path.exists(chm_output):
            raise RuntimeError(f"CHM编译失败:\n{result.stdout}\n{result.stderr}")
        return chm_output


class MsiBuilderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSI安装包生成工具 - 内嵌WiX")
        self.resize(900, 700)
        self.product_files = []  # 导入的产品文件/文件夹
        self.registry_entries = []  # 注册表项
        self.banner_image_path = None  # 自定义左侧banner图
        self.reg_parser = RegParser()
        self.chm_builder = ChmBuilder()
        self.init_ui()

    def init_ui(self):
        center_widget = QWidget()
        self.setCentralWidget(center_widget)
        main_layout = QVBoxLayout(center_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # 第1页：产品信息
        tab_info = QWidget()
        layout_info = QVBoxLayout(tab_info)
        # 产品名称
        layout_info.addWidget(QLabel("产品名称:"))
        self.edit_product_name = QLineEdit("MyApplication")
        layout_info.addWidget(self.edit_product_name)
        # 版本号
        layout_info.addWidget(QLabel("版本号:"))
        self.edit_version = QLineEdit("1.0.0.0")
        layout_info.addWidget(self.edit_version)
        # 制造商
        layout_info.addWidget(QLabel("制造商:"))
        self.edit_manufacturer = QLineEdit("MyCompany")
        layout_info.addWidget(self.edit_manufacturer)

        # 左侧banner图选择
        group_banner = QGroupBox("安装向导左侧自定义图片")
        layout_banner = QHBoxLayout(group_banner)
        self.label_banner_preview = QLabel("未选择图片")
        self.label_banner_preview.setFixedSize(150, 200)
        self.label_banner_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_banner_preview.setStyleSheet("border: 1px solid #999;")
        btn_select_banner = QPushButton("选择图片...")
        btn_select_banner.clicked.connect(self.select_banner_image)
        layout_banner.addWidget(self.label_banner_preview)
        layout_banner.addWidget(btn_select_banner)
        layout_banner.addStretch()
        layout_info.addWidget(group_banner)
        layout_info.addStretch()

        # 第2页：文件导入
        tab_files = QWidget()
        layout_files = QVBoxLayout(tab_files)
        btn_import_folder = QPushButton("导入产品文件夹")
        btn_import_folder.clicked.connect(self.import_product_folder)
        btn_import_file = QPushButton("导入单个文件")
        btn_import_file.clicked.connect(self.import_product_file)
        self.list_files = QListWidget()
        layout_files.addWidget(btn_import_folder)
        layout_files.addWidget(btn_import_file)
        layout_files.addWidget(QLabel("已导入的产品文件:"))
        layout_files.addWidget(self.list_files)

        # 第3页：注册表
        tab_reg = QWidget()
        layout_reg = QVBoxLayout(tab_reg)
        btn_import_reg = QPushButton("单独导入REG文件")
        btn_import_reg.clicked.connect(self.import_reg_file)
        self.list_reg = QListWidget()
        layout_reg.addWidget(btn_import_reg)
        layout_reg.addWidget(QLabel("已解析的注册表项:"))
        layout_reg.addWidget(self.list_reg)

        # 第4页：CHM帮助文档
        tab_chm = QWidget()
        layout_chm = QVBoxLayout(tab_chm)
        chm_top_layout = QHBoxLayout()
        btn_add_chm_page = QPushButton("添加CHM页面")
        btn_add_chm_page.clicked.connect(self.add_chm_page)
        self.checkbox_include_chm = QCheckBox("将CHM帮助文档打包进MSI")
        chm_top_layout.addWidget(btn_add_chm_page)
        chm_top_layout.addWidget(self.checkbox_include_chm)
        chm_top_layout.addStretch()
        layout_chm.addLayout(chm_top_layout)
        self.list_chm_pages = QListWidget()
        layout_chm.addWidget(self.list_chm_pages)

        # 添加所有标签页
        self.tabs.addTab(tab_info, "产品信息")
        self.tabs.addTab(tab_files, "文件导入")
        self.tabs.addTab(tab_reg, "注册表")
        self.tabs.addTab(tab_chm, "CHM帮助")

        # 底部：生成MSI按钮和日志
        btn_gen_msi = QPushButton("生成MSI安装包")
        btn_gen_msi.setStyleSheet("font-size: 14px; padding: 8px; background-color: #4CAF50; color: white;")
        btn_gen_msi.clicked.connect(self.generate_msi)
        main_layout.addWidget(btn_gen_msi)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(180)
        main_layout.addWidget(QLabel("编译日志:"))
        main_layout.addWidget(self.log_box)

    def log(self, msg: str):
        self.log_box.append(msg)
        QApplication.processEvents()

    def select_banner_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择左侧banner图片", "", "图片文件 (*.bmp *.png *.jpg)")
        if path:
            self.banner_image_path = path
            pixmap = QPixmap(path)
            self.label_banner_preview.setPixmap(pixmap.scaled(150, 200, Qt.AspectRatioMode.KeepAspectRatio))
            self.log(f"已选择banner图片: {path}")

    def import_product_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择产品文件夹")
        if folder:
            self.product_files.append(('folder', folder))
            self.list_files.addItem(f"[文件夹] {folder}")
            self.log(f"导入文件夹: {folder}")
            # 自动扫描里面的reg文件
            for root, dirs, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith('.reg'):
                        reg_path = os.path.join(root, f)
                        self._load_reg_file(reg_path)

    def import_product_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择产品文件")
        for p in paths:
            self.product_files.append(('file', p))
            self.list_files.addItem(f"[文件] {p}")
            self.log(f"导入文件: {p}")
            # 自动识别reg文件
            if p.lower().endswith('.reg'):
                self._load_reg_file(p)

    def import_reg_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择REG文件", "", "REG注册表文件 (*.reg)")
        for p in paths:
            self._load_reg_file(p)

    def _load_reg_file(self, reg_path: str):
        try:
            entries = self.reg_parser.parse_file(reg_path)
            self.registry_entries.extend(entries)
            for entry in entries:
                self.list_reg.addItem(f"[键] {entry['key_path']} ({len(entry['values'])}个值)")
            self.log(f"成功解析REG文件: {reg_path}, 共{len(entries)}个键")
        except Exception as e:
            QMessageBox.warning(self, "REG解析失败", f"文件: {reg_path}\n错误: {str(e)}")

    def add_chm_page(self):
        title, ok = QInputDialog.getText(self, "添加CHM页面", "页面标题:")
        if ok and title:
            self.chm_builder.add_page(title)
            self.list_chm_pages.addItem(title)
            self.log(f"添加CHM页面: {title}")

    def generate_msi(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "保存MSI", "output.msi", "MSI安装包 (*.msi)")
        if not save_path:
            return
        msi_path = Path(save_path)
        work_dir = msi_path.parent / f"{msi_path.stem}_build"
        os.makedirs(work_dir, exist_ok=True)

        product_name = self.edit_product_name.text()
        product_version = self.edit_version.text()
        manufacturer = self.edit_manufacturer.text()
        upgrade_code = str(uuid.uuid4())
        product_code = str(uuid.uuid4())

        try:
            self.log("===== 开始生成MSI =====")
            self.log(f"产品名称: {product_name}")
            self.log(f"版本: {product_version}")

            # 如果勾选了CHM，先编译CHM
            chm_path = None
            if self.checkbox_include_chm.isChecked() and self.chm_builder.pages:
                self.log("正在编译CHM帮助文档...")
                chm_path = self.chm_builder.build_chm(str(work_dir), "help")
                self.log(f"CHM编译完成: {chm_path}")

            # 收集所有文件列表
            file_entries = []  # (source_path, target_dir)
            for ftype, fpath in self.product_files:
                if ftype == 'file':
                    file_entries.append((fpath, '.'))
                elif ftype == 'folder':
                    for root, dirs, files in os.walk(fpath):
                        rel_dir = os.path.relpath(root, fpath)
                        for f in files:
                            full = os.path.join(root, f)
                            file_entries.append((full, rel_dir))

            if chm_path:
                file_entries.append((chm_path, 'docs'))

            # 生成WiX XML
            self.log("生成WiX工程文件...")
            wxs_content = self._generate_wxs(
                product_name, product_version, manufacturer,
                product_code, upgrade_code, file_entries
            )
            wxs_path = work_dir / "product.wxs"
            with open(wxs_path, 'w', encoding='utf-8') as f:
                f.write(wxs_content)

            # 调用candle
            candle_exe = get_resource_path(os.path.join("wix", "candle.exe"))
            light_exe = get_resource_path(os.path.join("wix", "light.exe"))

            if not os.path.exists(candle_exe):
                raise FileNotFoundError(
                    f"找不到内嵌candle.exe: {candle_exe}\n"
                    "请将WiX v3.11的bin目录下所有exe/dll复制到 wix 文件夹后重新打包。"
                )

            self.log("运行 candle 编译...")
            candle_cmd = [candle_exe, str(wxs_path), "-o", str(work_dir) + "\\"]
            ret = subprocess.run(candle_cmd, capture_output=True, text=True, cwd=str(work_dir))
            self.log(ret.stdout)
            if ret.returncode != 0:
                raise RuntimeError(f"candle失败:\n{ret.stderr}")

            wixobj_path = work_dir / "product.wixobj"
            self.log("运行 light 链接...")
            light_cmd = [light_exe, str(wixobj_path), "-o", str(msi_path)]
            ret2 = subprocess.run(light_cmd, capture_output=True, text=True, cwd=str(work_dir))
            self.log(ret2.stdout)
            if ret2.returncode != 0:
                raise RuntimeError(f"light失败:\n{ret2.stderr}")

            QMessageBox.information(self, "成功", f"MSI生成完成！\n{msi_path}")
            self.log("===== MSI生成成功 =====")

        except Exception as e:
            self.log(f"错误: {str(e)}")
            QMessageBox.critical(self, "生成失败", str(e))

    def _generate_wxs(self, product_name, version, manufacturer, product_code, upgrade_code, file_entries):
        """生成完整的WiX wxs文件"""
        # 生成文件组件
        component_xml = []
        component_refs = []
        file_id = 1
        for src_path, rel_dir in file_entries:
            fname = os.path.basename(src_path)
            comp_id = f"cmp{file_id}"
            # 处理目录结构
            dir_ref = "INSTALLFOLDER"
            if rel_dir and rel_dir != '.':
                # 简化：所有子目录都放在INSTALLFOLDER下
                dir_ref = "INSTALLFOLDER"
            component_xml.append(f'''      <Component Id="{comp_id}" Guid="{str(uuid.uuid4())}">
        <File Id="file{file_id}" Source="{src_path}" KeyPath="yes" />
      </Component>''')
            component_refs.append(f"      <ComponentRef Id=\"{comp_id}\" />")
            file_id += 1

        # 注册表XML
        reg_xml = self.reg_parser.to_wix_registry_nodes() if self.registry_entries else ""

        # banner图
        banner_xml = ""
        if self.banner_image_path and os.path.exists(self.banner_image_path):
            # WiX需要两个bmp：57x35 (InfoIcon) 和 493x58 (WixUI_Bmp_Banner)
            banner_xml = f'''
    <WixVariable Id="WixUIBannerBmp" Value="{self.banner_image_path}" />
    <WixVariable Id="WixUIDialogBmp" Value="{self.banner_image_path}" />
'''

        wxs = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="{product_code}" Name="{product_name}" Language="2052" Version="{version}" Manufacturer="{manufacturer}" UpgradeCode="{upgrade_code}">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />
    <MajorUpgrade DowngradeErrorMessage="已安装更新版本的{product_name}。" />
    <MediaTemplate />
{banner_xml}
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="{product_name}" />
      </Directory>
    </Directory>

    <Feature Id="ProductFeature" Title="{product_name}" Level="1">
{chr(10).join(component_refs)}
    </Feature>

    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
{chr(10).join(component_xml)}
    </ComponentGroup>

    <UI>
      <UIRef Id="WixUI_FeatureTree" />
      <UIRef Id="WixUI_ErrorProgressText" />
    </UI>
  </Product>
</Wix>'''
        # 把注册表节点插入到ProductComponents里
        if reg_xml:
            wxs = wxs.replace(
                '    </ComponentGroup>',
                f'      {reg_xml}\n    </ComponentGroup>'
            )
        return wxs


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MsiBuilderApp()
    win.show()
    sys.exit(app.exec())
