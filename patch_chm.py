# -*- coding: utf-8 -*-
import io, sys

p = r"D:\sb\MsiBuilder\main.py"
with io.open(p, "r", encoding="utf-8") as f:
    src = f.read()

# ========== 1. 顶部加 shutil/tempfile ==========
old_imp = "import sys\nimport os\nimport re\nimport subprocess\nimport uuid\n"
new_imp = "import sys\nimport os\nimport re\nimport subprocess\nimport uuid\nimport shutil\nimport tempfile\n"
assert old_imp in src, "import block not found"
src = src.replace(old_imp, new_imp, 1)

# ========== 2. 替换 ChmBuilder 类（从 class ChmBuilder 到 build_chm return chm_output 结束） ==========
start = src.index("class ChmBuilder:")
end = src.index("class MsiBuilderApp")
new_chm = r"""class ChmBuilder:
    # CHM帮助文档构建器，调用hhc.exe编译
    def __init__(self):
        self.pages = []  # list of {title, filename, html_content}
        self.images = {}  # img_name -> 源文件路径，编译时复制进工程目录

    def add_page(self, title: str, html_content: str = None):
        filename = f"page_{len(self.pages)+1}.htm"
        if html_content is None:
            html_content = f"<html><head><title>{title}</title></head><body><h1>{title}</h1></body></html>"
        self.pages.append({'title': title, 'filename': filename, 'html_content': html_content})

    def generate_project_files(self, output_dir: str, chm_name: str):
        # 生成.hhp工程文件、html文件，并复制图片进工程目录
        os.makedirs(output_dir, exist_ok=True)
        for page in self.pages:
            try:
                with open(os.path.join(output_dir, page['filename']), 'w', encoding='gbk', errors='replace') as f:
                    f.write(page['html_content'])
            except Exception:
                with open(os.path.join(output_dir, page['filename']), 'w', encoding='utf-8') as f:
                    f.write(page['html_content'])
        # 复制图片资源
        for img_name, src_path in self.images.items():
            try:
                shutil.copy2(src_path, os.path.join(output_dir, img_name))
            except Exception:
                pass

        files_lines = ""
        for page in self.pages:
            files_lines += f"{page['filename']}\\n"
        for img_name in self.images:
            files_lines += f"{img_name}\\n"

        hhp_content = f'''[OPTIONS]
Compatibility=1.1 or later
Compiled file={chm_name}.chm
Contents file={chm_name}.hhc
Default topic={self.pages[0]["filename"] if self.pages else "index.htm"}
Display compile progress=Yes
Full-text search=Yes
Language=0x804 中文(简体)

[FILES]
{files_lines}[INFOTYPES]

[MAP]
'''
        for i, page in enumerate(self.pages):
            hhp_content += f"IDH_{i+1}=0{i+1:04d}\\n"

        hhp_path = os.path.join(output_dir, f"{chm_name}.hhp")
        with open(hhp_path, 'w', encoding='gbk') as f:
            f.write(hhp_content)

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
            hhc_content += f'  <LI><OBJECT type="text/sitemap">\\n'
            hhc_content += f'    <param name="Name" value="{page["title"]}">\\n'
            hhc_content += f'    <param name="Local" value="{page["filename"]}">\\n'
            hhc_content += f'  </OBJECT>\\n'
        hhc_content += '</UL>\\n</BODY>\\n</HTML>'

        hhc_path = os.path.join(output_dir, f"{chm_name}.hhc")
        with open(hhc_path, 'w', encoding='gbk') as f:
            f.write(hhc_content)

        return hhp_path

    def build_chm(self, output_dir: str, chm_name: str):
        # 调用hhc.exe编译chm
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
            raise RuntimeError(f"CHM编译失败:\\n{result.stdout}\\n{result.stderr}")
        return chm_output


"""
src = src[:start] + new_chm + src[end:]

# ========== 3. 替换 CHM 标签页 UI ==========
old_chm_ui = '''        # 第4页：CHM帮助文档
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
'''
new_chm_ui = '''        # 第4页：CHM帮助文档
        tab_chm = QWidget()
        layout_chm = QVBoxLayout(tab_chm)
        chm_top_layout = QHBoxLayout()
        btn_add_chm_page = QPushButton("添加CHM页面")
        btn_add_chm_page.clicked.connect(self.add_chm_page)
        btn_del_chm_page = QPushButton("删除选中页面")
        btn_del_chm_page.clicked.connect(self.remove_chm_page)
        btn_insert_chm_image = QPushButton("插入图片")
        btn_insert_chm_image.clicked.connect(self.insert_chm_image)
        btn_compile_chm = QPushButton("单独编译CHM测试")
        btn_compile_chm.setStyleSheet("padding:4px 10px; background-color:#607D8B; color:white;")
        btn_compile_chm.clicked.connect(self.compile_chm_test)
        self.checkbox_include_chm = QCheckBox("将CHM打包进MSI")
        chm_top_layout.addWidget(btn_add_chm_page)
        chm_top_layout.addWidget(btn_del_chm_page)
        chm_top_layout.addWidget(btn_insert_chm_image)
        chm_top_layout.addWidget(btn_compile_chm)
        chm_top_layout.addWidget(self.checkbox_include_chm)
        chm_top_layout.addStretch()
        layout_chm.addLayout(chm_top_layout)

        chm_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list_chm_pages = QListWidget()
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("页面标题:"))
        self.edit_chm_title = QLineEdit()
        self.edit_chm_title.editingFinished.connect(self.save_current_chm_page)
        right_layout.addWidget(self.edit_chm_title)
        right_layout.addWidget(QLabel("页面正文（直接输入文字，点"插入图片"可加入图片）:"))
        self.edit_chm_body = QTextEdit()
        self.edit_chm_body.textChanged.connect(self.save_current_chm_page)
        right_layout.addWidget(self.edit_chm_body)
        chm_splitter.addWidget(self.list_chm_pages)
        chm_splitter.addWidget(right_panel)
        chm_splitter.setSizes([260, 640])
        layout_chm.addWidget(chm_splitter)
        self.list_chm_pages.currentRowChanged.connect(self.on_chm_page_changed)

        # 添加所有标签页
        self.tabs.addTab(tab_info, "产品信息")
        self.tabs.addTab(tab_files, "文件导入")
        self.tabs.addTab(tab_reg, "注册表")
        self.tabs.addTab(tab_chm, "CHM帮助")
'''
assert old_chm_ui in src, "old CHM UI block not found"
src = src.replace(old_chm_ui, new_chm_ui, 1)

# ========== 4. 去掉重复的 addTab 块，只保留 bundle ==========
old_dup = '''        # 添加所有标签页
        self.tabs.addTab(tab_info, "产品信息")
        self.tabs.addTab(tab_files, "文件导入")
        self.tabs.addTab(tab_reg, "注册表")
        self.tabs.addTab(tab_chm, "CHM帮助")
        self.tabs.addTab(tab_bundle, "捆绑包")
'''
new_dup = '''        self.tabs.addTab(tab_bundle, "捆绑包")
'''
assert old_dup in src, "duplicate addTab block not found"
src = src.replace(old_dup, new_dup, 1)

# ========== 5. 替换 add_chm_page 方法，新增CHM辅助方法 ==========
old_methods = '''    def add_chm_page(self):
        title, ok = QInputDialog.getText(self, "添加CHM页面", "页面标题:")
        if ok and title:
            self.chm_builder.add_page(title)
            self.list_chm_pages.addItem(title)
            self.log(f"添加CHM页面: {title}")
'''
new_methods = '''    def add_chm_page(self):
        title, ok = QInputDialog.getText(self, "添加CHM页面", "页面标题:")
        if ok and title:
            self.save_current_chm_page()
            self.chm_builder.add_page(title)
            self.list_chm_pages.addItem(title)
            self.list_chm_pages.setCurrentRow(self.list_chm_pages.count() - 1)
            self.log(f"添加CHM页面: {title}")

    def on_chm_page_changed(self, row):
        if row < 0 or row >= len(self.chm_builder.pages):
            self.edit_chm_title.blockSignals(True)
            self.edit_chm_title.clear()
            self.edit_chm_title.blockSignals(False)
            self.edit_chm_body.blockSignals(True)
            self.edit_chm_body.clear()
            self.edit_chm_body.blockSignals(False)
            return
        page = self.chm_builder.pages[row]
        self.edit_chm_title.blockSignals(True)
        self.edit_chm_title.setText(page['title'])
        self.edit_chm_title.blockSignals(False)
        self.edit_chm_body.blockSignals(True)
        self.edit_chm_body.setHtml(page['html_content'])
        self.edit_chm_body.blockSignals(False)

    def save_current_chm_page(self):
        row = self.list_chm_pages.currentRow()
        if row < 0 or row >= len(self.chm_builder.pages):
            return
        title = self.edit_chm_title.text().strip()
        if not title:
            title = self.chm_builder.pages[row]['title']
        self.chm_builder.pages[row]['title'] = title
        self.chm_builder.pages[row]['html_content'] = self.edit_chm_body.toHtml()
        item = self.list_chm_pages.currentItem()
        if item is not None:
            item.setText(title)

    def remove_chm_page(self):
        row = self.list_chm_pages.currentRow()
        if row < 0:
            return
        title = self.chm_builder.pages[row]['title']
        del self.chm_builder.pages[row]
        self.list_chm_pages.takeItem(row)
        self.log(f"已删除CHM页面: {title}")

    def insert_chm_image(self):
        if self.list_chm_pages.currentRow() < 0:
            QMessageBox.information(self, "提示", "请先添加并选中一个CHM页面")
            return
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not path:
            return
        img_name = f"img_{len(self.chm_builder.images)+1}_{os.path.basename(path)}"
        self.chm_builder.images[img_name] = path
        self.edit_chm_body.insertHtml(f'<img src="{img_name}" style="max-width:100%;">')
        self.save_current_chm_page()
        self.log(f"插入图片: {path}")

    def compile_chm_test(self):
        try:
            self.save_current_chm_page()
            if not self.chm_builder.pages:
                QMessageBox.information(self, "提示", "请先添加CHM页面")
                return
            out_dir = os.path.join(tempfile.gettempdir(), "msibuilder_chm_test")
            if os.path.exists(out_dir):
                shutil.rmtree(out_dir, ignore_errors=True)
            os.makedirs(out_dir, exist_ok=True)
            chm_path = self.chm_builder.build_chm(out_dir, "help")
            self.log(f"CHM编译成功: {chm_path}")
            QMessageBox.information(self, "成功", f"CHM已编译完成:\\n{chm_path}\\n\\n所在文件夹已打开，双击help.chm查看效果")
            os.startfile(out_dir)
        except Exception as e:
            self.log(f"CHM编译失败: {str(e)}")
            QMessageBox.warning(self, "编译失败", str(e))
'''
assert old_methods in src, "old add_chm_page not found"
src = src.replace(old_methods, new_methods, 1)

with io.open(p, "w", encoding="utf-8") as f:
    f.write(src)
print("PATCH OK, total length:", len(src))
