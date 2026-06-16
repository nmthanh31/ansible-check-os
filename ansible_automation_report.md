# Kế hoạch kiểm tra OS và Kubernetes bằng Ansible

Nguồn chuẩn: `list-job.md`.

## 1. Phạm vi

Môi trường hiện tại là 6 VM chạy cụm Kubernetes. Các job chỉ kiểm tra và tạo
báo cáo, không thay đổi cấu hình hệ thống.

```text
OS
  -> JOB-OS-01: Kiểm tra tài nguyên node
  -> JOB-OS-02: Kiểm tra event log OS
  -> JOB-OS-03: Kiểm tra cron job OS
  -> JOB-OS-04: Kiểm tra SMART

Kubernetes
  -> JOB-K8S-01: Kiểm tra tài nguyên
  -> JOB-K8S-02: Kiểm tra event toàn cụm
  -> JOB-K8S-03: Kiểm tra và tạo cảnh báo
```

## 2. Danh sách job và task

### `JOB-OS-01` - Kiểm tra tài nguyên node

- Kiểm tra vCPU và mức sử dụng CPU.
- Kiểm tra load average.
- Kiểm tra RAM khả dụng và đã sử dụng.
- Kiểm tra swap.
- Kiểm tra dung lượng filesystem.
- Kiểm tra inode.
- Phát hiện filesystem read-only.
- Liệt kê process sử dụng nhiều CPU/RAM.

### `JOB-OS-02` - Kiểm tra event log OS

- Thu thập kernel log trong 24 giờ.
- Kiểm tra systemd service failed.
- Phát hiện I/O và disk error.
- Phát hiện filesystem error/read-only.
- Phát hiện OOM Killer.
- Phát hiện network error/link down.
- Phát hiện segmentation fault.
- Kiểm tra lỗi containerd/kubelet.
- Kiểm tra authentication failure.
- Nhóm lỗi trùng theo nguồn và số lần xuất hiện.

### `JOB-OS-03` - Kiểm tra cron job OS

- Đọc `/etc/crontab`.
- Đọc `/etc/cron.d/`.
- Kiểm tra cron hourly/daily/weekly/monthly.
- Liệt kê user crontab.
- Liệt kê systemd timer.
- Ghi nhận user, lịch chạy, command và nguồn khai báo.

### `JOB-OS-04` - Kiểm tra SMART

- Phát hiện máy vật lý hay VM.
- Kiểm tra `smartctl` đã được cài đặt.
- Tìm thiết bị hỗ trợ SMART.
- VM không expose SMART thì `skipped`.
- Kiểm tra SMART overall health.
- Kiểm tra nhiệt độ ổ đĩa.
- Kiểm tra reallocated/pending/uncorrectable sector.
- Kiểm tra UDMA CRC error.
- Kiểm tra SSD wear level.
- Kiểm tra NVMe critical warning/media error.
- Đọc self-test log và error log.

Điều kiện quan trọng: nếu target là VM và không có disk/controller passthrough
hoặc hypervisor không expose SMART, job phải trả `skipped`; không được kết luận
ổ vật lý khỏe từ virtual disk.

### `JOB-K8S-01` - Kiểm tra tài nguyên

- Kiểm tra trạng thái và condition của node.
- Thu thập capacity và allocatable.
- Thu thập CPU/RAM usage.
- Kiểm tra Disk/Memory/PID Pressure.
- Đếm pod trên từng node.
- Tổng hợp request/limit theo node.
- So sánh request/limit với allocatable.
- Tổng hợp tài nguyên theo namespace/workload.
- Phát hiện container thiếu request/limit.
- Dùng Metrics API nếu có.
- Fallback sang SSH và `crictl stats` nếu không có Metrics Server.

### `JOB-K8S-02` - Kiểm tra event toàn cụm

- Thu thập event ở mọi namespace.
- Lọc Warning event.
- Phát hiện `FailedScheduling`.
- Phát hiện `BackOff`.
- Phát hiện `FailedMount`/`FailedAttachVolume`.
- Phát hiện `Unhealthy`/`Evicted`.
- Phát hiện `NodeNotReady`.
- Phát hiện lỗi pull image.
- Phát hiện lỗi tạo pod/container/sandbox.
- Nhóm event theo namespace, object và reason.

### `JOB-K8S-03` - Kiểm tra và tạo cảnh báo

- Cảnh báo node `NotReady` hoặc Pressure.
- Cảnh báo tài nguyên vượt ngưỡng.
- Cảnh báo request gần đạt allocatable.
- Cảnh báo limit overcommit.
- Cảnh báo pod lỗi hoặc Pending lâu.
- Cảnh báo workload thiếu replica.
- Cảnh báo Warning event lặp lại.
- Cảnh báo service không có endpoint.
- Cảnh báo PVC/volume lỗi.
- Cảnh báo lỗi OS hoặc SMART nghiêm trọng.
- Gộp thêm alert từ Prometheus/Alertmanager nếu có.
- Vẫn tự tạo cảnh báo khi không có monitoring stack.

## 3. Cấu trúc thư mục mới

```text
ansible-ops/
|-- playbooks/
|   |-- check_all.yml
|   |-- check_os.yml
|   `-- check_kubernetes.yml
|-- roles/
|   |-- os_checks/
|   |   |-- defaults/main.yml
|   |   `-- tasks/
|   |       |-- main.yml
|   |       |-- job_os_01_node_resources.yml
|   |       |-- job_os_02_event_logs.yml
|   |       |-- job_os_03_cron_jobs.yml
|   |       `-- job_os_04_smart.yml
|   |-- k8s_checks/
|   |   |-- defaults/main.yml
|   |   `-- tasks/
|   |       |-- main.yml
|   |       |-- job_k8s_01_resources.yml
|   |       |-- job_k8s_02_events.yml
|   |       `-- job_k8s_03_alerts.yml
|   `-- report/
|       `-- tasks/
|           |-- normalize_findings.yml
|           |-- build_report.yml
|           `-- notify.yml
```

Các role/playbook cũ chưa xóa ngay để tránh mất nội dung đang có; luồng triển
khai chính từ thời điểm này dùng `check_*.yml`, `os_checks` và `k8s_checks`.

## 4. Luồng chạy

```text
check_os.yml
  -> os_checks
     -> JOB-OS-01
     -> JOB-OS-02
     -> JOB-OS-03
     -> JOB-OS-04

check_kubernetes.yml
  -> k8s_checks
     -> JOB-K8S-01
     -> JOB-K8S-02
     -> JOB-K8S-03

check_all.yml
  -> check OS
  -> check Kubernetes
  -> report
```

## 5. Báo cáo kết quả

Mỗi job trả kết quả theo cấu trúc chung:

```json
{
  "job": "JOB-OS-02",
  "target": "Kubernetes-web01",
  "severity": "critical",
  "check": "os.kernel.io_error",
  "message": "I/O error detected in kernel log",
  "evidence": ["Buffer I/O error on device sda"],
  "detected_at": "2026-06-16T08:00:00+07:00"
}
```

Báo cáo tổng hợp cần có:

- Thời gian chạy.
- Danh sách node đã kiểm tra.
- Tổng số `critical`, `warning`, `info` và `skipped`.
- Kết quả chi tiết theo OS và Kubernetes.
- JSON để xử lý tự động.
- Markdown hoặc HTML để người vận hành đọc.

## 6. Nguyên tắc

- Các job chỉ kiểm tra, không thay đổi target.
- Dùng `changed_when: false`.
- Thiếu Metrics Server hoặc monitoring stack không được làm dừng job.
- Thiếu `smartctl` hoặc VM không expose SMART phải ghi `skipped`.
- Không lưu password trong inventory hoặc báo cáo.
- Kết quả phải có evidence để người vận hành xác minh.
