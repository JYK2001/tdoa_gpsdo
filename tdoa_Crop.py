import numpy as np
import os

def align_iq_files(iq_files, timestamps, output_dir, fs):
    """ 
    对齐多个 IQ 文件，裁剪较早的文件，使所有文件从相同时间开始 
    iq_files: 原始 IQ 数据文件列表
    timestamps: 手动输入的时间戳（单位：秒，支持微秒级）
    output_dir: 对齐后文件的输出目录
    fs: 采样率 (Hz)
    """
    
    # **步骤 1：找到最晚的时间戳**
    latest_start_time = max(timestamps)  # 以最晚开始的为基准

    # **步骤 2：计算每个文件的时间偏移量（单位：秒）**
    offsets = [latest_start_time - t for t in timestamps]

    # **步骤 3：遍历所有 IQ 文件，进行裁剪**
    os.makedirs(output_dir, exist_ok=True)  # 确保输出目录存在

    for i, iq_file in enumerate(iq_files):
        offset_samples = int(round(offsets[i] * fs ))  # **计算需要裁剪的采样点数**
        output_file = os.path.join(output_dir, os.path.basename(iq_file))

        print(f"处理 {iq_file}，裁剪 {offset_samples} 采样点...")

        # 读取 IQ 文件
        iq_data = np.fromfile(iq_file, dtype=np.complex64)

        # 如果需要裁剪，去掉前 offset_samples 采样点
        if offset_samples > 0:
            iq_data = iq_data[offset_samples:]

        # 保存裁剪后的 IQ 文件
        iq_data.tofile(output_file)
        print(f"已保存到 {output_file}")

    print("所有 IQ 文件对齐完成！")

# **手动输入时间戳（单位：秒，支持微秒）**
timestamps = [
    0.04035180357143,  # usrp_1 开始时间
    0.040741857142857,  # usrp_2 开始时间
    #1711344001.000789   # usrp_3 开始时间
]

# **示例调用**
iq_files = ["signal1.bin", "signal2.bin"#, "usrp_3_iq.bin"
]
output_dir = "aligned_iq"
fs = 40e6  # 采样率 1 MHz

align_iq_files(iq_files, timestamps, output_dir, fs)
