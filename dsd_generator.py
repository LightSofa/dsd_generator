from typing import List
from datetime import datetime
import os
import subprocess
import mobase
from PyQt6.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QCoreApplication


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(self.tr("DSD Generator Settings"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # ESP2DSD路径设置
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel(self.tr("ESP2DSD Executable:")))
        
        self.path_edit = QLineEdit()
        path_layout.addWidget(self.path_edit)
        
        browse_button = QPushButton(self.tr("Browse..."))
        browse_button.clicked.connect(self.browse_exe)
        path_layout.addWidget(browse_button)
        
        layout.addLayout(path_layout)
        
        # 确定和取消按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton(self.tr("OK"))
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select ESP2DSD Executable"),
            "",
            self.tr("Executable files (*.exe);;All files (*.*)")
        )
        if file_path:
            self.path_edit.setText(file_path)
    
    def get_exe_path(self) -> str:
        return self.path_edit.text()
    
    def set_exe_path(self, path: str):
        self.path_edit.setText(path)


class DSDGenerator(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer = None
        self._dialog = None
        self._parent = None
    
    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        return True
    
    def name(self) -> str:
        return "DSD Generator"
    
    def author(self) -> str:
        return "Your Name"
    
    def description(self) -> str:
        return self.__tr("Generate DSD configuration files from translation patches.")
    
    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, 0, mobase.ReleaseType.ALPHA)
        
        def isActive(self) -> bool:
            return bool(self._organizer.pluginSetting(self.name(), "enabled"))
        
    def settings(self) -> List[mobase.PluginSetting]:
        return [
                mobase.PluginSetting("enabled", self.__tr("Enable this plugin"), True),
                mobase.PluginSetting("esp2dsd_path", self.__tr("Path to ESP2DSD executable"), ""),
            ]
        
    def displayName(self) -> str:
        return self.__tr("Generate DSD Configs")
    
    def tooltip(self) -> str:
        return self.__tr("Generate DSD configuration files from translation patches")
    
    def icon(self) -> QIcon:
        return QIcon()

    def setParentWidget(self, widget):
        self._parent = widget

    def display(self):
        if not self._dialog:
            self._dialog = ConfigDialog(self._parent)
        
        # 加载保存的exe路径
        saved_path = self._organizer.pluginSetting(self.name(), "esp2dsd_path")
        if saved_path:
            self._dialog.set_exe_path(str(saved_path))
        
        if self._dialog.exec() == QDialog.DialogCode.Accepted:
            exe_path = self._dialog.get_exe_path()
            if not exe_path:
                return
                
            if not os.path.exists(exe_path):
                QMessageBox.critical(
                    self._parent,
                    self.__tr("Error"),
                    self.__tr("ESP2DSD executable not found!")
                )
                return
            
            # 保存设置
            self._organizer.setPluginSetting(self.name(), "esp2dsd_path", exe_path)
            
            # 确认是否继续
            if QMessageBox.question(
                self._parent,
                self.__tr("Confirm"),
                self.__tr("This will scan all mods for plugin files and generate DSD configurations. Continue?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
            
            try:
                self.generate_dsd_configs(exe_path)
            except Exception as e:
                QMessageBox.critical(
                    self._parent,
                    self.__tr("Error"),
                    str(e)
                )
    
    def generate_dsd_configs(self, esp2dsd_exe: str):
        # 获取所有模组
        mods = self._organizer.modList().allMods()
        original_files = {}  # 原始插件文件
        translation_files = {}  # 翻译插件文件
        
        # 遍历所有模组，按加载顺序从低到高
        for mod_name in mods:
            mod = self._organizer.getMod(mod_name)
            if not mod:
                continue
            
            # 遍历模组中的文件
            mod_path = mod.absolutePath()
            for root, _, files in os.walk(mod_path):
                for file in files:
                    if file.lower().endswith(('.esp', '.esm', '.esl')):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, mod_path)
                        
                        # 检查这个文件是否覆盖了之前的文件
                        if relative_path in original_files:
                            # 这是一个翻译文件，记录它和对应的原始文件
                            translation_files[relative_path] = {
                                'path': full_path,
                                'original': original_files[relative_path],
                                'priority': mod.priority()
                            }
                        else:
                            # 这是一个原始文件
                            original_files[relative_path] = full_path
        
        if not translation_files:
            raise Exception(self.__tr("No translation patches found in enabled mods!"))

        # 创建新的mod作为输出目录
        timestamp = datetime.now().strftime("%m-%d-%H-%M")
        mod_name = f"DSD_Configs_{timestamp}"
        try:
            self._organizer.createMod(mod_name)
        except Exception as e:
            raise Exception(self.__tr("Failed to create output mod: ") + str(e))
            
        mod = self._organizer.getMod(mod_name)
        if not mod:
            raise Exception(self.__tr("Failed to create output mod! {mod_name}"))
            
        output_dir = mod.absolutePath()
        
        # 为每个翻译文件生成DSD配置
        for file_path, info in translation_files.items():
            # 如果存在多个翻译，选择优先级最高的
            if (file_path in translation_files and 
                translation_files[file_path]['priority'] > info['priority']):
                continue
            
            # 调用esp2dsd生成配置文件
            output_file = os.path.join(output_dir, os.path.basename(file_path) + ".json")
            try:
                result = subprocess.run(
                    [esp2dsd_exe, info['original'], info['path']],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(esp2dsd_exe)
                )
                # esp2dsd.exe 会在当前目录的output文件夹下生成配置文件
                # 我们需要将其移动到我们指定的输出目录
                generated_file = os.path.join(
                    os.path.dirname(esp2dsd_exe),
                    "output",
                    os.path.basename(file_path) + ".json"
                )
                if os.path.exists(generated_file):
                    os.replace(generated_file, output_file)
                else:
                    raise Exception(f"Expected output file not found: {generated_file}")
            except subprocess.CalledProcessError as e:
                raise Exception(f"Error processing {file_path}: {e.stderr}")
        
        QMessageBox.information(
            self._parent,
            self.__tr("Success"),
            self.__tr(f"DSD configuration files have been generated in mod:\n{mod_name}")
        )
    
    def __tr(self, str_):
        return QCoreApplication.translate("DSDGenerator", str_)
