# -*- coding: utf-8 -*-
from typing import List
from datetime import datetime
import os
import mobase
import shutil
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QProgressDialog, QCheckBox, QTextEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QCoreApplication
import time
import json
import logging 
from .utils import file_stat
from .esp2dsd.converter import esp2dsd

def tr(msg: str) -> str:
    """翻译函数，使用QCoreApplication的translate方法"""
    return QCoreApplication.translate("ESP2DSD batch Convertor", msg)

# 日志初始化
logger = logging.getLogger("DSDGenerator")

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("ESP2DSD Convertor Settings"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # 添加复制选项复选框
        self.copy_checkbox = QCheckBox(self.tr("use generated config files instead of translation plugins"))
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
    def __init__(self, parent=None):
        super().__init__()
        self._organizer: mobase.IOrganizer
        self._dialog: ConfigDialog
        self._organizer = None # type: ignore
        self._dialog = None # type: ignore
        self._parent = None
        self._incorrect_pairs_file = os.path.join(os.path.dirname(__file__), "incorrect_pairs.json")
        self._blacklist_cache = None
        self._incorrect_pairs_cache = None
        self._last_blacklist_mtime = 0
        self._last_incorrect_pairs_mtime = 0

    def init(self, organizer: mobase.IOrganizer):
        logger.debug(f"[DSDGenerator] Initializing with organizer: {organizer}")
        self._organizer = organizer
        self._organizer.onAboutToRun(self.auto_run)
        return True
    
    def auto_run(self, app_path: str) -> bool:
        logger.debug(f"[DSDGenerator] Auto run triggered for: {app_path}")
        is_target_app = (os.path.basename(app_path).lower() == 'skse64_loader.exe')
        should_auto_run = self._organizer.pluginSetting(self.name(), "auto_run")
        
        if is_target_app and should_auto_run:
            # 检查是否需要生成DSD配置
            self.generate_dsd_configs(
                show_progress=bool(self._organizer.pluginSetting(self.name(), "show_progress_when_auto_run")),
                is_auto_run=True,
                blacklist=self._read_blacklist()
            )

        return True


    def name(self) -> str:
        return "DSD Generator"
    
    def author(self) -> str:
        return "lightsofa"
    
    def description(self) -> str:
        return tr("Generate DSD configuration files from translation patches.")
    
    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(1, 0, 0, 0, mobase.ReleaseType.ALPHA)
        
    def isActive(self) -> bool:
        return bool(self._organizer.pluginSetting(self.name(), "enabled"))
        
    def settings(self) -> List[mobase.PluginSetting]:
        return [
                mobase.PluginSetting("enabled", tr("Enable this plugin"), True),
                mobase.PluginSetting("copy_to_translation_patch_directoy", tr("make a copy to translation patch directories"), False),
                mobase.PluginSetting("output_mod_name", tr("Output Dir"), ""),
                mobase.PluginSetting("auto_run", tr("Automatically generate DSD configs when game starts"), False),
                mobase.PluginSetting("show_progress_when_auto_run", tr("Show progress dialog when auto generating"), True),
            ]
        
    def displayName(self) -> str:
        return tr("Generate DSD Configs")
    
    def tooltip(self) -> str:
        return tr("Generate DSD configuration files from translation patches")
    
    def icon(self) -> QIcon:
        return QIcon()

    def setParentWidget(self, widget):
        self._parent = widget

    def display(self):
        logger.debug("[DSDGenerator] Display dialog triggered")
        if not self._dialog:
            self._dialog = ConfigDialog(self._parent)
        
        # 加载保存的设置
        copy_enabled = self._organizer.pluginSetting(self.name(), "copy_to_translation_patch_directoy")
        output_name = self._organizer.pluginSetting(self.name(), "output_mod_name")
        blacklist = self._read_blacklist()
        
        if output_name:
            self._dialog.set_output_name(str(output_name))
        self._dialog.set_copy_enabled(bool(copy_enabled))
        self._dialog.set_blacklist(blacklist or [])
        
        if self._dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存设置
            self._organizer.setPluginSetting(self.name(), "copy_to_translation_patch_directoy", self._dialog.get_copy_enabled())
            self._organizer.setPluginSetting(self.name(), "output_mod_name", self._dialog.get_output_name())
            self._dialog.save_blacklist()
            
            # 确认是否继续
            if QMessageBox.question(
                self._parent,
                tr("Confirm"),
                tr("This will scan all mods for plugin files and generate DSD configurations. Continue?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
            
            try:
                self.generate_dsd_configs(show_progress=True, is_auto_run=False, blacklist=blacklist)
            except Exception as e:
                QMessageBox.critical(
                    self._parent,
                    tr("Error"),
                    str(e)
                )
    
    def _read_blacklist(self) -> List[str]:
        blacklist_file = os.path.join(os.path.dirname(__file__), "blacklist.txt")
        logger.debug(f"[DSDGenerator] Reading blacklist from {blacklist_file}")
        if os.path.exists(blacklist_file):
            current_mtime = os.path.getmtime(blacklist_file)
            if self._blacklist_cache is not None and current_mtime == self._last_blacklist_mtime:
                return self._blacklist_cache
            
            with open(blacklist_file, 'r', encoding='utf-8') as f:
                self._blacklist_cache = [line.strip() for line in f if line.strip()]
                self._last_blacklist_mtime = current_mtime
                return self._blacklist_cache
        return []

    def _get_incorrect_pairs(self) -> dict:
        logger.debug("[DSDGenerator] Getting incorrect pairs")
        if os.path.exists(self._incorrect_pairs_file):
            current_mtime = os.path.getmtime(self._incorrect_pairs_file)
            if self._incorrect_pairs_cache is not None and current_mtime == self._last_incorrect_pairs_mtime:
                return self._incorrect_pairs_cache
            
            try:
                with open(self._incorrect_pairs_file, 'r', encoding='utf-8') as f:
                    self._incorrect_pairs_cache = json.load(f)
                    self._last_incorrect_pairs_mtime = current_mtime
                    return self._incorrect_pairs_cache
            except Exception:
                return {}
        return {}

    def _is_valid_translation_pair(self, original_file: str, translation_file: str) -> bool:
        logger.debug(f"[DSDGenerator] Validating translation pair: {original_file} -> {translation_file}")
        logger.debug(f"Checking file pair: {original_file} <-> {translation_file}")
        try:
            orig_stat = os.stat(original_file)
            trans_stat = os.stat(translation_file)
            
            # 检查文件大小比例
            if trans_stat.st_size > orig_stat.st_size * 1.2 or trans_stat.st_size < orig_stat.st_size * 0.8:
                return False

            # 检查错误配对缓存
            incorrect_pairs = self._get_incorrect_pairs()
            file_name = os.path.basename(original_file)
            if file_name in incorrect_pairs:
                pair = incorrect_pairs[file_name]
                if (pair["original"]["size"] == orig_stat.st_size and
                    pair["original"]["mtime"] == orig_stat.st_mtime):
                    # 检查 translations 列表中是否有匹配的 translation 文件
                    for t in pair.get("translations", []):
                        if (t["size"] == trans_stat.st_size and
                            t["mtime"] == trans_stat.st_mtime):
                            return False
            return True
        except Exception as e:
            logger.warning(f"Error checking file pair: {str(e)}")
            return False

    def _record_incorrect_pair(self, original_file: str, translation_file: str):
        logger.debug(f"[DSDGenerator] Recording incorrect pair: {original_file} -> {translation_file}")
        try:
            incorrect_pairs = self._get_incorrect_pairs()
            file_name = os.path.basename(original_file)
            orig_stat = file_stat(original_file)
            trans_stat = file_stat(translation_file)
            if file_name not in incorrect_pairs:
                incorrect_pairs[file_name] = {
                    "original": orig_stat,
                    "translations": [trans_stat]
                }
            else:
                # 如果 original 发生变化则重置 translations
                if (incorrect_pairs[file_name]["original"]["size"] != orig_stat["size"] or
                    incorrect_pairs[file_name]["original"]["mtime"] != orig_stat["mtime"]):
                    incorrect_pairs[file_name]["original"] = orig_stat
                    incorrect_pairs[file_name]["translations"] = [trans_stat]
                else:
                    # 添加到 translations 列表（避免重复）
                    translations = incorrect_pairs[file_name].setdefault("translations", [])
                    if not any(t["size"] == trans_stat["size"] and t["mtime"] == trans_stat["mtime"] for t in translations):
                        translations.append(trans_stat)

            self._incorrect_pairs_cache = incorrect_pairs
            self._last_incorrect_pairs_mtime = time.time()

            with open(self._incorrect_pairs_file, 'w', encoding='utf-8') as f:
                json.dump(incorrect_pairs, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"Error recording incorrect pair: {str(e)}")

    def _get_output_mod_name(self, is_auto_run: bool = False) -> str:
        logger.debug(f"[DSDGenerator] Getting output mod name, auto_run: {is_auto_run}")
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
        logger.debug(f"[DSDGenerator] Checking if should copy to patch dir, auto_run: {is_auto_run}")
        if is_auto_run:
            return bool(self._organizer.pluginSetting(self.name(), "copy_to_translation_patch_directoy"))
        return self._dialog.get_copy_enabled()

    def generate_dsd_configs(self, show_progress: bool = True, is_auto_run: bool = False, blacklist: list[str] = []):
        logger.debug(f"[DSDGenerator] Starting DSD config generation. show_progress: {show_progress}, auto_run: {is_auto_run}")
        progress_dialog = None
        if show_progress:
            progress_dialog = QProgressDialog(
                tr("Preparing to scan mods..."), 
                None,
                0,
                0,
                self._parent
            )
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            progress_dialog.setAutoClose(True)
            progress_dialog.setAutoReset(True)
            progress_dialog.setLabelText(tr("[ESP2DSD] Scanning translation patches..."))
            # 强制刷新界面，确保进度条立即显示
            QCoreApplication.processEvents()

        # 将黑名单分为文件黑名单、文件夹黑名单和modid黑名单
        blacklist_files = []
        blacklist_folders = []
        blacklist_modids = []
        
        # 读取黑名单
        blacklist_items = blacklist
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
        original_files = {}
        translation_files = {}

        # 遍历所有模组，按加载顺序从低到高
        logger.debug(f"Processing mods...")
        for mod_name in mods:

            logger.debug(f"Processing mod: {mod_name}")
            # 检查模组是否在黑名单中
            if mod_name.lower() in blacklist_folders:
                logger.debug(f"Skipping mod {mod_name} due to folder blacklist")
                continue
                
            mod = self._organizer.modList().getMod(mod_name)
            if not mod:
                logger.debug(f"Mod {mod_name} not found in mod list, skipping...")
                continue

            # 检查modid是否在黑名单中 (仅当blacklist_modids非空)
            logger.debug(f"Checking modid for {mod_name}...")
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
            logger.debug(f"Processing mod: {mod_name}")
            mod_path = mod.absolutePath()
            # 只遍历mod_path下的第一层文件，不进行深度遍历
            try:
                files = os.listdir(mod_path)
            except Exception as e:
                logger.warning(f"Failed to list files in {mod_path}: {e}")
                continue
            root = mod_path
            for file in files:
                # 跳过黑名单中的插件
                if file.lower() in map(str.lower, blacklist_files):
                    continue
                    
                if file.lower().endswith(('.esp', '.esm', '.esl')):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, mod_path)
                    
                    # 检查这个文件是否覆盖了之前的文件
                    if relative_path in original_files:
                        # 检查配对有效性
                        if not self._is_valid_translation_pair(original_files[relative_path], full_path):
                            logger.info(f"Skipping invalid translation pair: {original_files[relative_path]} -> {full_path}")
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
            if progress_dialog:
                progress_dialog.close()
            QMessageBox.information(self._parent,"ESP2DSD", tr("No translation patches found in enabled mods!"))
            return

        # 在获取到translation_files后更新进度对话框的最大值
        if progress_dialog and len(translation_files) > 0:
            progress_dialog.setMaximum(len(translation_files))
            progress_dialog.setLabelText(tr("Generating DSD configurations..."))
            translating_progress = 0

        # 设置输出目录
        output_mod_name = self._get_output_mod_name(is_auto_run)

        # 统计最终生成的翻译文件数量
        output_files_count = 0

        # 为每个翻译文件生成DSD配置
        logger.debug(f"Generated DSD configurations in {output_mod_name}...")
        for file_path, info in translation_files.items():
            # 如果存在多个翻译，选择优先级最高的
            if (file_path in translation_files and 
                self._get_mod_priority(translation_files[file_path]['mod_name']) > 
                self._get_mod_priority(info['mod_name'])):
                continue
            
            # 调用esp2dsd生成配置文件
            output_dir = os.path.join(self._organizer.modsPath(), output_mod_name, r"SKSE/Plugins/DynamicStringDistributor", os.path.basename(file_path))
            output_file = os.path.join(output_dir, os.path.basename(file_path) + ".json")
            try:
                # Call the python function to get the DSD config as a string
                json_string = esp2dsd(Path(info['path']), Path(info['original']))
                
                # Check if the generated config is empty (just "[]")
                if len(json_string) < 3:
                    self._record_incorrect_pair(info['original'], info['path'])
                    logger.warning(f"Empty config generated for {file_path}, recorded as incorrect pair")
                else:
                    os.makedirs(output_dir, exist_ok=True)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(json_string)
                    
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
                                shutil.copy2(output_file, os.path.join(copy_to_dir, os.path.basename(output_file)))
                            else:
                                logger.warning(
                                    f"Skipped renaming {info['path']}: .mohidden file already exists")
                        else:
                            logger.critical(
                                f"Cannot access file for renaming: {info['path']}")
                    output_files_count += 1

            except Exception as e:
                raise Exception(f"Error processing {file_path}: {str(e)}")

            if progress_dialog:
                translating_progress += 1
                progress_dialog.setValue(translating_progress)

        # 修改进度对话框的关闭逻辑
        if progress_dialog:
            progress_dialog.setValue(progress_dialog.maximum())
            progress_dialog.close()

        if is_auto_run:
            logger.info(
                f"DSD configurations generated successfully! {output_files_count} files generated."
            )
        else:
            QMessageBox.information(
                self._parent,
                tr("Success"),
                tr(f"DSD configurations generated successfully!\n{output_files_count} files generated.")
            )


        # 刷新模组列表
        self._organizer.refresh()
        # 自动运行时自动启用生成的模组
        if (is_auto_run and output_files_count > 0):
            self._organizer.modList().setActive(output_mod_name, True)
        
    def _get_mod_priority(self, mod_name: str) -> int:
        logger.debug(f"[DSDGenerator] Getting priority for mod: {mod_name}")
        return self._organizer.modList().priority(mod_name) # type: ignore