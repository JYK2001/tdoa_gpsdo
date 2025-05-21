import uhd
import numpy as np
import time

# 参数设置
center_freq = 2.4e9  # 2.4 GHz
sample_rate = 56e6  # 0.5 MSps
gain = 40  # 接收增益
num_samples = int(0.00001* sample_rate)  # 采集 2 秒的数据
buffer_size =32768 # 缓冲区大小
file_name = "signal1.bin"

# 初始化 USRP
usrp = uhd.usrp.MultiUSRP()
usrp.set_rx_rate(sample_rate)
usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(center_freq))
usrp.set_rx_gain(gain)
usrp.set_clock_source("external", 0)  # 使用 GPSDO 时钟
usrp.set_time_source("external", 0)  # 使用 GPSDO 时间源
print(f"当前 USRP 时间源: {usrp.get_time_source(0)}")
print(f"当前 USRP 时钟源: {usrp.get_clock_source(0)}")
usrp.set_time_now(uhd.types.TimeSpec(0.0))
time.sleep(1)  # 等待 1 秒，确保 USRP 处理命令

# 确保 USRP 已检测到 GPSDO 的 PPS 信号
last_pps_time = usrp.get_time_last_pps().get_real_secs()
print(f"当前 USRP 时间: {usrp.get_time_now().get_real_secs()}")
print(f"最近的 PPS 触发时间: {last_pps_time}")

# 等待下一个 PPS 触发
while True:
    new_pps_time = usrp.get_time_last_pps().get_real_secs()
    if new_pps_time > last_pps_time:
        break
    time.sleep(0.001)

print(f"PPS 触发，当前 USRP 时间: {usrp.get_time_now().get_real_secs()}")

# 在 PPS 触发前立即设置下一个 PPS 触发时刻
usrp.set_time_next_pps(uhd.types.TimeSpec(9.0))

# 再次等待 PPS 触发
last_pps_time = usrp.get_time_last_pps().get_real_secs()
while True:
    new_pps_time = usrp.get_time_last_pps().get_real_secs()
    if new_pps_time > last_pps_time:
        break
    time.sleep(0.001)

# 记录 PPS 触发时间
pps_time = usrp.get_time_now().get_real_secs()
print(f"第二次 PPS 触发，当前 USRP 时间: {pps_time}")

# 创建流
stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
stream_args.args = "recv_buff_size=10000000,recv_frame_size=65536,num_recv_frames=512"
streamer = usrp.get_rx_stream(stream_args)
metadata = uhd.types.RXMetadata()
recv_buffer = np.zeros((buffer_size,), dtype=np.complex64)
received_samples = np.zeros((num_samples,), dtype=np.complex64)  # 预分配数组

# 等待 1 秒以确保时间稳定
time.sleep(0) 

# 启动接收流
streamer.issue_stream_cmd(uhd.types.StreamCMD(uhd.types.StreamMode.start_cont))
start_time = usrp.get_time_now().get_real_secs()
print(f"信号采集开始，当前 USRP 时间: {start_time}")

# 记录信号
write_index = 0
while write_index < num_samples:
    num_recv = streamer.recv(recv_buffer, metadata, timeout=1.0)
    
    if metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
        print("RX Metadata warning: Overflow detected, continuing...")
        continue  # 忽略溢出错误，继续采集
    elif metadata.error_code != uhd.types.RXMetadataErrorCode.none:
        print(f"RX Metadata error: {metadata.error_code}")
        break  # 其他错误则终止

    # 确保不超过数组边界
    num_samples_to_copy = min(num_recv, num_samples - write_index)
    
    # 直接存入 NumPy 数组
    received_samples[write_index : write_index + num_samples_to_copy] = recv_buffer[:num_samples_to_copy]
    write_index += num_samples_to_copy

# 停止流
streamer.issue_stream_cmd(uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont))

end_time = usrp.get_time_now().get_real_secs()
print(f"信号采集完成，当前 USRP 时间: {end_time}")

# 保存数据
received_samples.tofile(file_name)

print(f"信号采集完成，已保存到 {file_name}，PPS 时间戳: {pps_time}，信号采集时间戳: {start_time}")
