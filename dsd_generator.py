from typing import List
from datetime import datetime
import os
import subprocess
import mobase
import shutil
from PyQt6.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QProgressDialog, QCheckBox, QTextEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QCoreApplication, qInfo, qCritical, qDebug, qWarning
import time



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
        
        # 添加复制选项复选框
        self.copy_checkbox = QCheckBox(self.tr("use generated config files instead of translation patch plugins"))
        layout.addWidget(self.copy_checkbox)
        # add a description tip when mouse hover on the checkbox
        self.copy_checkbox.setToolTip(self.tr("This will copy generated DSD configuration file to the translation patch directories, and add '.mohidden' suffix to the original translation plugin."))

        # 黑名单管理
        blacklist_layout = QVBoxLayout()
        blacklist_layout.addWidget(QLabel(self.tr("ignored plugins (one per line):")))
        self.blacklist_edit = QTextEdit()
        self.blacklist_edit.setMaximumHeight(100)
        blacklist_layout.addWidget(self.blacklist_edit)
        layout.addLayout(blacklist_layout)
        
        # 输出MOD名称设置
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel(self.tr("Output Dir:")))
        
        self.output_edit = QLineEdit()
        # 修改占位符文本的设置方法
        self.output_edit.setPlaceholderText(self.tr(f"DSD_Configs_{datetime.now().strftime('%y-%m-%d-%H-%M')}"))
        output_layout.addWidget(self.output_edit)
        
        layout.addLayout(output_layout)
        
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
    
    def get_copy_enabled(self) -> bool:
        return self.copy_checkbox.isChecked()
    
    def set_copy_enabled(self, enabled: bool):
        self.copy_checkbox.setChecked(enabled)
    
    def set_blacklist(self, blacklist: List[str]):
        self.blacklist_edit.setPlainText('\n'.join(blacklist))

    def save_blacklist(self):
        with open(os.path.join(os.path.dirname(__file__), "blacklist.txt"), 'w', encoding='utf-8') as f:
            f.write(self.blacklist_edit.toPlainText())

    def get_output_name(self) -> str:
        return self.output_edit.text().strip()
    
    def set_output_name(self, name: str):
        self.output_edit.setText(name)

class DSDGenerator(mobase.IPluginTool):
    def __init__(self):
        super().__init__()
        self._organizer: mobase.IOrganizer
        self._dialog: ConfigDialog
        self._organizer = None # type: ignore
        self._dialog = None # type: ignore
        self._parent = None
    
    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        self._organizer.onAboutToRun(self.auto_run)
        return True
    
    def auto_run(self, app_path: str) -> bool:
        auto_run = self._organizer.pluginSetting(self.name(), "auto_run")
        if (os.path.basename(app_path).lower() == 'skse64_loader.exe') and auto_run:
            return self.run_if_needed()
        return True

    def run_if_needed(self) -> bool:
        exe_path = self._organizer.pluginSetting(self.name(), "esp2dsd_path")
        if not exe_path or not os.path.exists(str(exe_path)):
            qWarning(f"ESP2DSD executable not set or does not exist: {exe_path}")
            return True
        show_progress_when_auto_run = self._organizer.pluginSetting(self.name(), "show_progress_when_auto_run")
        self.generate_dsd_configs(str(exe_path), show_progress=bool(show_progress_when_auto_run), is_auto_run=True)
        
        return True


    def name(self) -> str:
        return "DSD Generator"
    
    def author(self) -> str:
        return "lightsofa"
    
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
                mobase.PluginSetting("copy_to_translation_patch_directoy", self.__tr("make a copy to translation patch directories"), False),
                mobase.PluginSetting("output_mod_name", self.__tr("Output Dir"), ""),
                mobase.PluginSetting("auto_run", self.__tr("Automatically generate DSD configs when game starts"), True),
                mobase.PluginSetting("show_progress_when_auto_run", self.__tr("Show progress dialog when auto generating"), True),
            ]
        
    def displayName(self) -> str:
        return self.__tr("ESP2DSD batch convertor")
    
    def tooltip(self) -> str:
        return self.__tr("Generate DSD configuration files from translation patches")
    
    def icon(self) -> QIcon:
        return QIcon()

    def setParentWidget(self, widget):
        self._parent = widget

    def display(self):
        if not self._dialog:
            self._dialog = ConfigDialog(self._parent)
        
        # 加载保存的设置
        saved_path = self._organizer.pluginSetting(self.name(), "esp2dsd_path")
        copy_enabled = self._organizer.pluginSetting(self.name(), "copy_to_translation_patch_directoy")
        output_name = self._organizer.pluginSetting(self.name(), "output_mod_name")
        blacklist = self._read_blacklist()
        
        if saved_path:
            self._dialog.set_exe_path(str(saved_path))
        if output_name:
            self._dialog.set_output_name(str(output_name))
        self._dialog.set_copy_enabled(bool(copy_enabled))
        self._dialog.set_blacklist(blacklist or [])
        
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
            self._organizer.setPluginSetting(self.name(), "copy_to_translation_patch_directoy", self._dialog.get_copy_enabled())
            self._organizer.setPluginSetting(self.name(), "output_mod_name", self._dialog.get_output_name())
            self._dialog.save_blacklist()
            
            # 确认是否继续
            if QMessageBox.question(
                self._parent,
                self.__tr("Confirm"),
                self.__tr("This will scan all mods for plugin files and generate DSD configurations. Continue?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
            
            try:
                self.generate_dsd_configs(exe_path, show_progress=True, is_auto_run=False)
            except Exception as e:
                QMessageBox.critical(
                    self._parent,
                    self.__tr("Error"),
                    str(e)
                )
    
    def _read_blacklist(self) -> List[str]:
        blacklist_file = os.path.join(os.path.dirname(__file__), "blacklist.txt")
        if os.path.exists(blacklist_file):
            with open(blacklist_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def _get_output_mod_name(self, is_auto_run: bool = False) -> str:
        if is_auto_run:
            # 从插件设置中获取输出目录名称
            saved_name = self._organizer.pluginSetting(self.name(), "output_mod_name")
            if saved_name:
                return str(saved_name)
            # 如果没有保存的名称，使用默认格式
            return f"DSD_Configs_{datetime.now().strftime('%y-%m-%d-%H-%M')}"
        else:
            # 正常运行时从对话框获取
            custom_name = self._dialog.get_output_name()
            return custom_name if custom_name else self._dialog.output_edit.placeholderText()

    def _should_copy_to_patch_dir(self, is_auto_run: bool = False) -> bool:
        if is_auto_run:
            return bool(self._organizer.pluginSetting(self.name(), "copy_to_translation_patch_directoy"))
        return self._dialog.get_copy_enabled()

    def generate_dsd_configs(self, esp2dsd_exe: str, show_progress: bool = True, is_auto_run: bool = False):
        # 修改进度对话框的显示逻辑
        progress_dialog = None
        if show_progress:
            translating_progress = 0
            progress_dialog = QProgressDialog(
                self.__tr("Generating DSD configurations..."), 
                None,
                translating_progress, 
                0, 
                self._parent
            )
            progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress_dialog.show()

        # 将黑名单分为文件黑名单、文件夹黑名单和modid黑名单
        blacklist_files = []
        blacklist_folders = []
        blacklist_modids = []
        
        # 从文件读取黑名单而不是从对话框
        blacklist_items = self._read_blacklist()
        
        for item in blacklist_items:
            item = item.strip()
            if not item or item.startswith('#'):
                continue
            if item.startswith('@'):
                blacklist_modids.append(item[1:].lower())
            elif item.endswith('/'):
                blacklist_folders.append(item[:-1].lower())
            else:
                blacklist_files.append(item.lower())

        # 获取所有已启用的模组
        mods = [mod for mod in self._organizer.modList().allModsByProfilePriority() if self._organizer.modList().state(mod) & mobase.ModState.ACTIVE]
        original_files = {}  # 原始插件文件
        translation_files = {}  # 翻译插件文件

        # 遍历所有模组，按加载顺序从低到高
        for mod_name in mods:
            # 检查模组是否在黑名单中
            if mod_name.lower() in blacklist_folders:
                continue
                
            mod = self._organizer.modList().getMod(mod_name)
            if not mod:
                continue

            # 检查modid是否在黑名单中 (仅当blacklist_modids非空)
            if blacklist_modids:
                mod_meta_file = os.path.join(mod.absolutePath(), 'meta.ini')
                skip_mod = False
                if os.path.exists(mod_meta_file):
                    with open(mod_meta_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('modid='):
                                mod_id = line.strip().split('=')[1].lower()
                                if mod_id in blacklist_modids:
                                    skip_mod = True
                                    blacklist_modids.remove(mod_id)
                                break
                if skip_mod:
                    continue
                    
            # 遍历模组中的文件
            mod_path = mod.absolutePath()
            for root, _, files in os.walk(mod_path):
                for file in files:
                    # 跳过黑名单中的插件
                    if file.lower() in map(str.lower, blacklist_files):
                        continue
                        
                    if file.lower().endswith(('.esp', '.esm', '.esl')):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, mod_path)
                        
                        # 检查这个文件是否覆盖了之前的文件
                        if relative_path in original_files:
                            # 如果这个文件的文件大小是在原始文件的1.2倍以上，或者在原始文件的0.8倍以下，那么它肯定不是翻译文件
                            if os.path.getsize(full_path) > os.path.getsize(original_files[relative_path]) * 1.2 or \
                                os.path.getsize(full_path) < os.path.getsize(original_files[relative_path]) * 0.8:
                                continue
                            # 这是一个翻译文件，记录它和对应的原始文件
                            translation_files[relative_path] = {
                                'path': full_path,
                                'original': original_files[relative_path],
                                'mod_name': mod_name  # 保存mod名称而不是priority
                            }
                        else:
                            # 这是一个原始文件
                            original_files[relative_path] = full_path
        
        if not translation_files:
            raise Exception(self.__tr("No translation patches found in enabled mods!"))

        # 修改进度更新逻辑
        if progress_dialog:
            progress_dialog.setMaximum(len(translation_files))

        # 设置输出目录
        output_mod_name = self._get_output_mod_name(is_auto_run)
        output_dir = os.path.join(self._organizer.modsPath(), output_mod_name)
        os.makedirs(output_dir, exist_ok=True)

        # 统计最终生成的翻译文件数量
        generated_files_count = 0

        # 为每个翻译文件生成DSD配置
        for file_path, info in translation_files.items():
            # 如果存在多个翻译，选择优先级最高的
            if (file_path in translation_files and 
                self._get_mod_priority(translation_files[file_path]['mod_name']) > 
                self._get_mod_priority(info['mod_name'])):
                continue
            
            # 调用esp2dsd生成配置文件
            output_dir = os.path.join(output_mod_name, r"SKSE/Plugins/DynamicStringDistributor", os.path.basename(file_path))
            output_file = os.path.join(output_dir, os.path.basename(file_path) + ".json")
            try:
                # Run ESP2DSD at background
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE

                result = subprocess.run(
                    [esp2dsd_exe, info['original'], info['path']],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(esp2dsd_exe),
                    startupinfo=startupinfo
                )
                
                # Write log to file in output directory
                # log_file = os.path.join(output_dir, os.path.basename(file_path) + ".log")
                # with open(log_file, "w", encoding="utf-8") as f:
                #     f.write(f"Original: {info['original']}\n")
                #     f.write(f"Translation: {info['path']}\n")
                    # f.write("\nStdout:\n")
                    # f.write(result.stdout)
                    # f.write("\nStderr:\n")
                    # f.write(result.stderr)

                # esp2dsd.exe 会在当前目录的output文件夹下生成配置文件
                # 我们需要将其移动到我们指定的输出目录
                pluginName = os.path.splitext(os.path.basename(file_path))
                generated_file = os.path.join(
                    os.path.dirname(esp2dsd_exe),
                    "output",
                    f"{pluginName[0]}_output{pluginName[1]}.json"
                )
                if os.path.exists(generated_file):
                    if os.path.getsize(generated_file) < 3:  # 排除空JSON文件
                        os.remove(generated_file)  
                    else:
                        try:
                            os.makedirs(output_dir, exist_ok=True)
                            os.replace(generated_file, output_file)
                            
                            if self._should_copy_to_patch_dir(is_auto_run):
                                # 检查原文件是否存在且能访问
                                if os.path.exists(info['path']) and os.access(info['path'], os.W_OK):
                                    # 检查目标文件是否已存在
                                    if not os.path.exists(info['path'] + ".mohidden"):
                                        os.rename(info['path'], info['path'] + ".mohidden")
                                        
                                        translation_patch_dir = os.path.dirname(info['path'])
                                        copy_to_dir = os.path.join(translation_patch_dir, 
                                                                 "SKSE", "Plugins", 
                                                                 "DynamicStringDistributor",
                                                                 os.path.basename(file_path))
                                        os.makedirs(copy_to_dir, exist_ok=True)
                                        shutil.copy2(output_file, os.path.join(copy_to_dir, 
                                                                             os.path.basename(output_file)))
                                        generated_files_count += 1
                                    else:
                                        qWarning(
                                            f"Skipped renaming {info['path']}: .mohidden file already exists")
                                else:
                                    qCritical(
                                        f"Cannot access file for renaming: {info['path']}")
                        except (OSError, IOError) as e:
                            raise Exception(f"File operation failed for {file_path}: {str(e)}")
                else:
                    raise Exception(f"Expected output file not found: {generated_file}")
            except subprocess.CalledProcessError as e:
                raise Exception(f"Error processing {file_path}: {e.stderr}")
            translating_progress += 1
            if progress_dialog:
                progress_dialog.setValue(translating_progress)

        if progress_dialog:
            progress_dialog.cancel()
        if is_auto_run:
            qInfo(
                f"DSD configurations generated successfully! {generated_files_count} files generated."
            )
        else:
            QMessageBox.information(
                self._parent,
                self.__tr("Success"),
                self.__tr("DSD configurations generated successfully!" + f"\n{generated_files_count} {self.__tr('files generated.')}")
            )

        # 刷新模组列表
        self._organizer.refresh()
        
    def _get_mod_priority(self, mod_name: str) -> int:
        return self._organizer.modList().priority(mod_name) # type: ignore
    
    def __tr(self, str_):
        return QCoreApplication.translate("DSDGenerator", str_)

