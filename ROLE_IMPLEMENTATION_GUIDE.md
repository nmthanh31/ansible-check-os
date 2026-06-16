# Hướng dẫn viết role kiểm tra OS và Kubernetes

Tài liệu này hướng dẫn triển khai các role trong cấu trúc mới:

```text
roles/
|-- os_checks/
|   `-- tasks/
|       |-- job_os_01_node_resources.yml
|       |-- job_os_02_event_logs.yml
|       |-- job_os_03_cron_jobs.yml
|       `-- job_os_04_smart.yml
|-- k8s_checks/
|   `-- tasks/
|       |-- job_k8s_01_resources.yml
|       |-- job_k8s_02_events.yml
|       `-- job_k8s_03_alerts.yml
`-- report/
```

Các job chỉ kiểm tra và thu thập dữ liệu, không thay đổi cấu hình hệ thống.

## 1. Quy ước chung

Mọi task kiểm tra phải có:

```yaml
changed_when: false
```

Với command có thể không tồn tại hoặc dữ liệu có thể rỗng, dùng:

```yaml
failed_when: false
```

Không dùng `ignore_errors: true` tràn lan. Nếu cần bỏ qua lỗi, phải lưu lại lý
do vào danh sách `skipped`.

Schema kết quả tối thiểu:

```yaml
job: JOB-OS-01
target: "{{ inventory_hostname }}"
severity: warning
check: os.cpu.usage
message: CPU usage exceeds warning threshold
evidence:
  - "cpu_usage=85"
detected_at: "{{ ansible_date_time.iso8601 }}"
```

Giải thích:

- `job`: mã job đang chạy.
- `target`: host, node, namespace hoặc object bị ảnh hưởng.
- `severity`: `critical`, `warning`, `info` hoặc `skipped`.
- `check`: mã kiểm tra ngắn, dùng để lọc và gom nhóm.
- `message`: nội dung dễ đọc cho người vận hành.
- `evidence`: bằng chứng cụ thể lấy từ command/API.
- `detected_at`: thời điểm phát hiện.

Mỗi role nên gom kết quả vào list chung:

```yaml
os_check_findings: []
k8s_check_findings: []
check_skipped: []
```

## 2. Role `os_checks`

Role `os_checks` chạy trên group `kubernetes_servers` qua playbook:

```text
playbooks/check_os.yml
```

File điều phối:

```yaml
# roles/os_checks/tasks/main.yml
---
- name: JOB-OS-01 - Kiểm tra tài nguyên node
  ansible.builtin.import_tasks: job_os_01_node_resources.yml
  tags:
    - job_os_01
    - os_resources

- name: JOB-OS-02 - Kiểm tra event log OS
  ansible.builtin.import_tasks: job_os_02_event_logs.yml
  tags:
    - job_os_02
    - os_event_logs

- name: JOB-OS-03 - Kiểm tra cron job OS
  ansible.builtin.import_tasks: job_os_03_cron_jobs.yml
  tags:
    - job_os_03
    - os_cron_jobs

- name: JOB-OS-04 - Kiểm tra SMART
  ansible.builtin.import_tasks: job_os_04_smart.yml
  tags:
    - job_os_04
    - os_smart
```

Giải thích:

- `import_tasks` chia nhỏ role thành từng job.
- `tags` cho phép chạy riêng từng job bằng `--tags job_os_01`.
- `main.yml` không chứa logic kiểm tra, chỉ điều phối.

### 2.1. `JOB-OS-01` - Kiểm tra tài nguyên node

Mục tiêu:

- CPU/vCPU.
- Load average.
- RAM và swap.
- Disk và inode.
- Filesystem read-only.
- Top process theo CPU/RAM.

Code mẫu:

```yaml
---
- name: JOB-OS-01 | Initialize result lists
  ansible.builtin.set_fact:
    os_node_resource_findings: []
    os_node_resource_raw: {}
  changed_when: false

- name: JOB-OS-01 | Read CPU count
  ansible.builtin.command: nproc
  register: os_cpu_count
  changed_when: false

- name: JOB-OS-01 | Read load average
  ansible.builtin.command: cat /proc/loadavg
  register: os_loadavg
  changed_when: false

- name: JOB-OS-01 | Read memory and swap
  ansible.builtin.command: free -m
  register: os_memory
  changed_when: false

- name: JOB-OS-01 | Read filesystem usage
  ansible.builtin.command: df -PTh
  register: os_filesystems
  changed_when: false

- name: JOB-OS-01 | Read inode usage
  ansible.builtin.command: df -Pi
  register: os_inodes
  changed_when: false

- name: JOB-OS-01 | Detect read-only filesystems
  ansible.builtin.shell: |
    findmnt -rn -o TARGET,OPTIONS | awk '$2 ~ /(^|,)ro(,|$)/ {print $0}'
  args:
    executable: /bin/bash
  register: os_readonly_filesystems
  changed_when: false
  failed_when: false

- name: JOB-OS-01 | Read top CPU processes
  ansible.builtin.shell: |
    ps -eo pid,user,comm,%cpu,%mem --sort=-%cpu | head -n {{ os_check_top_process_count + 1 }}
  args:
    executable: /bin/bash
  register: os_top_cpu_processes
  changed_when: false

- name: JOB-OS-01 | Read top memory processes
  ansible.builtin.shell: |
    ps -eo pid,user,comm,%cpu,%mem --sort=-%mem | head -n {{ os_check_top_process_count + 1 }}
  args:
    executable: /bin/bash
  register: os_top_memory_processes
  changed_when: false

- name: JOB-OS-01 | Save raw node resource result
  ansible.builtin.set_fact:
    os_node_resource_raw:
      cpu_count: "{{ os_cpu_count.stdout }}"
      loadavg: "{{ os_loadavg.stdout }}"
      memory: "{{ os_memory.stdout_lines }}"
      filesystems: "{{ os_filesystems.stdout_lines }}"
      inodes: "{{ os_inodes.stdout_lines }}"
      read_only_filesystems: "{{ os_readonly_filesystems.stdout_lines }}"
      top_cpu_processes: "{{ os_top_cpu_processes.stdout_lines }}"
      top_memory_processes: "{{ os_top_memory_processes.stdout_lines }}"
  changed_when: false
```

Giải thích code:

- `set_fact` đầu tiên khởi tạo biến để job luôn có output.
- `nproc` lấy số vCPU Linux nhìn thấy.
- `/proc/loadavg` trả load 1/5/15 phút.
- `free -m` lấy RAM/swap theo MB, dễ đọc khi debug.
- `df -PTh` dùng format POSIX để output ổn định hơn.
- `df -Pi` lấy inode.
- `findmnt` phát hiện mount có option `ro`.
- `ps --sort=-%cpu` và `ps --sort=-%mem` lấy process tiêu thụ tài nguyên cao.
- Giai đoạn đầu lưu raw để kiểm tra đúng dữ liệu trước; sau đó mới parse thành
  finding warning/critical.

### 2.2. `JOB-OS-02` - Kiểm tra event log OS

Mục tiêu:

- Kernel log 24 giờ.
- Systemd service failed.
- I/O error, disk error, filesystem error.
- OOM Killer.
- Network link down.
- Segmentation fault.
- Lỗi containerd/kubelet.
- Authentication failure.

Code mẫu:

```yaml
---
- name: JOB-OS-02 | Initialize event log result
  ansible.builtin.set_fact:
    os_event_log_raw: {}
    os_event_log_findings: []
  changed_when: false

- name: JOB-OS-02 | Read kernel errors
  ansible.builtin.command:
    cmd: journalctl -k --since "{{ os_check_log_since }}" --priority=warning..alert --no-pager
  register: os_kernel_errors
  changed_when: false
  failed_when: false

- name: JOB-OS-02 | Read failed systemd services
  ansible.builtin.command:
    cmd: systemctl --failed --no-pager --plain
  register: os_failed_services
  changed_when: false
  failed_when: false

- name: JOB-OS-02 | Read OS error patterns
  ansible.builtin.shell: |
    journalctl --since "{{ os_check_log_since }}" --no-pager \
      | grep -Ei 'I/O error|disk error|filesystem error|read-only file system|oom-killer|segfault|link is down|authentication failure|containerd|kubelet' \
      || true
  args:
    executable: /bin/bash
  register: os_error_patterns
  changed_when: false
  failed_when: false

- name: JOB-OS-02 | Save raw event log result
  ansible.builtin.set_fact:
    os_event_log_raw:
      kernel_errors: "{{ os_kernel_errors.stdout_lines }}"
      failed_services: "{{ os_failed_services.stdout_lines }}"
      error_patterns: "{{ os_error_patterns.stdout_lines }}"
  changed_when: false
```

Giải thích code:

- `journalctl -k` chỉ đọc kernel log.
- `--priority=warning..alert` giảm nhiễu, lấy warning trở lên.
- `systemctl --failed` tìm service fail.
- `grep -Ei ... || true` giúp không fail khi không có lỗi nào.
- Các pattern nên được đưa thành biến sau này để chỉnh dễ hơn.

### 2.3. `JOB-OS-03` - Kiểm tra cron job OS

Mục tiêu:

- Đọc cron hệ thống.
- Đọc cron theo thư mục.
- Đọc user crontab.
- Đọc systemd timer.

Code mẫu:

```yaml
---
- name: JOB-OS-03 | Read system crontab
  ansible.builtin.command:
    cmd: cat /etc/crontab
  register: os_system_crontab
  changed_when: false
  failed_when: false

- name: JOB-OS-03 | List cron.d files
  ansible.builtin.find:
    paths: /etc/cron.d
    file_type: file
  register: os_cron_d_files
  changed_when: false
  failed_when: false

- name: JOB-OS-03 | Read cron.d files
  ansible.builtin.command:
    cmd: cat {{ item.path }}
  loop: "{{ os_cron_d_files.files | default([]) }}"
  register: os_cron_d_content
  changed_when: false
  failed_when: false

- name: JOB-OS-03 | List periodic cron directories
  ansible.builtin.shell: |
    for d in /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly; do
      [ -d "$d" ] && find "$d" -maxdepth 1 -type f -printf '%p\n'
    done
  args:
    executable: /bin/bash
  register: os_periodic_cron_files
  changed_when: false
  failed_when: false

- name: JOB-OS-03 | Read systemd timers
  ansible.builtin.command:
    cmd: systemctl list-timers --all --no-pager --plain
  register: os_systemd_timers
  changed_when: false
  failed_when: false

- name: JOB-OS-03 | Save cron inventory
  ansible.builtin.set_fact:
    os_cron_jobs_raw:
      system_crontab: "{{ os_system_crontab.stdout_lines | default([]) }}"
      cron_d: "{{ os_cron_d_content.results | default([]) }}"
      periodic_files: "{{ os_periodic_cron_files.stdout_lines | default([]) }}"
      systemd_timers: "{{ os_systemd_timers.stdout_lines | default([]) }}"
  changed_when: false
```

Giải thích code:

- `find` của Ansible an toàn hơn tự parse `ls`.
- Đọc từng file `/etc/cron.d` bằng loop.
- `systemd timer` được đưa vào vì nhiều tác vụ định kỳ hiện không dùng cron.
- Job này chỉ kiểm kê, không chỉnh sửa cron.

### 2.4. `JOB-OS-04` - Kiểm tra SMART

Mục tiêu:

- Phát hiện máy vật lý hay VM.
- Kiểm tra `smartctl`.
- Tìm thiết bị hỗ trợ SMART.
- VM không expose SMART thì skipped.
- Đọc SMART health, nhiệt độ, bad sector, SSD/NVMe wear.

Code mẫu:

```yaml
---
- name: JOB-OS-04 | Detect virtualization type
  ansible.builtin.command:
    cmd: systemd-detect-virt
  register: os_virtualization_type
  changed_when: false
  failed_when: false

- name: JOB-OS-04 | Check smartctl availability
  ansible.builtin.command:
    cmd: command -v smartctl
  register: os_smartctl
  changed_when: false
  failed_when: false

- name: JOB-OS-04 | Scan SMART devices
  ansible.builtin.command:
    cmd: smartctl --scan-open
  register: os_smart_devices
  changed_when: false
  failed_when: false
  when: os_smartctl.rc == 0

- name: JOB-OS-04 | Mark SMART skipped when smartctl is missing
  ansible.builtin.set_fact:
    os_smart_skipped:
      job: JOB-OS-04
      target: "{{ inventory_hostname }}"
      severity: skipped
      check: os.smart.available
      message: smartctl is not installed
      evidence: []
  changed_when: false
  when: os_smartctl.rc != 0

- name: JOB-OS-04 | Mark SMART skipped when VM does not expose SMART
  ansible.builtin.set_fact:
    os_smart_skipped:
      job: JOB-OS-04
      target: "{{ inventory_hostname }}"
      severity: skipped
      check: os.smart.vm_not_exposed
      message: SMART data is not exposed to the VM
      evidence:
        - "virtualization={{ os_virtualization_type.stdout | default('unknown') }}"
  changed_when: false
  when:
    - os_smartctl.rc == 0
    - os_virtualization_type.rc == 0
    - os_virtualization_type.stdout != "none"
    - (os_smart_devices.stdout_lines | default([])) | length == 0

- name: JOB-OS-04 | Read SMART data
  ansible.builtin.command:
    cmd: smartctl -x {{ item.split()[0] }}
  loop: "{{ os_smart_devices.stdout_lines | default([]) }}"
  register: os_smart_data
  changed_when: false
  failed_when: false
  when:
    - os_smartctl.rc == 0
    - (os_virtualization_type.stdout | default('none')) == "none" or
      ((os_smart_devices.stdout_lines | default([])) | length > 0)
```

Giải thích code:

- `systemd-detect-virt` trả `none` nếu là máy vật lý; trả tên hypervisor nếu là
  VM.
- `command -v smartctl` kiểm tra tool, không tự cài.
- `smartctl --scan-open` tìm thiết bị đọc được SMART.
- VM không expose SMART thì job `skipped`, không kết luận ổ vật lý khỏe.
- `smartctl -x` đọc dữ liệu chi tiết; chỉ đọc, không chạy self-test.

## 3. Role `k8s_checks`

Role `k8s_checks` chạy từ một node có quyền gọi Kubernetes API hoặc có
`kubectl`.

File điều phối:

```yaml
# roles/k8s_checks/tasks/main.yml
---
- name: JOB-K8S-01 - Kiểm tra tài nguyên
  ansible.builtin.import_tasks: job_k8s_01_resources.yml
  tags:
    - job_k8s_01
    - k8s_resources

- name: JOB-K8S-02 - Kiểm tra event toàn cụm
  ansible.builtin.import_tasks: job_k8s_02_events.yml
  tags:
    - job_k8s_02
    - k8s_events

- name: JOB-K8S-03 - Kiểm tra và tạo cảnh báo
  ansible.builtin.import_tasks: job_k8s_03_alerts.yml
  tags:
    - job_k8s_03
    - k8s_alerts
```

### 3.1. `JOB-K8S-01` - Kiểm tra tài nguyên

Mục tiêu:

- Node condition.
- Capacity và allocatable.
- CPU/RAM usage.
- Pod count.
- Request/limit theo node, namespace, workload.
- Container thiếu request/limit.
- Fallback khi không có Metrics Server.

Code mẫu:

```yaml
---
- name: JOB-K8S-01 | Read Kubernetes nodes
  ansible.builtin.command:
    cmd: kubectl get nodes -o json
  register: k8s_nodes_json
  changed_when: false

- name: JOB-K8S-01 | Read pods
  ansible.builtin.command:
    cmd: kubectl get pods -A -o json
  register: k8s_pods_json
  changed_when: false

- name: JOB-K8S-01 | Try Metrics API for node usage
  ansible.builtin.command:
    cmd: kubectl top nodes --no-headers
  register: k8s_top_nodes
  changed_when: false
  failed_when: false

- name: JOB-K8S-01 | Try Metrics API for pod usage
  ansible.builtin.command:
    cmd: kubectl top pods -A --no-headers
  register: k8s_top_pods
  changed_when: false
  failed_when: false

- name: JOB-K8S-01 | Save Kubernetes resource raw data
  ansible.builtin.set_fact:
    k8s_resource_raw:
      nodes: "{{ k8s_nodes_json.stdout | from_json }}"
      pods: "{{ k8s_pods_json.stdout | from_json }}"
      top_nodes_available: "{{ k8s_top_nodes.rc == 0 }}"
      top_nodes: "{{ k8s_top_nodes.stdout_lines | default([]) }}"
      top_pods_available: "{{ k8s_top_pods.rc == 0 }}"
      top_pods: "{{ k8s_top_pods.stdout_lines | default([]) }}"
  changed_when: false
```

Giải thích code:

- `kubectl get ... -o json` giúp parse bằng `from_json`, ổn định hơn parse text.
- `kubectl top` có thể fail nếu không có Metrics Server, nên `failed_when:
  false`.
- Nếu Metrics API thiếu, vẫn còn node capacity/allocatable và pod request/limit
  từ Kubernetes API.
- Fallback `crictl stats` nên triển khai bằng task chạy trên từng node OS, sau
  đó ghép với pod/container ID.

### 3.2. `JOB-K8S-02` - Kiểm tra event toàn cụm

Mục tiêu:

- Thu thập event mọi namespace.
- Lọc Warning event.
- Nhóm theo namespace, object và reason.

Code mẫu:

```yaml
---
- name: JOB-K8S-02 | Read cluster events
  ansible.builtin.command:
    cmd: kubectl get events -A -o json
  register: k8s_events_json
  changed_when: false
  failed_when: false

- name: JOB-K8S-02 | Save raw events
  ansible.builtin.set_fact:
    k8s_events_raw: "{{ (k8s_events_json.stdout | default('{\"items\":[]}')) | from_json }}"
  changed_when: false

- name: JOB-K8S-02 | Extract warning events
  ansible.builtin.set_fact:
    k8s_warning_events: >-
      {{
        k8s_events_raw.items
        | selectattr('type', 'equalto', 'Warning')
        | list
      }}
  changed_when: false
```

Giải thích code:

- Kubernetes Event có thời gian lưu ngắn, nên job chỉ phản ánh hiện trạng tại
  lúc chạy.
- `-A` lấy tất cả namespace.
- Lọc `type == Warning` để tập trung lỗi.
- Sau bước này có thể nhóm theo `involvedObject`, `reason`, `message`.

### 3.3. `JOB-K8S-03` - Kiểm tra và tạo cảnh báo

Mục tiêu:

- Tạo cảnh báo từ dữ liệu OS/K8S đã thu thập.
- Không phụ thuộc Prometheus/Alertmanager.
- Nếu có monitoring stack thì gộp thêm alert.

Code mẫu:

```yaml
---
- name: JOB-K8S-03 | Initialize alert list
  ansible.builtin.set_fact:
    k8s_generated_alerts: []
  changed_when: false

- name: JOB-K8S-03 | Create alerts from warning events
  ansible.builtin.set_fact:
    k8s_generated_alerts: >-
      {{
        k8s_generated_alerts
        + [
          {
            'job': 'JOB-K8S-03',
            'target': item.metadata.namespace ~ '/' ~ item.involvedObject.name,
            'severity': 'warning',
            'check': 'k8s.event.warning',
            'message': item.reason ~ ': ' ~ item.message,
            'evidence': [item.reason, item.message]
          }
        ]
      }}
  loop: "{{ k8s_warning_events | default([]) }}"
  changed_when: false

- name: JOB-K8S-03 | Try Alertmanager API
  ansible.builtin.uri:
    url: "{{ k8s_alertmanager_url }}/api/v2/alerts"
    method: GET
    return_content: true
  register: k8s_alertmanager_alerts
  changed_when: false
  failed_when: false
  when: k8s_alertmanager_url is defined
```

Giải thích code:

- `k8s_generated_alerts` là alert tự tạo từ kết quả kiểm tra.
- Job không cần Prometheus/Alertmanager để hoạt động.
- `uri` chỉ chạy nếu có `k8s_alertmanager_url`.
- Nếu Alertmanager không có hoặc API lỗi, cảnh báo nội bộ vẫn được tạo.

## 4. Role `report`

Role `report` gom kết quả từ `os_checks` và `k8s_checks`.

Các task nên có:

```text
normalize_findings.yml
build_report.yml
notify.yml
```

Luồng đề xuất:

```yaml
---
- name: Normalize findings
  ansible.builtin.import_tasks: normalize_findings.yml

- name: Build report
  ansible.builtin.import_tasks: build_report.yml

- name: Notify
  ansible.builtin.import_tasks: notify.yml
```

Giải thích:

- `normalize_findings.yml`: đưa raw data/finding về schema chung.
- `build_report.yml`: xuất JSON và Markdown/HTML.
- `notify.yml`: gửi email/Mattermost nếu cấu hình.

## 5. Cách chạy khi phát triển

Chạy riêng từng job OS:

```bash
ansible-playbook playbooks/check_os.yml --tags job_os_01
ansible-playbook playbooks/check_os.yml --tags job_os_02
ansible-playbook playbooks/check_os.yml --tags job_os_03
ansible-playbook playbooks/check_os.yml --tags job_os_04
```

Chạy riêng từng job Kubernetes:

```bash
ansible-playbook playbooks/check_kubernetes.yml --tags job_k8s_01
ansible-playbook playbooks/check_kubernetes.yml --tags job_k8s_02
ansible-playbook playbooks/check_kubernetes.yml --tags job_k8s_03
```

Chạy toàn bộ:

```bash
ansible-playbook playbooks/check_all.yml
```

Syntax check:

```bash
ansible-playbook playbooks/check_all.yml --syntax-check
```

## 6. Thứ tự triển khai khuyến nghị

1. Viết `JOB-OS-01` và in raw output.
2. Parse `JOB-OS-01` thành finding warning/critical.
3. Viết `JOB-OS-02`.
4. Viết `JOB-K8S-01`.
5. Viết `JOB-K8S-02`.
6. Viết `JOB-K8S-03` dựa trên dữ liệu từ các job trước.
7. Viết `JOB-OS-03` và `JOB-OS-04`.
8. Hoàn thiện role `report`.
