import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import argparse

def load_and_align_signals(file1, file2, fs, visualize=False):
    """
    加载并对齐两路IQ信号
    :param file1: USRP1的IQ文件路径
    :param file2: USRP2的IQ文件路径
    :param fs: 采样率 (Hz)
    :param visualize: 是否显示信号波形
    :return: (signal1, signal2, time_delay_seconds)
    """
    # 加载原始信号
    sig1 = np.fromfile(file1, dtype=np.complex64)
    sig2 = np.fromfile(file2, dtype=np.complex64)
    
    print(f"[状态] 原始信号长度 - USRP1: {len(sig1)}, USRP2: {len(sig2)}")

    # 自动对齐长度（取最小公共长度）
    min_len = min(len(sig1), len(sig2))
    sig1 = sig1[:min_len]
    sig2 = sig2[:min_len]
    print(f"[状态] 对齐后长度: {min_len}")

    # 可视化原始信号（可选）
    if visualize:
        plt.figure(figsize=(12, 6))
        plt.plot(np.real(sig1), label='USRP1 I路', alpha=0.7)
        plt.plot(np.real(sig2), label='USRP2 I路', alpha=0.7)
        plt.title("对齐后的信号对比")
        plt.xlabel("采样点")
        plt.ylabel("幅度")
        plt.legend()
        plt.show()

    return sig1, sig2

def compute_time_delay(sig1, sig2, fs, method='fft'):
    """
    计算两路信号的时间差
    :param sig1: 信号1 (复数IQ)
    :param sig2: 信号2 (复数IQ)
    :param fs: 采样率 (Hz)
    :param method: 计算方法 ('fft'或'direct')
    :return: (time_delay_seconds, correlation_peak_ratio)
    """
    # 计算互相关
    if method == 'fft':
        corr = signal.correlate(sig1, sig2, mode='same', method='fft')
    else:
        corr = signal.correlate(sig1, sig2, mode='same', method='direct')
    
    # 生成时延标尺
    lags = signal.correlation_lags(len(sig1), len(sig2), mode='same')
    
    # 找到峰值位置
    peak_idx = np.argmax(np.abs(corr))
    peak_lag = lags[peak_idx]
    
    # 计算时间差
    time_delay = peak_lag / fs
    
    # 计算峰值显著性比
    peak_ratio = np.abs(corr[peak_idx]) / np.mean(np.abs(corr))
    
    return time_delay, peak_ratio, corr, lags

def main():
    parser = argparse.ArgumentParser(description="USRP信号时间差分析工具")
    parser.add_argument("file1",help="USRP1的IQ数据文件路径")
    parser.add_argument("file2",help="USRP2的IQ数据文件路径")
    parser.add_argument("--fs", type=float, default=10e6, help="采样率 (Hz)")
    parser.add_argument("--visualize", action="store_true", help="显示信号波形")
    args = parser.parse_args()

    try:
        # 1. 加载并对齐信号
        sig1, sig2 = load_and_align_signals(args.file1, args.file2, args.fs, args.visualize)

        # 2. 计算时间差
        delay, peak_ratio, corr, lags = compute_time_delay(sig1, sig2, args.fs)
        
        # 3. 输出结果
        print("\n[结果] 时间差分析报告")
        print(f"采样率: {args.fs/1e6} MHz")
        print(f"时延 (采样点): {delay * args.fs:.1f}")
        print(f"时延 (秒): {delay:.6f}")
        print(f"时延 (微秒): {delay * 1e6:.3f}")
        print(f"峰值显著性比: {peak_ratio:.1f} (建议>10)")

        # 4. 可视化互相关结果
        if args.visualize:
            plt.figure(figsize=(12, 4))
            plt.plot(lags/args.fs, np.abs(corr))
            plt.title("互相关结果 (绝对值)")
            plt.xlabel("Time Delay (s)")
            plt.ylabel("Correlation Magnitude")
            plt.grid()
            plt.show()

        # 5. 结果验证建议
        if peak_ratio < 5:
            print("\n[警告] 峰值不显著，请检查：")
            print("- 信号是否真的相关")
            print("- 截断时是否保留了重叠时段")
            print("- 尝试滤波或调整截断位置")

    except Exception as e:
        print(f"\n[错误] 分析失败: {str(e)}")

if __name__ == "__main__":
    main()
