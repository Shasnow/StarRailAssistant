; *** Inno Setup 版本 6.5.0+ 中文(简体) 语言文件 ***
;
; 翻译作者：EveGlowLuna
; 仅为 StarRailAssistant 项目打包使用。
;
; 注意：翻译此文本时，请不要在原本没有句号(.)的消息后面添加句号，
; 因为 Inno Setup 会在这些消息后面自动添加句号(添加句号会导致显示两个句号)。

[LangOptions]
; 以下三个条目非常重要。请务必阅读并理解帮助文件中的 '[LangOptions] section' 主题。
LanguageName=中文(简体)
LanguageID=$0804
; 如果可能，LanguageCodePage 应始终设置，即使此文件是 Unicode 格式
; 对于英文，它被设置为零，因为英文只使用 ASCII 字符
LanguageCodePage=936
; 如果您要翻译的语言需要特殊的字体或大小，请取消注释以下任何条目并相应地更改它们。
;DialogFontName=
;DialogFontSize=9
;WelcomeFontName=微软雅黑
;WelcomeFontSize=12
;TitleFontName=微软雅黑
;TitleFontSize=29
;CopyrightFontName=微软雅黑
;CopyrightFontSize=9

[Messages]

; *** 应用程序标题
SetupAppTitle=安装程序
SetupWindowTitle=安装程序 - %1
UninstallAppTitle=卸载程序
UninstallAppFullTitle=%1 卸载程序

; *** 杂项通用
InformationTitle=信息
ConfirmTitle=确认
ErrorTitle=错误

; *** SetupLdr 消息
SetupLdrStartupMessage=这将安装 %1。您是否希望继续？
LdrCannotCreateTemp=无法创建临时文件。安装程序已中止
LdrCannotExecTemp=无法在临时目录中执行文件。安装程序已中止
HelpTextNote=

; *** 启动错误消息
LastErrorMessage=%1。%n%n错误 %2: %3
SetupFileMissing=安装目录中缺少文件 %1。请纠正问题或获取程序的新副本。
SetupFileCorrupt=安装文件已损坏。请获取程序的新副本。
SetupFileCorruptOrWrongVer=安装文件已损坏，或与此版本的安装程序不兼容。请纠正问题或获取程序的新副本。
InvalidParameter=命令行上传递了无效参数:%n%n%1
SetupAlreadyRunning=安装程序已在运行。
WindowsVersionNotSupported=此程序不支持您的计算机正在运行的 Windows 版本。
WindowsServicePackRequired=此程序需要 %1 Service Pack %2 或更高版本。
NotOnThisPlatform=此程序无法在 %1 上运行。
OnlyOnThisPlatform=此程序必须在 %1 上运行。
OnlyOnTheseArchitectures=此程序只能安装在为以下处理器架构设计的 Windows 版本上:%n%n%1
WinVersionTooLowError=此程序需要 %1 版本 %2 或更高版本。
WinVersionTooHighError=此程序无法安装在 %1 版本 %2 或更高版本上。
AdminPrivilegesRequired=安装此程序时，您必须以管理员身份登录。
PowerUserPrivilegesRequired=安装此程序时，您必须以管理员身份或作为 Power Users 组的成员登录。
SetupAppRunningError=安装程序检测到 %1 当前正在运行。%n%n请现在关闭它的所有实例，然后单击确定继续，或单击取消退出。
UninstallAppRunningError=卸载程序检测到 %1 当前正在运行。%n%n请现在关闭它的所有实例，然后单击确定继续，或单击取消退出。

; *** 启动问题
PrivilegesRequiredOverrideTitle=选择安装程序安装模式
PrivilegesRequiredOverrideInstruction=选择安装模式
PrivilegesRequiredOverrideText1=%1 可以为所有用户安装(需要管理员权限)，或仅为您安装。
PrivilegesRequiredOverrideText2=%1 可以为您安装，或为所有用户安装(需要管理员权限)。
PrivilegesRequiredOverrideAllUsers=为&所有用户安装
PrivilegesRequiredOverrideAllUsersRecommended=为&所有用户安装(推荐)
PrivilegesRequiredOverrideCurrentUser=仅&为我安装
PrivilegesRequiredOverrideCurrentUserRecommended=仅&为我安装(推荐)

; *** 杂项错误
ErrorCreatingDir=安装程序无法创建目录 "%1"
ErrorTooManyFilesInDir=无法在目录 "%1" 中创建文件，因为它包含的文件太多

; *** 安装通用消息
ExitSetupTitle=退出安装程序
ExitSetupMessage=安装程序未完成。如果您现在退出，程序将不会被安装。%n%n您可以在其他时间再次运行安装程序以完成安装。%n%n退出安装程序？
AboutSetupMenuItem=&关于安装程序...
AboutSetupTitle=关于安装程序
AboutSetupMessage=%1 版本 %2%n%3%n%n%1 主页:%n%4
AboutSetupNote=
TranslatorNote=

; *** 按钮
ButtonBack=< &上一步
ButtonNext=&下一步 >
ButtonInstall=&安装
ButtonOK=确定
ButtonCancel=取消
ButtonYes=&是
ButtonYesToAll=全部&是
ButtonNo=&否
ButtonNoToAll=全部&否
ButtonFinish=&完成
ButtonBrowse=&浏览...
ButtonWizardBrowse=&浏览...
ButtonNewFolder=&新建文件夹

; *** "选择语言" 对话框消息
SelectLanguageTitle=选择安装程序语言
SelectLanguageLabel=选择安装过程中要使用的语言。

; *** 通用向导文本
ClickNext=单击下一步继续，或单击取消退出安装程序。
BeveledLabel=
BrowseDialogTitle=浏览文件夹
BrowseDialogLabel=在下面的列表中选择一个文件夹，然后单击确定。
NewFolderName=新文件夹

; *** "欢迎" 向导页面
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=这将在您的计算机上安装 [name/ver]。%n%n建议您在继续之前关闭所有其他应用程序。

; *** "密码" 向导页面
WizardPassword=密码
PasswordLabel1=此安装受密码保护。
PasswordLabel3=请提供密码，然后单击下一步继续。密码区分大小写。
PasswordEditLabel=&密码:
IncorrectPassword=您输入的密码不正确。请重试。

; *** "许可协议" 向导页面
WizardLicense=许可协议
LicenseLabel=请在继续之前阅读以下重要信息。
LicenseLabel3=请阅读以下许可协议。您必须接受此协议的条款才能继续安装。
LicenseAccepted=我&接受协议
LicenseNotAccepted=我&不接受协议

; *** "信息" 向导页面
WizardInfoBefore=信息
InfoBeforeLabel=请在继续之前阅读以下重要信息。
InfoBeforeClickLabel=当您准备好继续安装时，单击下一步。
WizardInfoAfter=信息
InfoAfterLabel=请在继续之前阅读以下重要信息。
InfoAfterClickLabel=当您准备好继续安装时，单击下一步。

; *** "用户信息" 向导页面
WizardUserInfo=用户信息
UserInfoDesc=请输入您的信息。
UserInfoName=&用户名:
UserInfoOrg=&组织:
UserInfoSerial=&序列号:
UserInfoNameRequired=您必须输入一个名称。

; *** "选择目标位置" 向导页面
WizardSelectDir=选择目标位置
SelectDirDesc=[name] 应该安装在哪里？
SelectDirLabel3=安装程序将把 [name] 安装到以下文件夹中。
SelectDirBrowseLabel=要继续，请单击下一步。如果您想选择其他文件夹，请单击浏览。
DiskSpaceGBLabel=至少需要 [gb] GB 的可用磁盘空间。
DiskSpaceMBLabel=至少需要 [mb] MB 的可用磁盘空间。
CannotInstallToNetworkDrive=安装程序无法安装到网络驱动器。
CannotInstallToUNCPath=安装程序无法安装到 UNC 路径。
InvalidPath=您必须输入带有驱动器号的完整路径；例如:%n%nC:\APP%n%n或以下形式的 UNC 路径:%n%n\\server\share
InvalidDrive=您选择的驱动器或 UNC 共享不存在或无法访问。请选择另一个。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序至少需要 %1 KB 的可用空间才能安装，但所选驱动器只有 %2 KB 可用。%n%n您是否仍要继续？
DirNameTooLong=文件夹名称或路径太长。
InvalidDirName=文件夹名称无效。
BadDirName32=文件夹名称不能包含以下任何字符:%n%n%1
DirExistsTitle=文件夹存在
DirExists=文件夹:%n%n%1%n%n已存在。您是否仍要安装到该文件夹？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹:%n%n%1%n%n不存在。您是否要创建该文件夹？

; *** "选择组件" 向导页面
WizardSelectComponents=选择组件
SelectComponentsDesc=应该安装哪些组件？
SelectComponentsLabel2=选择您要安装的组件；清除您不想安装的组件。准备好继续时单击下一步。
FullInstallation=完整安装
; 如果可能，请不要将 'Compact' 翻译为 'Minimal' (即您语言中的 'Minimal')
CompactInstallation=精简安装
CustomInstallation=自定义安装
NoUninstallWarningTitle=组件存在
NoUninstallWarning=安装程序检测到以下组件已在您的计算机上安装:%n%n%1%n%n取消选择这些组件不会卸载它们。%n%n您是否仍要继续？
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceGBLabel=当前选择至少需要 [gb] GB 的磁盘空间。
ComponentsDiskSpaceMBLabel=当前选择至少需要 [mb] MB 的磁盘空间。

; *** "选择附加任务" 向导页面
WizardSelectTasks=选择附加任务
SelectTasksDesc=应该执行哪些附加任务？
SelectTasksLabel2=选择您希望安装程序在安装 [name] 时执行的附加任务，然后单击下一步。

; *** "选择开始菜单文件夹" 向导页面
WizardSelectProgramGroup=选择开始菜单文件夹
SelectStartMenuFolderDesc=安装程序应该在哪里放置程序的快捷方式？
SelectStartMenuFolderLabel3=安装程序将在以下开始菜单文件夹中创建程序的快捷方式。
SelectStartMenuFolderBrowseLabel=要继续，请单击下一步。如果您想选择其他文件夹，请单击浏览。
MustEnterGroupName=您必须输入一个文件夹名称。
GroupNameTooLong=文件夹名称或路径太长。
InvalidGroupName=文件夹名称无效。
BadGroupName=文件夹名称不能包含以下任何字符:%n%n%1
NoProgramGroupCheck2=&不要创建开始菜单文件夹

; *** "准备安装" 向导页面
WizardReady=准备安装
ReadyLabel1=安装程序现在已准备好开始在您的计算机上安装 [name]。
ReadyLabel2a=单击安装继续安装，或单击上一步如果您想查看或更改任何设置。
ReadyLabel2b=单击安装继续安装。
ReadyMemoUserInfo=用户信息:
ReadyMemoDir=目标位置:
ReadyMemoType=安装类型:
ReadyMemoComponents=选定的组件:
ReadyMemoGroup=开始菜单文件夹:
ReadyMemoTasks=附加任务:

; *** TDownloadWizardPage 向导页面和 DownloadTemporaryFile
DownloadingLabel2=正在下载文件...
ButtonStopDownload=&停止下载
StopDownload=您确定要停止下载吗？
ErrorDownloadAborted=下载已中止
ErrorDownloadFailed=下载失败: %1 %2
ErrorDownloadSizeFailed=获取大小失败: %1 %2
ErrorProgress=无效进度: %1 / %2
ErrorFileSize=无效文件大小: 期望 %1，发现 %2

; *** TExtractionWizardPage 向导页面和 ExtractArchive
ExtractingLabel=正在提取文件...
ButtonStopExtraction=&停止提取
StopExtraction=您确定要停止提取吗？
ErrorExtractionAborted=提取已中止
ErrorExtractionFailed=提取失败: %1

; *** 归档提取失败详情
ArchiveIncorrectPassword=密码不正确
ArchiveIsCorrupted=归档已损坏
ArchiveUnsupportedFormat=归档格式不受支持

; *** "准备安装" 向导页面
WizardPreparing=准备安装
PreparingDesc=安装程序正在准备在您的计算机上安装 [name]。
PreviousInstallNotCompleted=先前程序的安装/卸载未完成。您需要重新启动计算机以完成该安装。%n%n重新启动计算机后，再次运行安装程序以完成 [name] 的安装。
CannotContinue=安装程序无法继续。请单击取消退出。
ApplicationsFound=以下应用程序正在使用需要由安装程序更新的文件。建议您允许安装程序自动关闭这些应用程序。
ApplicationsFound2=以下应用程序正在使用需要由安装程序更新的文件。建议您允许安装程序自动关闭这些应用程序。安装完成后，安装程序将尝试重新启动这些应用程序。
CloseApplications=&自动关闭应用程序
DontCloseApplications=&不要关闭应用程序
ErrorCloseApplications=安装程序无法自动关闭所有应用程序。建议您在继续之前关闭所有使用需要由安装程序更新的文件的应用程序。
PrepareToInstallNeedsRestart=安装程序必须重新启动您的计算机。重新启动计算机后，再次运行安装程序以完成 [name] 的安装。%n%n您现在要重新启动吗？

; *** "正在安装" 向导页面
WizardInstalling=正在安装
InstallingLabel=请稍候，安装程序正在您的计算机上安装 [name]。

; *** "安装完成" 向导页面
FinishedHeadingLabel=完成 [name] 安装向导
FinishedLabelNoIcons=安装程序已在其计算机上完成安装 [name]。
FinishedLabel=安装程序已在其计算机上完成安装 [name]。可以通过选择安装的快捷方式来启动应用程序。
ClickFinish=单击完成退出安装程序。
FinishedRestartLabel=要完成 [name] 的安装，安装程序必须重新启动您的计算机。您现在要重新启动吗？
FinishedRestartMessage=要完成 [name] 的安装，安装程序必须重新启动您的计算机。%n%n您现在要重新启动吗？
ShowReadmeCheck=是的，我想查看 README 文件
YesRadio=&是，现在重新启动计算机
NoRadio=&否，我稍后重新启动计算机
; 例如用作 'Run MyProg.exe'
RunEntryExec=运行 %1
; 例如用作 'View Readme.txt'
RunEntryShellExec=查看 %1

; *** "安装程序需要下一张磁盘" 内容
ChangeDiskTitle=安装程序需要下一张磁盘
SelectDiskLabel2=请插入磁盘 %1 并单击确定。%n%n如果此磁盘上的文件可以在下面显示的文件夹之外的其他文件夹中找到，请输入正确的路径或单击浏览。
PathLabel=&路径:
FileNotInDir2=无法在 "%2" 中找到文件 "%1"。请插入正确的磁盘或选择另一个文件夹。
SelectDirectoryLabel=请指定下一张磁盘的位置。

; *** 安装阶段消息
SetupAborted=安装程序未完成。%n%n请纠正问题并再次运行安装程序。
AbortRetryIgnoreSelectAction=选择操作
AbortRetryIgnoreRetry=&重试
AbortRetryIgnoreIgnore=&忽略错误并继续(不推荐)
AbortRetryIgnoreCancel=取消安装
RetryCancelSelectAction=选择操作
RetryCancelRetry=&重试
RetryCancelCancel=取消

; *** 安装状态消息
StatusClosingApplications=正在关闭应用程序...
StatusCreateDirs=正在创建目录...
StatusExtractFiles=正在提取文件...
StatusDownloadFiles=正在下载文件...
StatusCreateIcons=正在创建快捷方式...
StatusCreateIniEntries=正在创建 INI 条目...
StatusCreateRegistryEntries=正在创建注册表条目...
StatusRegisterFiles=正在注册文件...
StatusSavingUninstall=正在保存卸载信息...
StatusRunProgram=正在完成安装...
StatusRestartingApplications=正在重新启动应用程序...
StatusRollback=正在回滚更改...

; *** 杂项错误
ErrorInternal2=内部错误: %1
ErrorFunctionFailedNoCode=%1 失败
ErrorFunctionFailed=%1 失败；代码 %2
ErrorFunctionFailedWithMessage=%1 失败；代码 %2。%n%3
ErrorExecutingProgram=无法执行文件:%n%1

; *** 注册表错误
ErrorRegOpenKey=打开注册表项时出错:%n%1\%2
ErrorRegCreateKey=创建注册表项时出错:%n%1\%2
ErrorRegWriteKey=写入注册表项时出错:%n%1\%2

; *** INI 错误
ErrorIniEntry=在文件 "%1" 中创建 INI 条目时出错。

; *** 文件复制错误
FileAbortRetryIgnoreSkipNotRecommended=&跳过此文件(不推荐)
FileAbortRetryIgnoreIgnoreNotRecommended=&忽略错误并继续(不推荐)
SourceIsCorrupted=源文件已损坏
SourceDoesntExist=源文件 "%1" 不存在
SourceVerificationFailed=源文件验证失败: %1
VerificationSignatureDoesntExist=签名文件 "%1" 不存在
VerificationSignatureInvalid=签名文件 "%1" 无效
VerificationKeyNotFound=签名文件 "%1" 使用未知密钥
VerificationFileNameIncorrect=文件名称不正确
VerificationFileTagIncorrect=文件标签不正确
VerificationFileSizeIncorrect=文件大小不正确
VerificationFileHashIncorrect=文件哈希不正确
ExistingFileReadOnly2=无法替换现有文件，因为它被标记为只读。
ExistingFileReadOnlyRetry=&移除只读属性并重试
ExistingFileReadOnlyKeepExisting=&保留现有文件
ErrorReadingExistingDest=尝试读取现有文件时出错:
FileExistsSelectAction=选择操作
FileExists2=文件已存在。
FileExistsOverwriteExisting=&覆盖现有文件
FileExistsKeepExisting=&保留现有文件
FileExistsOverwriteOrKeepAll=&对下一个冲突执行此操作
ExistingFileNewerSelectAction=选择操作
ExistingFileNewer2=现有文件比安装程序尝试安装的文件更新。
ExistingFileNewerOverwriteExisting=&覆盖现有文件
ExistingFileNewerKeepExisting=&保留现有文件(推荐)
ExistingFileNewerOverwriteOrKeepAll=&对下一个冲突执行此操作
ErrorChangingAttr=尝试更改现有文件的属性时出错:
ErrorCreatingTemp=尝试在目标目录中创建文件时出错:
ErrorReadingSource=尝试读取源文件时出错:
ErrorCopying=尝试复制文件时出错:
ErrorDownloading=尝试下载文件时出错:
ErrorExtracting=尝试提取归档时出错:
ErrorReplacingExistingFile=尝试替换现有文件时出错:
ErrorRestartReplace=RestartReplace 失败:
ErrorRenamingTemp=尝试重命名目标目录中的文件时出错:
ErrorRegisterServer=无法注册 DLL/OCX: %1
ErrorRegSvr32Failed=RegSvr32 退出代码 %1
ErrorRegisterTypeLib=无法注册类型库: %1

; *** 安装后错误
ErrorOpeningReadme=尝试打开 README 文件时出错。
ErrorRestartingComputer=安装程序无法重新启动计算机。请手动执行。

; *** 卸载程序显示名称标记
; 例如用作 'My Program (32-bit)'
UninstallDisplayNameMark=%1 (%2)
; 例如用作 'My Program (32-bit, All users)'
UninstallDisplayNameMarks=%1 (%2, %3)
UninstallDisplayNameMark32Bit=32位
UninstallDisplayNameMark64Bit=64位
UninstallDisplayNameMarkAllUsers=所有用户
UninstallDisplayNameMarkCurrentUser=当前用户

; *** 卸载程序消息
UninstallNotFound=文件 "%1" 不存在。无法卸载。
UninstallOpenError=无法打开文件 "%1"。无法卸载
UninstallUnsupportedVer=卸载日志文件 "%1" 是此版本的卸载程序无法识别的格式。无法卸载
UninstallUnknownEntry=在卸载日志中遇到未知条目 (%1)
ConfirmUninstall=您确定要完全删除 %1 及其所有组件吗？
UninstallOnlyOnWin64=此安装只能在 64 位 Windows 上卸载。
OnlyAdminCanUninstall=此安装只能由具有管理员权限的用户卸载。
UninstallStatusLabel=请稍候，%1 正从您的计算机中删除。
UninstalledAll=%1 已成功从您的计算机中删除。
UninstalledMost=%1 卸载完成。%n%n某些元素无法删除。这些可以手动删除。
UninstalledAndNeedsRestart=要完成 %1 的卸载，必须重新启动您的计算机。%n%n您现在要重新启动吗？
UninstallDataCorrupted="%1" 文件已损坏。无法卸载

; *** 卸载阶段消息
ConfirmDeleteSharedFileTitle=删除共享文件？
ConfirmDeleteSharedFile2=系统指示以下共享文件不再被任何程序使用。您是否希望卸载程序删除此共享文件？%n%n如果任何程序仍在使用此文件并且它被删除，这些程序可能无法正常运行。如果您不确定，请选择否。将文件留在系统上不会造成任何损害。
SharedFileNameLabel=文件名:
SharedFileLocationLabel=位置:
WizardUninstalling=卸载状态
StatusUninstalling=正在卸载 %1...

; *** 关闭阻止原因
ShutdownBlockReasonInstallingApp=正在安装 %1。
ShutdownBlockReasonUninstallingApp=正在卸载 %1。

; 以下自定义消息不是由安装程序本身使用的，但如果您在脚本中使用它们，
; 您需要将它们翻译。

[CustomMessages]

NameAndVersion=%1 版本 %2
AdditionalIcons=附加快捷方式:
CreateDesktopIcon=创建&桌面快捷方式
CreateQuickLaunchIcon=创建&快速启动快捷方式
ProgramOnTheWeb=%1 在线
UninstallProgram=卸载 %1
LaunchProgram=启动 %1
AssocFileExtension=&将 %1 与 %2 文件扩展名关联
AssocingFileExtension=正在将 %1 与 %2 文件扩展名关联...
AutoStartProgramGroupDescription=启动:
AutoStartProgram=自动启动 %1
AddonHostProgramNotFound=在您选择的文件夹中找不到 %1。%n%n您是否仍要继续？