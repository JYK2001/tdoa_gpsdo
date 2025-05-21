#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/stream.hpp>
#include <uhd/types/tune_request.hpp>
#include <uhd/types/metadata.hpp>
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <complex>
#include <vector>
#include <cstring>

int main() {
    try {
        // 参数设置
        const double center_freq = 2.4e9;
        const double sample_rate = 15e6;
        const double gain = 40;
        const size_t num_samples = static_cast<size_t>(0.005 * sample_rate);
        const size_t buffer_size = 32768;
        const std::string file_name = "signal1.bin";

        // 创建 USRP
        uhd::device_addr_t dev_addr;
        auto usrp = uhd::usrp::multi_usrp::make(dev_addr);

        usrp->set_rx_rate(sample_rate);
        usrp->set_rx_freq(uhd::tune_request_t(center_freq));
        usrp->set_rx_gain(gain);

        usrp->set_clock_source("external", 0);
        usrp->set_time_source("external", 0);
        std::cout << "当前时钟源: " << usrp->get_clock_source(0) << std::endl;
        std::cout << "当前时间源: " << usrp->get_time_source(0) << std::endl;

        usrp->set_time_now(uhd::time_spec_t(0.0));
        std::this_thread::sleep_for(std::chrono::seconds(1));

        // 确保 GPSDO PPS 锁定
        double last_pps = usrp->get_time_last_pps().get_real_secs();

        // 等待 PPS 上升沿
        while (true) {
            double new_pps = usrp->get_time_last_pps().get_real_secs();
            if (new_pps > last_pps) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }

        // 设置下一个 PPS 触发时间
        usrp->set_time_next_pps(uhd::time_spec_t(9.0));

        last_pps = usrp->get_time_last_pps().get_real_secs();
        while (true) {
            double new_pps = usrp->get_time_last_pps().get_real_secs();
            if (new_pps > last_pps) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }

        // 配置数据流
        uhd::stream_args_t stream_args("fc32", "sc16");
        stream_args.args["recv_buff_size"] = "10000000";
        stream_args.args["recv_frame_size"] = "65536";
        stream_args.args["num_recv_frames"] = "512";

        auto rx_stream = usrp->get_rx_stream(stream_args);
        uhd::rx_metadata_t md;
        std::vector<std::complex<float>> recv_buffer(buffer_size);
        std::vector<std::complex<float>> received_samples(num_samples);

        std::this_thread::sleep_for(std::chrono::milliseconds(500));

        // 启动流
        uhd::stream_cmd_t stream_cmd(uhd::stream_cmd_t::STREAM_MODE_START_CONTINUOUS);
        stream_cmd.stream_now = true;
        rx_stream->issue_stream_cmd(stream_cmd);

        auto ts = usrp->get_time_now();
        uint64_t start_sec = ts.get_full_secs();
        uint64_t start_nsec = static_cast<uint64_t>(ts.get_frac_secs() * 1e9);
        std::cout << "开始接收，USRP 时间: " << start_sec << " 秒 " << start_nsec << " 纳秒" << std::endl;

        size_t write_index = 0;
        while (write_index < num_samples) {
            size_t num_rx = rx_stream->recv(&recv_buffer.front(), buffer_size, md, 1.0);

            if (md.error_code == uhd::rx_metadata_t::ERROR_CODE_OVERFLOW) {
                std::cerr << "警告: 溢出发生，继续接收..." << std::endl;
                continue;
            } else if (md.error_code != uhd::rx_metadata_t::ERROR_CODE_NONE) {
                std::cerr << "接收错误: " << md.strerror() << std::endl;
                break;
            }

            size_t to_copy = std::min(num_rx, num_samples - write_index);
            std::memcpy(&received_samples[write_index], &recv_buffer[0], to_copy * sizeof(std::complex<float>));
            write_index += to_copy;
        }

        // 停止流
        uhd::stream_cmd_t stop_cmd(uhd::stream_cmd_t::STREAM_MODE_STOP_CONTINUOUS);
        rx_stream->issue_stream_cmd(stop_cmd);

        auto ts_end = usrp->get_time_now();
        uint64_t end_sec = ts_end.get_full_secs();
        uint64_t end_nsec = static_cast<uint64_t>(ts_end.get_frac_secs() * 1e9);
        std::cout << "接收完成，USRP 时间: " << end_sec << " 秒 " << end_nsec << " 纳秒" << std::endl;

        // 写入文件
        std::ofstream outfile(file_name, std::ios::binary);
        outfile.write(reinterpret_cast<const char*>(received_samples.data()), received_samples.size() * sizeof(std::complex<float>));
        outfile.close();

        std::cout << "已保存信号到 " << file_name << "\n采集起始时间: " << start_sec << " 秒 " << start_nsec << " 纳秒" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "发生异常: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
