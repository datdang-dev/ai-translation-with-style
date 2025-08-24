# Translation Job Monitor GUI

Một giao diện đồ họa (GUI) để monitoring và quản lý các job translation theo batch với real-time logging.

## Tính năng chính

### 🖥️ Giao diện chính
- **Job List View**: Hiển thị danh sách tất cả translation jobs với trạng thái real-time
- **Control Panel**: Cấu hình và điều khiển batch translation
- **Status Bar**: Hiển thị trạng thái hiện tại của hệ thống

### 📊 Monitoring Real-time
- **Live Status Updates**: Cập nhật trạng thái job theo thời gian thực
- **Progress Tracking**: Theo dõi tiến độ từng job với phần trăm hoàn thành
- **Individual Log Windows**: Mỗi job có cửa sổ log riêng để theo dõi chi tiết

### 🔧 Quản lý Job
- **Start/Stop Controls**: Bắt đầu và dừng batch translation
- **Job Cancellation**: Hủy các job đang chạy hoặc đang chờ
- **Clear Completed**: Xóa các job đã hoàn thành khỏi danh sách
- **Export Logs**: Xuất log của job ra file text

### 💾 Configuration Management
- **Save/Load Settings**: Lưu và tải cấu hình
- **File Browser**: Chọn file config, thư mục input/output
- **Parameter Tuning**: Điều chỉnh max concurrent jobs, delay giữa các job

## Cấu trúc Files

```
/workspace/
├── translation_monitor_gui.py      # Main GUI application
├── gui_batch_orchestrator.py       # Enhanced orchestrator with GUI support
├── demo_gui.py                     # Demo script
├── requirements.txt                # Dependencies
└── demo_data/                      # Demo files (tự động tạo)
    ├── input/                      # Sample input files
    ├── output/                     # Translation output
    └── config/                     # Demo configuration
```

## Cài đặt và Chạy

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy Demo
```bash
python demo_gui.py
```

### 3. Chạy trực tiếp GUI
```bash
python translation_monitor_gui.py
```

## Hướng dẫn sử dụng

### 🚀 Bắt đầu

1. **Mở ứng dụng**: Chạy `python demo_gui.py` hoặc `python translation_monitor_gui.py`

2. **Cấu hình**: 
   - **Config File**: Chọn file cấu hình preset translation
   - **Input Dir**: Thư mục chứa các file cần dịch
   - **Output Dir**: Thư mục lưu kết quả
   - **File Pattern**: Pattern để tìm file (mặc định: `chunk_*.json`)

3. **Thiết lập tham số**:
   - **Max Concurrent**: Số job chạy đồng thời (mặc định: 3)
   - **Job Delay**: Thời gian delay giữa các job (giây)

4. **Bắt đầu**: Click **"Start Batch Translation"**

### 📋 Theo dõi Jobs

#### Job List Columns:
- **Job ID**: Mã định danh unique của job
- **Status**: Trạng thái hiện tại (Pending, Processing, Completed, Failed, Cancelled)
- **Input File**: File đầu vào
- **Output File**: File đầu ra
- **Start Time**: Thời gian bắt đầu
- **Duration**: Thời gian thực hiện
- **Progress**: Tiến độ và bước hiện tại

#### Status Icons:
- ⏳ **Pending**: Đang chờ xử lý
- 🔄 **Processing**: Đang xử lý
- ✅ **Completed**: Hoàn thành thành công
- ❌ **Failed**: Thất bại
- 🚫 **Cancelled**: Đã hủy

### 🖱️ Thao tác với Jobs

#### Double-click trên job:
- Mở cửa sổ log real-time cho job đó

#### Right-click (Context Menu):
- **Open Log Window**: Mở cửa sổ log
- **View Details**: Xem thông tin chi tiết
- **Export Logs**: Xuất log ra file
- **Cancel Job**: Hủy job (chỉ với pending/processing jobs)

### 📊 Log Windows

Mỗi job có thể có cửa sổ log riêng với:
- **Real-time logs**: Hiển thị log theo thời gian thực
- **Status display**: Trạng thái và bước hiện tại
- **Terminal-style**: Giao diện giống terminal (đen/xanh)
- **Auto-scroll**: Tự động scroll xuống log mới

### 🛠️ Menu Functions

#### File Menu:
- **Load Configuration**: Tải cấu hình từ file
- **Save Configuration**: Lưu cấu hình hiện tại
- **Exit**: Thoát ứng dụng

#### View Menu:
- **Refresh Jobs**: Làm mới danh sách job
- **Open All Log Windows**: Mở tất cả cửa sổ log
- **Close All Log Windows**: Đóng tất cả cửa sổ log

#### Help Menu:
- **About**: Thông tin về ứng dụng

## Kiến trúc hệ thống

### Main Components:

1. **TranslationMonitorGUI**: 
   - Giao diện chính
   - Quản lý job list view
   - Xử lý user interactions

2. **GUIBatchOrchestrator**:
   - Enhanced orchestrator với GUI callbacks
   - Real-time status updates
   - Thread-safe logging

3. **JobMonitorWindow**:
   - Individual log windows cho mỗi job
   - Real-time log streaming
   - Status display

4. **GUIJobStatus**:
   - Extended job status với GUI-specific data
   - Progress tracking
   - Log message storage

### Threading Model:
- **Main GUI Thread**: Xử lý UI updates
- **Monitoring Thread**: Background monitoring và callbacks
- **Translation Threads**: Async translation execution
- **Thread-safe Communication**: Sử dụng queues và callbacks

## Demo và Testing

### Demo Script (`demo_gui.py`):
- Tự động tạo sample files
- Pre-configure settings
- Hướng dẫn sử dụng chi tiết

### Sample Files:
- 5 chunk files với sample text
- Demo configuration
- Structured directory layout

## Troubleshooting

### Common Issues:

1. **GUI không hiển thị**:
   - Kiểm tra tkinter có được cài đặt
   - Thử chạy `python -m tkinter` để test

2. **Import errors**:
   - Đảm bảo tất cả dependencies đã cài đặt
   - Kiểm tra Python path

3. **Jobs không chạy**:
   - Kiểm tra config file tồn tại
   - Xác nhận input directory có files matching pattern
   - Kiểm tra log windows để xem error details

4. **Real-time updates không hoạt động**:
   - Restart ứng dụng
   - Kiểm tra threading errors trong terminal

### Debug Mode:
Để debug, chạy từ terminal để xem console output:
```bash
python translation_monitor_gui.py
```

## Performance Notes

- **Concurrent Jobs**: Số lượng job đồng thời ảnh hưởng đến hiệu suất
- **Log Windows**: Nhiều log window mở có thể làm chậm GUI
- **Large Files**: Files lớn có thể cần timeout longer
- **Memory Usage**: Monitor memory khi chạy nhiều job

## Future Enhancements

Có thể mở rộng:
- **Dark Mode**: Theme tối cho GUI
- **Job Templates**: Lưu template cho different job types
- **Statistics Dashboard**: Charts và metrics
- **Remote Monitoring**: Monitor jobs từ xa
- **Job Scheduling**: Schedule jobs để chạy sau
- **Notification System**: Alerts khi job complete/fail

## License

Tham khảo LICENSE file trong project root.

---

**Developed by**: Translation Team  
**Version**: 1.0  
**Last Updated**: 2024