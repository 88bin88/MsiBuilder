# -*- coding: utf-8 -*-
import io, shutil
p = r'D:\sb\MsiBuilder\main.py'
bak = r'D:\sb\MsiBuilder\main.py.bak_v310_tree'
shutil.copy2(p, bak)
s = io.open(p, encoding='utf-8').read()

# ========== 1. ChmBuilder.__init__ 加 tree 和计数器 ==========
old1 = """class ChmBuilder:
    # CHM帮助文档构建器，调用hhc.exe编译
    def __init__(self):
        self.pages = []  # list of {title, filename, html_content}
        self.images = {}  # img_name -> 源文件路径，编译时复制进工程目录"""
new1 = """class ChmBuilder:
    # CHM帮助文档构建器，调用hhc.exe编译
    def __init__(self):
        self.pages = []  # list of {title, filename, html_content}
        self.images = {}  # img_name -> 源文件路径，编译时复制进工程目录
        self.tree = []  # 多级目录树: [{type:'folder',title,children:[...]},{type:'page',title,filename}]
        self._page_counter = 0  # 页面文件计数器（删除页面后也不撞名）"""
assert old1 in s, "1"
s = s.replace(old1, new1, 1)

# ========== 2. add_page 改造 + 新增 add_folder / 辅助方法 ==========
old2 = """    def add_page(self, title: str, html_content: str = None):
        filename = f"page_{len(self.pages)+1}.htm"
        if html_content is None:
            html_content = f"<html><head><title>{title}</title></head><body><h1>{title}</h1></body></html>"
        self.pages.append({'title': title, 'filename': filename, 'html_content': html_content})"""
new2 = """    def add_page(self, title: str, html_content: str = None):
        self._page_counter += 1
        filename = f"page_{self._page_counter}.htm"
        if html_content is None:
            html_content = f'<html><head><meta charset="UTF-8"><title>{title}</title></head><body><h1>{title}</h1></body></html>'
        self.pages.append({'title': title, 'filename': filename, 'html_content': html_content})
        return len(self.pages) - 1

    def add_folder(self, title: str, parent: dict = None):
        \"\"\"添加目录节点（支持多级嵌套）\"\"\"
        node = {'type': 'folder', 'title': title, 'children': []}
        if parent is not None:
            parent.setdefault('children', []).append(node)
        else:
            self.tree.append(node)
        return node

    def _find_page(self, filename: str):
        for p in self.pages:
            if p['filename'] == filename:
                return p
        return None

    def _find_first_page(self, nodes=None):
        \"\"\"递归找第一个页面节点（用于窗口标题和默认主题）\"\"\"
        if nodes is None:
            nodes = self.tree
        for node in nodes:
            if node['type'] == 'page':
                return node
            if node['type'] == 'folder':
                found = self._find_first_page(node.get('children', []))
                if found:
                    return found
        return None"""
assert old2 in s, "2"
s = s.replace(old2, new2, 1)

# ========== 3. generate_project_files 的 window_title / Default topic ==========
old3 = """        window_title = self.pages[0]["title"] if self.pages else chm_name
        hhp_content = f\'\'\'[OPTIONS]
Compatibility=1.1 or later
Compiled file={chm_name}.chm
Contents file={chm_name}.hhc
Default topic={self.pages[0]["filename"] if self.pages else "index.htm"}"""
new3 = """        first_node = self._find_first_page()
        if first_node:
            first_page = self._find_page(first_node['filename'])
            window_title = first_page['title'] if first_page else chm_name
            default_topic = first_node['filename']
        else:
            window_title = self.pages[0]["title"] if self.pages else chm_name
            default_topic = self.pages[0]["filename"] if self.pages else "index.htm"
        hhp_content = f\'\'\'[OPTIONS]
Compatibility=1.1 or later
Compiled file={chm_name}.chm
Contents file={chm_name}.hhc
Default topic={default_topic}"""
assert old3 in s, "3"
s = s.replace(old3, new3, 1)

# ========== 4. hhc 生成改为递归目录树 ==========
old4 = """        for page in self.pages:
            hhc_content += f'  <LI><OBJECT type="text/sitemap">\\n'
            hhc_content += f'    <param name="Name" value="{page["title"]}">\\n'
            hhc_content += f'    <param name="Local" value="{page["filename"]}">\\n'
            hhc_content += f'  </OBJECT>\\n'
        hhc_content += '</UL>\\n</BODY>\\n</HTML>'"""
new4 = """        if not self.tree:
            # 兼容旧数据：无目录树时按扁平列表生成
            for page in self.pages:
                hhc_content += f'  <LI><OBJECT type="text/sitemap">\\n'
                hhc_content += f'    <param name="Name" value="{page["title"]}">\\n'
                hhc_content += f'    <param name="Local" value="{page["filename"]}">\\n'
                hhc_content += f'  </OBJECT>\\n'
        else:
            hhc_content += self._hhc_tree_content()
        hhc_content += '</UL>\\n</BODY>\\n</HTML>'"""
assert old4 in s, "4"
s = s.replace(old4, new4, 1)

# ========== 4b. 在 build_chm 前插入递归生成方法 ==========
old4b = """    def build_chm(self, output_dir: str, chm_name: str):"""
new4b = """    def _hhc_tree_content(self, nodes=None, indent=1):
        \"\"\"递归生成多级目录树对应的hhc HTML片段\"\"\"
        if nodes is None:
            nodes = self.tree
        pad = '  ' * indent
        lines = []
        for node in nodes:
            if node['type'] == 'folder':
                lines.append(f'{pad}<LI> <OBJECT type="text/sitemap">')
                lines.append(f'{pad}  <param name="Name" value="{node["title"]}">')
                lines.append(f'{pad}</OBJECT>')
                children = node.get('children', [])
                if children:
                    lines.append(f'{pad}<UL>')
                    sub = self._hhc_tree_content(children, indent + 1)
                    if sub:
                        lines.extend(sub.split('\\n'))
                    lines.append(f'{pad}</UL>')
            else:
                page = self._find_page(node['filename'])
                if page is None:
                    continue
                lines.append(f'{pad}<LI> <OBJECT type="text/sitemap">')
                lines.append(f'{pad}  <param name="Name" value="{node["title"]}">')
                lines.append(f'{pad}  <param name="Local" value="{page["filename"]}">')
                lines.append(f'{pad}</OBJECT>')
        return '\\n'.join(lines)

    def build_chm(self, output_dir: str, chm_name: str):"""
assert old4b in s, "4b"
s = s.replace(old4b, new4b, 1)

# ========== 5. GUI: init_ui CHM 部分 ==========
old5 = """        btn_add_chm_page = QPushButton("添加CHM页面")
        btn_add_chm_page.clicked.connect(self.add_chm_page)
        btn_del_chm_page = QPushButton("删除选中页面")
        btn_del_chm_page.clicked.connect(self.remove_chm_page)"""
new5 = """        btn_add_chm_page = QPushButton("添加CHM页面")
        btn_add_chm_page.clicked.connect(self.add_chm_page)
        btn_add_chm_folder = QPushButton("添加子目录")
        btn_add_chm_folder.clicked.connect(self.add_chm_folder)
        btn_del_chm_page = QPushButton("删除选中节点")
        btn_del_chm_page.clicked.connect(self.remove_chm_page)"""
assert old5 in s, "5"
s = s.replace(old5, new5, 1)

old5b = """        chm_top_layout.addWidget(btn_add_chm_page)
        chm_top_layout.addWidget(btn_del_chm_page)"""
new5b = """        chm_top_layout.addWidget(btn_add_chm_page)
        chm_top_layout.addWidget(btn_add_chm_folder)
        chm_top_layout.addWidget(btn_del_chm_page)"""
assert old5b in s, "5b"
s = s.replace(old5b, new5b, 1)

old5c = """        self.list_chm_pages = QListWidget()"""
new5c = """        self.list_chm_pages = QTreeWidget()
        self.list_chm_pages.setHeaderHidden(True)"""
assert old5c in s, "5c"
s = s.replace(old5c, new5c, 1)

old5d = """        self.list_chm_pages.currentRowChanged.connect(self.on_chm_page_changed)"""
new5d = """        self.list_chm_pages.currentItemChanged.connect(self.on_chm_page_changed)"""
assert old5d in s, "5d"
s = s.replace(old5d, new5d, 1)

# ========== 6. GUI 方法改造 ==========
old6 = """    def add_chm_page(self):
        title, ok = QInputDialog.getText(self, "添加CHM页面", "页面标题:")
        if ok and title:
            self.save_current_chm_page()
            self.chm_builder.add_page(title)
            self.list_chm_pages.addItem(title)
            self.list_chm_pages.setCurrentRow(self.list_chm_pages.count() - 1)
            self.log(f"添加CHM页面: {title}")"""
new6 = """    def _sync_tree_from_widget(self):
        \"\"\"从QTreeWidget重建ChmBuilder.tree（目录树唯一同步入口）\"\"\"
        def build(node_item):
            ntype = node_item.data(0, Qt.ItemDataRole.UserRole)
            title = node_item.text(0)
            if ntype == 'folder':
                return {'type': 'folder', 'title': title,
                        'children': [build(node_item.child(i)) for i in range(node_item.childCount())]}
            return {'type': 'page', 'title': title,
                    'filename': node_item.data(0, Qt.ItemDataRole.UserRole + 1)}
        self.chm_builder.tree = [
            build(self.list_chm_pages.topLevelItem(i))
            for i in range(self.list_chm_pages.topLevelItemCount())
        ]

    def _find_chm_page_by_filename(self, filename):
        for p in self.chm_builder.pages:
            if p['filename'] == filename:
                return p
        return None

    def _chm_item_parent(self):
        \"\"\"返回新节点应挂载的父item（选中目录挂它下，选中页面挂它父级，无选中挂根）\"\"\"
        current = self.list_chm_pages.currentItem()
        if current is not None:
            if current.data(0, Qt.ItemDataRole.UserRole) == 'folder':
                return current
            p = current.parent()
            if p is not None:
                return p
        return None

    def add_chm_page(self):
        title, ok = QInputDialog.getText(self, "添加CHM页面", "页面标题:")
        if ok and title:
            self.save_current_chm_page()
            page_index = self.chm_builder.add_page(title)
            filename = self.chm_builder.pages[page_index]['filename']
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, 'page')
            item.setData(0, Qt.ItemDataRole.UserRole + 1, filename)
            parent = self._chm_item_parent()
            if parent is not None:
                parent.addChild(item)
            else:
                self.list_chm_pages.addTopLevelItem(item)
            self.list_chm_pages.setCurrentItem(item)
            self._sync_tree_from_widget()
            self.log(f"添加CHM页面: {title}")

    def add_chm_folder(self):
        title, ok = QInputDialog.getText(self, "添加子目录", "目录名称:")
        if ok and title:
            self.save_current_chm_page()
            item = QTreeWidgetItem([title])
            item.setData(0, Qt.ItemDataRole.UserRole, 'folder')
            parent = self._chm_item_parent()
            if parent is not None:
                parent.addChild(item)
            else:
                self.list_chm_pages.addTopLevelItem(item)
            self.list_chm_pages.setCurrentItem(item)
            self._sync_tree_from_widget()
            self.log(f"添加子目录: {title}")"""
assert old6 in s, "6"
s = s.replace(old6, new6, 1)

old7 = """    def on_chm_page_changed(self, row):
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
        self.edit_chm_body.blockSignals(False)"""
new7 = """    def on_chm_page_changed(self, item, prev_item=None):
        self.edit_chm_title.blockSignals(True)
        self.edit_chm_title.clear()
        self.edit_chm_title.blockSignals(False)
        self.edit_chm_body.blockSignals(True)
        self.edit_chm_body.clear()
        self.edit_chm_body.blockSignals(False)
        if item is None:
            return
        if item.data(0, Qt.ItemDataRole.UserRole) == 'folder':
            self.edit_chm_title.setPlaceholderText("（这是目录，不能编辑正文）")
            return
        filename = item.data(0, Qt.ItemDataRole.UserRole + 1)
        page = self._find_chm_page_by_filename(filename)
        if page is None:
            return
        self.edit_chm_title.blockSignals(True)
        self.edit_chm_title.setText(page['title'])
        self.edit_chm_title.blockSignals(False)
        self.edit_chm_body.blockSignals(True)
        self.edit_chm_body.setHtml(page['html_content'])
        self.edit_chm_body.blockSignals(False)"""
assert old7 in s, "7"
s = s.replace(old7, new7, 1)

old8 = """    def save_current_chm_page(self):
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
            item.setText(title)"""
new8 = """    def save_current_chm_page(self):
        item = self.list_chm_pages.currentItem()
        if item is None or item.data(0, Qt.ItemDataRole.UserRole) != 'page':
            return
        filename = item.data(0, Qt.ItemDataRole.UserRole + 1)
        page = self._find_chm_page_by_filename(filename)
        if page is None:
            return
        title = self.edit_chm_title.text().strip()
        if not title:
            title = page['title']
        page['title'] = title
        page['html_content'] = self.edit_chm_body.toHtml()
        item.setText(0, title)
        self._sync_tree_from_widget()"""
assert old8 in s, "8"
s = s.replace(old8, new8, 1)

old9 = """    def remove_chm_page(self):
        row = self.list_chm_pages.currentRow()
        if row < 0:
            return
        title = self.chm_builder.pages[row]['title']
        del self.chm_builder.pages[row]
        self.list_chm_pages.takeItem(row)
        self.log(f"已删除CHM页面: {title}")"""
new9 = """    def remove_chm_page(self):
        item = self.list_chm_pages.currentItem()
        if item is None:
            return
        title = item.text(0)
        # 递归收集该节点下所有页面filename
        filenames = []
        def collect(i):
            if i.data(0, Qt.ItemDataRole.UserRole) == 'page':
                filenames.append(i.data(0, Qt.ItemDataRole.UserRole + 1))
            for c in range(i.childCount()):
                collect(i.child(c))
        collect(item)
        self.chm_builder.pages = [
            p for p in self.chm_builder.pages if p['filename'] not in filenames
        ]
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
        else:
            idx = self.list_chm_pages.indexOfTopLevelItem(item)
            self.list_chm_pages.takeTopLevelItem(idx)
        self._sync_tree_from_widget()
        self.log(f"已删除CHM节点: {title}")"""
assert old9 in s, "9"
s = s.replace(old9, new9, 1)

old10 = """    def insert_chm_image(self):
        if self.list_chm_pages.currentRow() < 0:
            QMessageBox.information(self, "提示", "请先添加并选中一个CHM页面")
            return"""
new10 = """    def insert_chm_image(self):
        item = self.list_chm_pages.currentItem()
        if item is None or item.data(0, Qt.ItemDataRole.UserRole) != 'page':
            QMessageBox.information(self, "提示", "请先添加并选中一个CHM页面")
            return"""
assert old10 in s, "10"
s = s.replace(old10, new10, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ALL OK')
