# DSD Generator

DSD Generator是一个Mod Organizer 2插件，用于批量处理翻译补丁并生成DSD配置文件。该插件可以自动扫描所有启用的模组，找到翻译补丁并生成相应的DSD配置文件。

## 功能特性

- 自动扫描所有已启用的模组来查找翻译补丁
- 自动调用ESP2DSD可执行文件生成DSD配置文件
- 支持将生成的配置文件保存到新的mod目录
- 支持黑名单功能，可以排除不需要处理的插件
- 可选择性地将生成的配置文件复制到原翻译补丁目录
- 可以自动隐藏原始翻译ESP文件（添加.mohidden后缀）

## 安装步骤

1. 将`esp2dsd_batch_converter`文件夹放入Mod Organizer 2的`plugins`目录
2. 从Nexus下载[esp2dsd](https://www.nexusmods.com/skyrimspecialedition/mods/107676?tab=files)工具
3. 重启Mod Organizer 2

## 使用方法

1. 在Mod Organizer 2的`工具`菜单中找到`Generate DSD Configs`
2. 点击后在设置对话框中：
   - 设置esp2dsd.exe的路径
   - 可选择是否将配置复制到翻译补丁目录
   - 可在黑名单中添加不需要处理的插件名称
3. 点击确定后，插件将：
   - 扫描所有启用的模组
   - 自动识别翻译补丁
   - 生成DSD配置文件
   - 创建新的mod存放生成的配置文件

## 高级功能

- **黑名单功能**: 在设置对话框中可以添加不需要处理的插件名称，每行一个
- **自动复制选项**: 启用后会自动将生成的配置文件复制到原翻译补丁目录，并隐藏原ESP文件
- **冲突处理**: 当存在多个翻译补丁时，会自动选择优先级最高的版本

## 注意事项

- 生成的配置文件会保存在一个新的mod中，格式为"DSD_Configs_年-月-日-时-分"
- 使用自动复制功能时，原ESP文件会被重命名为".mohidden"后缀
- 确保ESP2DSD工具的正确安装和配置

## License
MIT