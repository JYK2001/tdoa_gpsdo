#include <uhd/usrp/multi_usrp.hpp>
#include <thread>
#include <iostream>
#include <vector>
#include <numeric>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <algorithm> // std::replace

// 获取当前时间的字符串表示（ISO 8601格式）
std::string get_current_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto in_time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;
    std::stringstream ss;
    ss << std::put_time(std::localtime(&in_time_t), "%Y-%m-%d %H:%M:%S")
       << '.' << std::setfill('0') << std::setw(3) << ms.count();
    return ss.str();
}

int main() {
    try {
        // 初始化 USRP
        uhd::device_addr_t args;
        args["type"] = "b200";
        auto usrp = uhd::usrp::multi_usrp::make(args);

        // 强制尝试使用外部时钟和 PPS
        usrp->set_clock_source("external");
        usrp->set_time_source("external");
        usrp->set_master_clock_rate(32e6);

        // 等待参考时钟锁定
        bool ref_locked = false;
        for (int i = 0; i < 10; ++i) {
            ref_locked = usrp->get_mboard_sensor("ref_locked").to_bool();
            if (ref_locked) break;
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }

        if (!ref_locked) {
            std::cerr << "[警告] 外部参考时钟未锁定，切换到内部时钟和系统时间源\n";
            usrp->set_clock_source("internal");
            usrp->set_time_source("internal");
        }

        std::cout << "当前时钟源: " << usrp->get_clock_source(0)
                  << ", 当前时间源: " << usrp->get_time_source(0) << "\n";
        std::cout << "主时钟速率: " << usrp->get_master_clock_rate()/1e6 << " MHz\n";

        // 准备CSV文件（添加时间戳和元数据）
        std::string filename = "pps_jitter_" + get_current_timestamp() + ".csv";
        std::replace(filename.begin(), filename.end(), ':', '-');

        std::ofstream f(filename);
        f << "# PPS Jitter Analysis Report\n";
        f << "# Timestamp: " << get_current_timestamp() << "\n";
        f << "# Clock Source: " << usrp->get_clock_source(0) << "\n";
        f << "# Time Source: " << usrp->get_time_source(0) << "\n";
        f << "# Master Clock: " << usrp->get_master_clock_rate()/1e6 << " MHz\n";
        f << "Sample,Timestamp,Deviation(ns),PPS_Time\n";

        // PPS抖动采集
        const size_t N = 100;
        std::vector<double> deviations(N);
        double prev = usrp->get_time_last_pps().get_real_secs();

        for (size_t i = 0; i < N; ++i) {
            double curr;
            while (true) {
                curr = usrp->get_time_last_pps().get_real_secs();
                if (curr != prev) break;
                std::this_thread::sleep_for(std::chrono::microseconds(50));
            }

            deviations[i] = (curr - prev - 1.0) * 1e9;

            f << i << ","
              << get_current_timestamp() << ","
              << deviations[i] << ","
              << curr << "\n";

            prev = curr;

            if ((i + 1) % 10 == 0)
                std::cout << "采集进度: " << (i + 1) << "/" << N << std::endl;
        }

        // 结果统计
        double avg = std::accumulate(deviations.begin(), deviations.end(), 0.0) / N;
        auto [min, max] = std::minmax_element(deviations.begin(), deviations.end());

        f << "\n# Summary\n";
        f << "# Average," << avg << "\n";
        f << "# Peak-to-Peak," << (*max - *min) << "\n";
        f << "# Max Advance," << *min << "\n";
        f << "# Max Delay," << *max << "\n";

        std::cout << "\n=== 最终结果 ===\n"
                  << "平均周期误差: " << avg << " ns\n"
                  << "峰峰值抖动: " << (*max - *min) << " ns\n"
                  << "最大提前: " << *min << " ns\n"
                  << "最大延迟: " << *max << " ns" << std::endl;

        std::cout << "数据已保存到: " << filename << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "错误: " << e.what() << std::endl;
        return 1;
    }
}
