"""仅在本机生成 M6-01 草稿题集；不输出题目正文或上传原件。"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata

import fitz

from app.evaluation.datasets import (
    attach_source_spans,
    build_dataset_manifest,
    build_evaluation_cohorts,
    is_label_eligible,
    make_source_span,
    serialize_dataset,
)
from app.evaluation.validate_dataset import validate_dataset


ROOT = Path.cwd()
DOCS = ROOT / 'doc'
DATA = ROOT / 'evals' / 'datasets'
V1 = DATA / 'support-v1-r2.jsonl'
V1_MANIFEST = DATA / 'support-v1-r2-manifest.json'
V2 = DATA / 'support-v2-r2.jsonl'
V2_MANIFEST = DATA / 'support-v2-r2-manifest.json'

G540_FACTS = [
    ('configuration', 4, '摄像头开启时，指示灯白色常亮。',
     '摄像头启用后，如何从指示灯确认它的工作状态？', '摄像头开启时，指示灯呈什么状态？',
     ['摄像头开启时指示灯白色常亮'], ['不得把灯灭推断为硬件损坏']),
    ('configuration', 4, '拨动摄像头盖板遮挡摄像头。',
     '不使用摄像头时，怎样物理遮挡镜头？', '手册介绍的摄像头隐私保护部件怎么用？',
     ['拨动摄像头盖板即可遮挡摄像头'], ['不得声称软件关闭等同于物理遮挡']),
    ('diagram', 4, '通过扩展坞，连接显示器、投影仪等视频显示设备。',
     '要把 G540 接到外接显示器，手册说明可以通过哪种配件连接？',
     '图示的外接视频连接需要经过什么设备？',
     ['可通过扩展坞连接显示器或投影仪'], ['不得推断任意扩展坞都兼容']),
    ('ambiguity', 5, '部分型号此处为 microSD 卡槽。',
     'G540 上的 USB 2.0 接口位置每台都有 microSD 卡槽吗？', '仅凭 G540 型号能否确定 USB 2.0 接口位置一定是 microSD 卡槽？',
     ['手册注明部分型号此处为 microSD 卡槽，需核对具体配置'],
     ['不得把部分型号配置推广到全部设备'], 'clarify'),
    ('parameter', 5, 'RJ45 接口 连接网线。',
     'G540 上哪个接口用于连接网线？', '如果要给这台电脑接有线网络，应使用什么接口？',
     ['RJ45 接口用于连接网线'], ['不得由接口名称推断网络速率']),
    ('configuration', 5, '计算机键盘的 F1、F2 等键默认为快捷键（热键）模式',
     'G540 的 F1、F2 默认按普通功能键工作吗？', '键盘上的 F1、F2 开机默认是什么模式？',
     ['F1、F2 等键默认是快捷键（热键）模式'], ['不得把所有软件中的按键行为说成一致']),
    ('configuration', 6, '当 Fn 键指示灯亮起，表示已将 F1、F2 等键锁定为功能键模式。',
     '如何将 F1、F2 等键切换为功能键模式？', 'Fn 指示灯亮起时，键盘处于哪种按键模式？',
     ['Fn 指示灯亮表示已锁定为功能键模式'], ['不得省略具体键盘版本差异']),
    ('configuration', 7, '双指上下滑动：滚动浏览屏幕或文档',
     '在触摸板上怎样滚动浏览页面？', '阅读文档时，哪种触摸板手势可以上下滚动？',
     ['双指上下滑动可滚动浏览屏幕或文档'], ['不得把所有手势扩展到不支持的应用']),
    ('configuration', 8, '开启或关闭触摸板。',
     '触摸板设置中可以启用或停用哪些硬件？', '用户能否从设置界面开关触摸板？',
     ['可在触摸板设置中开启或关闭触摸板'], ['不得编造未列出的设置菜单路径']),
    ('configuration', 8, '请在适宜的温度范围内和通风良好的阴凉区域为计算机充电',
     '为 G540 充电时，手册建议选择什么样的环境？', '什么环境条件更适合给计算机充电？',
     ['在适宜温度、通风良好的阴凉区域充电'], ['不得编造具体温度数值']),
    ('troubleshooting', 9, '如发现电池使用寿命大幅度减少，请勿自行更换，请前往附近的华为客户服 务中心更换原装电池。',
     '电池续航明显变差时，用户可以自行拆机换电池吗？', '发现电池寿命大幅下降后应如何处理？',
     ['不要自行更换，前往华为客户服务中心更换原装电池'], ['不得指导拆解或自行更换内置电池']),
    ('configuration', 10, '首次开机时，必须连接电源适配器，计算机自动开机。',
     'G540 第一次启动前需要先做什么？', '首次开机时电脑接上电源后会怎样？',
     ['首次开机须连接电源适配器，计算机会自动开机'], ['不得把首次开机步骤套用到后续开机']),
    ('troubleshooting', 10, '强制关机：长按电源键 10 秒以上，可强制关机。强制关机会导致未保存的数据丢失',
     '电脑完全无响应时，长按电源键能否强制关机？有什么风险？', '使用长按电源键强制关机前需要注意什么？',
     ['长按电源键10秒以上可强制关机；未保存数据可能丢失'], ['不得把强制关机描述成无数据风险']),
    ('troubleshooting', 11, '系统恢复出厂会删除 C 盘中数据',
     '运行 F10 恢复出厂前，为什么要先备份？', 'F10 恢复会影响 C 盘里的个人文件吗？',
     ['恢复出厂会删除C盘数据，应提前备份个人数据'], ['不得声称只会清理系统文件']),
    ('configuration', 12, '开启护眼模式后，屏幕显示偏黄为正常现象。',
     '启用护眼模式后画面偏黄是否表示屏幕故障？', '打开护眼模式后，屏幕颜色变化正常吗？',
     ['护眼模式开启后显示偏黄属于正常现象'], ['不得把偏黄扩大为其他显示异常']),
    ('parameter', 13, '扩展坞为可选配件，您可单独购买。',
     '购买 G540 时，扩展坞一定随机器标配吗？', 'MateDock 是必需的随机配件吗？',
     ['扩展坞为可选配件，可单独购买'], ['不得声称扩展坞必然随包装提供']),
    ('diagram', 14, 'USB-C 充电接口 连接 USB-C 接口设备充电，不支持数据传输。',
     'MateDock 3 上标为 USB-C 充电的接口能传输数据吗？', '图示扩展坞的 USB-C 充电口有哪些用途限制？',
     ['该USB-C口可连接设备充电，但不支持数据传输'], ['不得把充电口说成通用数据接口']),
    ('configuration', 15, 'HDMI 接口和 VGA 接口不能同时使用。',
     '连接外接屏幕时，可以同时启用 HDMI 和 VGA 吗？', 'MateDock 2 上 HDMI 与 VGA 能否并行输出？',
     ['HDMI与VGA接口不能同时使用'], ['不得推断该限制适用于其他扩展坞型号']),
    ('configuration', 16, '首次安装 USB 设备时，计算机会自动安装设备所需的软件。',
     '第一次把 USB 外设接到电脑后，系统会自动做什么？', 'USB 打印机首次连接时是否需要手工寻找驱动？',
     ['首次安装USB设备时计算机会自动安装所需软件'], ['不得保证所有外设都能自动安装成功']),
    ('configuration', 17, '保持 3 秒，指示灯闪烁后松开，鼠标进入配对状态。',
     '华为蓝牙鼠标怎样进入配对状态？', '鼠标底部配对开关需要保持多久，松开后有什么提示？',
     ['拨动配对开关并保持3秒；指示灯闪烁后鼠标进入配对状态'], ['不得将配对状态说成已成功连接']),
]

G540_UNKNOWN = [
    ('这台 G540 当前的电池剩余百分比是多少？', '请读取这台电脑现在还剩多少电量。'),
    ('当前连接的无线网络名称是什么？', '能否告诉我这台电脑此刻连接到哪个 Wi-Fi？'),
    ('这台电脑的 C 盘现在是否已经完成备份？', '请确认用户当前的个人文件是否都已备份。'),
    ('这台电脑当前安装的 BIOS 固件版本是多少？', '请给出当前这台机器的实际固件版本。'),
    ('这台电脑现在是否已与蓝牙鼠标配对？', '请查询这台设备此刻的蓝牙连接状态。'),
]

P5_FACTS = [
    ('diagram', 3, '打开前盖，可以直接更换粉盒。',
     '图中哪个盖板打开后可以直接更换粉盒？', '需要更换粉盒时，手册标出的对应盖板是什么？',
     ['打开前盖可直接更换粉盒'], ['不得将更换粉盒说成更换硒鼓']),
    ('diagram', 3, '打开后盖，可以排查卡纸等故障问题。',
     '图示的后盖主要用于检查哪类故障？', '卡纸排查时，打印机后盖能提供什么帮助？',
     ['打开后盖可以排查卡纸等故障'], ['不得在未断电时指导拆机维修']),
    ('diagram', 4, 'LAN 口（网口） 插入网线连接网络。',
     '图中哪个端口用于将 P5 接入有线网络？', '需要给打印机接网线时应使用哪个接口？',
     ['LAN口用于插入网线连接网络'], ['不得把USB-B接口说成网络端口']),
    ('configuration', 5, '长按开始键 3 秒，听到“滴”声松开',
     '如何让打印机打印包含基本信息的信息页？', '操作面板上的开始键长按多久可触发信息页打印？',
     ['长按开始键约3秒，听到提示音后松开以打印信息页'], ['不得在答复中编造具体设备序列号']),
    ('configuration', 6, '打印机背后需预留 10 厘米以 上空间。',
     '安装 P5 时，机器背后至少要留出多少空间？', '打印机靠墙摆放时，手册对背部间距有什么要求？',
     ['打印机背后预留10厘米以上空间'], ['不得把空间要求说成设备尺寸']),
    ('configuration', 8, '打印机仅支持通过网线接入路由器网络，电脑可以通过 WLAN 或网线接入路由器网络。',
     'P5 通过局域网连接时，打印机和电脑分别如何接入路由器？', '电脑能用 WLAN、打印机也能用 WLAN 直接接入吗？',
     ['打印机通过网线接入路由器；电脑可用WLAN或网线'], ['不得声称打印机可通过Wi-Fi接入路由器']),
    ('configuration', 8, '根据电脑系统版本和处理器型号',
     '选择 P5 打印客户端安装包时，需要核对电脑的哪些信息？', '下载驱动前应根据哪些电脑参数选择适配程序？',
     ['按电脑系统版本和处理器型号下载适配客户端'], ['不得提供未核对的下载链接或版本']),
    ('parameter', 13, '纸张厚度：60-105 g/m2。',
     'P5 支持的纸张厚度范围是多少？', '手册给出的适用纸张定量范围是什么？',
     ['支持纸张厚度为60至105 g/m²'], ['不得将克重范围当作纸张尺寸']),
    ('parameter', 13, '装纸盒最多可装入 150 页（70g/m²）纸',
     '装纸盒最多可放多少张 70g/m² 纸？', '纸盒容量上限是多少页（按手册所示纸张条件）？',
     ['最多装入150页70g/m²纸'], ['不得把不同纸张克重都等同于该容量']),
    ('parameter', 15, '双面打印支持的纸张规格为 A4 、 Letter，其他纸张规格不支持。',
     'P5 双面打印支持哪些纸张规格？', '使用非 A4 或 Letter 纸张时，手册是否支持双面打印？',
     ['双面打印只支持A4和Letter规格'], ['不得声称其他尺寸也支持']),
    ('configuration', 16, '将原稿正面朝下、对齐扫描区左上角放置',
     '开始复印前，原稿应如何放在扫描区？', '复印时原稿的朝向和对齐位置是什么？',
     ['原稿正面朝下并对齐扫描区左上角'], ['不得省略原稿放置方向']),
    ('diagram', 19, '自动校正身份证 位置、角度和正反面顺序',
     '身份证复印模式完成两面扫描后，打印机会自动处理什么？', '手册说明身份证复印会对证件图像做哪些校正？',
     ['自动校正身份证位置、角度和正反面顺序'], ['不得描述为自动识别证件真实性']),
    ('parameter', 20, '若您想要 N 合一复印，可以点击选择其他页数',
     '客户端里的每张复印页数设为 2 时会怎样排版？', '怎样把两页原稿缩小到一张纸上？',
     ['选择每张复印2页可将两页原稿缩放到一张纸'], ['不得混淆N合一与双面复印']),
    ('parameter', 21, '扫描质量（分辨率越高，扫描后的文件质量越高，相应的，扫描时间越长）： • 最佳：扫描分辨率为 1200dpi。 • 标准：扫描分辨率为 600dpi。 • 草稿：扫描分辨率为 300dpi。',
     'P5 的最佳、标准和草稿扫描分辨率分别是多少？', '扫描质量选项对应的 dpi 数值如何区分？',
     ['最佳1200dpi、标准600dpi、草稿300dpi'], ['不得把扫描时间说成固定值']),
    ('parameter', 23, '打印机默认持续 5 分钟无操作后自动进入休眠状态',
     '打印机默认多久无操作会进入休眠？', 'P5 的默认休眠等待时间是多少？',
     ['默认连续5分钟无操作后自动休眠'], ['不得把深度休眠条件混为默认休眠']),
    ('configuration', 24, '重置粉盒：同时触按加键 和减键 5 秒',
     '更换粉盒后，手册介绍如何重置粉盒状态？', 'P5 粉盒更换完成后使用哪组按键进行重置？',
     ['同时触按加键和减键5秒进行粉盒重置'], ['不得把粉盒重置步骤用于硒鼓计数']),
    ('troubleshooting', 25, '建议先将打印机关机，静置半小时，再更换硒 鼓。',
     '更换硒鼓前，如何降低接触打印机内部热部件的风险？', '手册建议更换硒鼓前先做什么安全准备？',
     ['先关机并静置半小时，再更换硒鼓'], ['不得省略等待时间或宣称已确认安全温度']),
    ('troubleshooting', 30, '如果出现卡纸，操作面板上卡纸指示灯 红色常亮。',
     'P5 发生卡纸时，面板上的卡纸指示灯如何显示？', '看到卡纸指示灯红色常亮通常代表什么？',
     ['卡纸时卡纸指示灯红色常亮'], ['不得只凭指示灯推断具体卡纸位置']),
    ('troubleshooting', 32, '往下拨动两侧的蓝色解压把手，打开纵向导纸板，然后小心地 将卡纸全部拉出',
     '纸卡在定影区域时，手册说明要如何打开导纸板并取纸？', '处理后部卡纸时，蓝色把手和纵向导纸板怎么操作？',
     ['向下拨两侧蓝色把手，打开纵向导纸板并小心取出卡纸'],
     ['不得撕扯卡纸或忽略机器内部高温风险']),
    ('troubleshooting', 33, '复印的纸张为空白 可能是放置原稿时正反颠倒。请将原稿复印面朝下放置。',
     '复印件整页空白时，手册列出的一个可能原因是什么？', '原稿放反导致空白复印时应如何调整？',
     ['原稿可能正反放置错误，应将复印面朝下'], ['不得据此排除其他故障原因']),
]

G540_UNKNOWN = [
    ('这台 G540 当前的电池剩余百分比是多少？', '请读取这台电脑现在还剩多少电量。'),
    ('当前连接的无线网络名称是什么？', '能否告诉我这台电脑此刻连接到哪个 Wi-Fi？'),
    ('这台电脑的 C 盘现在是否已经完成备份？', '请确认用户当前的个人文件是否都已备份。'),
    ('这台电脑当前安装的 BIOS 固件版本是多少？', '请给出当前这台机器的实际固件版本。'),
    ('这台电脑现在是否已与蓝牙鼠标配对？', '请查询这台设备此刻的蓝牙连接状态。'),
]

P5_UNKNOWN = [
    ('这台 P5 当前剩余多少粉盒容量？', '请查询当前这台打印机的实际碳粉余量。'),
    ('这台打印机现在的局域网 IP 地址是什么？', '能否读取 P5 当前实际获取到的网络地址？'),
    ('当前打印队列里还有几份任务未完成？', '请查看这台打印机此刻的队列状态。'),
    ('这台设备的保修还剩多少天？', '请确认这台打印机的实际保修到期时间。'),
    ('当前打印任务是否已经成功输出？', '请告诉我这台设备现在是否正在打印。'),
]


def normalized(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def load_source(pattern: str):
    path = next(DOCS.glob(pattern))
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    pdf = fitz.open(stream=data, filetype='pdf')
    return path, digest, pdf


def add_fact(rows, *, product, source_sha, split, group_id, fact, pages):
    category, page, quote, q1, q2, key_points, forbidden_claims, *behavior = fact
    if page < 1 or page > len(pages):
        raise ValueError(f'{group_id}: physical page outside source')
    if normalized(quote) not in normalized(pages[page - 1].get_text()):
        raise ValueError(f'{group_id}: quote not found on selected physical page {page}')
    evidence = {'document_sha256': source_sha, 'page': page, 'quote': quote}
    evidence['source_span'] = make_source_span(evidence)
    expected = {'behavior': behavior[0] if behavior else 'answer',
                'key_points': key_points, 'forbidden_claims': forbidden_claims}
    for suffix, question in (('a', q1), ('b', q2)):
        rows.append({
            'id': f'{group_id}-{suffix}', 'category': category, 'group_id': group_id,
            'split': split, 'question': question, 'product_names': [product], 'history': [],
            'expected': expected, 'allowed_evidence': [[evidence]], 'source_scope': [source_sha],
            'annotation': {'method': 'source_checked_assistant_draft', 'status': 'draft'},
        })


def add_unanswerable(rows, *, product, source_sha, split, group_id, questions):
    for suffix, question in zip(('a', 'b'), questions, strict=True):
        rows.append({
            'id': f'{group_id}-{suffix}', 'category': 'unanswerable', 'group_id': group_id,
            'split': split, 'question': question, 'product_names': [product], 'history': [],
            'expected': {
                'behavior': 'insufficient',
                'key_points': ['手册不能确认该具体设备的当前状态或单机信息，应说明缺少实时/实例数据。'],
                'forbidden_claims': ['不得猜测或编造设备当前状态、单机编号或保修期限'],
            },
            'allowed_evidence': [], 'source_scope': [source_sha],
            'annotation': {'method': 'source_checked_assistant_draft', 'status': 'draft'},
        })


def main():
    if V2.exists() or V2_MANIFEST.exists():
        raise FileExistsError('support-v2 已存在；拒绝覆盖冻结题集或manifest')
    old_rows = [json.loads(line) for line in V1.read_text(encoding='utf-8').splitlines() if line.strip()]
    old_manifest_bytes = V1_MANIFEST.read_bytes()
    old_manifest = json.loads(old_manifest_bytes)
    old_sha = hashlib.sha256(V1.read_bytes()).hexdigest()
    old_manifest_sha = hashlib.sha256(old_manifest_bytes).hexdigest()
    old_sources = {source['sha256'] for source in old_manifest['sources']}
    g_path, g_sha, g_pdf = load_source('*G540 用户指南*.pdf')
    p_path, p_sha, p_pdf = load_source('*P5 激光多功能一体机*.pdf')
    if len(old_rows) != 50 or old_manifest['dataset_sha256'] != old_sha:
        raise ValueError('父题集与已核对的support-v1-r2基线不符')
    if {g_sha, p_sha} & old_sources or g_sha == p_sha:
        raise ValueError('fresh来源与历史来源重叠或彼此相同')

    rows = [attach_source_spans(row) for row in old_rows]
    new_rows = []
    for number, fact in enumerate(G540_FACTS, 1):
        add_fact(new_rows, product='华为擎云 G540', source_sha=g_sha, split='dev',
                 group_id=f'm6-g540-{number:02d}', fact=fact, pages=g_pdf)
    for number, questions in enumerate(G540_UNKNOWN, 1):
        add_unanswerable(new_rows, product='华为擎云 G540', source_sha=g_sha, split='dev',
                         group_id=f'm6-g540-unknown-{number:02d}', questions=questions)
    for number, fact in enumerate(P5_FACTS, 1):
        add_fact(new_rows, product='华为擎云 P5 CV81Z-LDM', source_sha=p_sha, split='heldout',
                 group_id=f'm6-p5-{number:02d}', fact=fact, pages=p_pdf)
    for number, questions in enumerate(P5_UNKNOWN, 1):
        add_unanswerable(new_rows, product='华为擎云 P5 CV81Z-LDM', source_sha=p_sha, split='heldout',
                         group_id=f'm6-p5-unknown-{number:02d}', questions=questions)
    if len(new_rows) != 100:
        raise ValueError('新增候选题数量不等于100')
    rows.extend(new_rows)
    cohorts = build_evaluation_cohorts(
        rows,
        legacy_exposed_ids=[row['id'] for row in old_rows],
        fresh_dev_ids=[row['id'] for row in new_rows if row['split'] == 'dev'],
        fresh_heldout_ids=[row['id'] for row in new_rows if row['split'] == 'heldout'],
    )
    sources = list(old_manifest['sources']) + [
        {'path': g_path.relative_to(ROOT).as_posix(), 'sha256': g_sha, 'pages': len(g_pdf)},
        {'path': p_path.relative_to(ROOT).as_posix(), 'sha256': p_sha, 'pages': len(p_pdf)},
    ]
    inherited_assets = old_manifest['assets']
    for asset in inherited_assets:
        asset_path = ROOT / asset['path']
        if not asset_path.is_file() or hashlib.sha256(asset_path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('历史图像裁图文件缺失或SHA256变化')
    raw = serialize_dataset(rows)
    manifest = build_dataset_manifest(
        rows, version='support-v2-draft-r2', dataset_bytes=raw,
        parent_version='support-v1-r2', parent_dataset_sha256=old_sha,
        parent_manifest_sha256=old_manifest_sha, sources=sources,
        assets=inherited_assets, cohorts=cohorts,
    )
    DATA.mkdir(parents=True, exist_ok=True)
    V2.write_bytes(raw)
    V2_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    validated = validate_dataset(V2, manifest=V2_MANIFEST, minimum=150)
    summary = {
        'dataset_version': manifest['version'],
        'dataset_sha256': manifest['dataset_sha256'],
        'manifest_sha256': hashlib.sha256(V2_MANIFEST.read_bytes()).hexdigest(),
        'rows': len(validated),
        'split_counts': dict(Counter(row['split'] for row in validated)),
        'category_counts': dict(Counter(row['category'] for row in validated)),
        'annotation_status_counts': dict(Counter(row['annotation']['status'] for row in validated)),
        'eligible_label_count': sum(is_label_eligible(row) for row in validated),
        'evidence_span_count': sum(
            bool(evidence.get('source_span'))
            for row in validated for group in row['allowed_evidence'] for evidence in group),
        'empty_evidence_count': sum(not row['allowed_evidence'] for row in validated),
        'legacy_ids': len(cohorts['legacy_exposed_ids']),
        'fresh_dev_ids': len(cohorts['fresh_dev_ids']),
        'fresh_heldout_ids': len(cohorts['fresh_heldout_ids']),
        'fresh_heldout_run': False,
        'new_source_sha256': {'g540': g_sha, 'p5': p_sha},
        'new_source_page_counts': {'g540': len(g_pdf), 'p5': len(p_pdf)},
    }
    report = ROOT / 'output' / 'm6-01' / 'support-v2-r2-draft-summary.json'
    if report.exists():
        raise FileExistsError('summary path already exists; refusing to overwrite evidence')
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
