# Hướng dẫn triển khai Role kiểm tra OS và Kubernetes

Tài liệu này giải thích chi tiết **toàn bộ file, task và câu lệnh** trong từng role.
Mọi đoạn code đều lấy từ source thực tế, không phải code mẫu giả định.

---

## Mục lục

1. [Tổng quan cấu trúc dự án](#1-tổng-quan-cấu-trúc-dự-án)
2. [Cấu hình Ansible (`ansible.cfg`)](#2-cấu-hình-ansible-ansiblecfg)
3. [Inventory (`inventories/lab/`)](#3-inventory-inventorieslab)
4. [Playbook điều phối (`playbooks/`)](#4-playbook-điều-phối-playbooks)
5. [Role `os_checks`](#5-role-os_checks)
   - 5.1 [Biến mặc định (`defaults/main.yml`)](#51-biến-mặc-định-defaultsmainyml)
   - 5.2 [File điều phối (`tasks/main.yml`)](#52-file-điều-phối-tasksmainyml)
   - 5.3 [JOB-OS-01 – Kiểm tra tài nguyên node](#53-job-os-01--kiểm-tra-tài-nguyên-node)
   - 5.4 [JOB-OS-02 – Kiểm tra event log OS](#54-job-os-02--kiểm-tra-event-log-os)
   - 5.5 [JOB-OS-03 – Kiểm tra cron job OS](#55-job-os-03--kiểm-tra-cron-job-os)
   - 5.6 [JOB-OS-04 – Kiểm tra SMART ổ đĩa](#56-job-os-04--kiểm-tra-smart-ổ-đĩa)
   - 5.7 [Save report (`tasks/save_report.yml`)](#57-save-report-taskssave_reportyml)
6. [Role `k8s_checks`](#6-role-k8s_checks)
   - 6.1 [Biến mặc định (`defaults/main.yml`)](#61-biến-mặc-định-defaultsmainyml)
   - 6.2 [File điều phối (`tasks/main.yml`)](#62-file-điều-phối-tasksmainyml)
   - 6.3 [JOB-K8S-01 – Kiểm tra tài nguyên](#63-job-k8s-01--kiểm-tra-tài-nguyên)
   - 6.4 [JOB-K8S-02 – Kiểm tra event toàn cụm](#64-job-k8s-02--kiểm-tra-event-toàn-cụm)
   - 6.5 [JOB-K8S-03 – Kiểm tra và tạo cảnh báo](#65-job-k8s-03--kiểm-tra-và-tạo-cảnh-báo)
   - 6.6 [Save report (`tasks/save_report.yml`)](#66-save-report-taskssave_reportyml)
7. [Quy ước chung và schema kết quả](#7-quy-ước-chung-và-schema-kết-quả)
8. [Cách chạy](#8-cách-chạy)
9. [Thứ tự triển khai khuyến nghị](#9-thứ-tự-triển-khai-khuyến-nghị)

---

## 1. Tổng quan cấu trúc dự án

```text
ansible-ops/
├── ansible.cfg                            # Cấu hình Ansible toàn cục
├── inventories/
│   └── lab/
│       ├── inventory.ini                  # Danh sách host và group
│       └── group_vars/
│           └── kubernetes_servers/
│               ├── all.yml                # Biến không bí mật cho group
│               ├── vault.yml              # Biến mật khẩu (mã hóa ansible-vault)
│               └── vault.yml.example      # File mẫu để copy
├── playbooks/
│   ├── check_os.yml                       # Chạy role os_checks
│   ├── check_kubernetes.yml               # Chạy role k8s_checks
│   └── check_all.yml                      # Import cả hai playbook trên
└── roles/
    ├── os_checks/
    │   ├── defaults/
    │   │   └── main.yml                   # Ngưỡng cảnh báo, thời gian log, v.v.
    │   └── tasks/
    │       ├── main.yml                   # Điều phối import các job
    │       ├── job_os_01_node_resources.yml
    │       ├── job_os_02_event_logs.yml
    │       ├── job_os_03_cron_jobs.yml
    │       ├── job_os_04_smart.yml
    │       └── save_report.yml            # Ghi JSON báo cáo về control node
    └── k8s_checks/
        ├── defaults/
        │   └── main.yml                   # Đường dẫn kubectl/crictl, ngưỡng, v.v.
        └── tasks/
            ├── main.yml
            ├── job_k8s_01_resources.yml
            ├── job_k8s_02_events.yml
            ├── job_k8s_03_alerts.yml
            └── save_report.yml
```

**Nguyên tắc thiết kế:**

- Mọi task **chỉ đọc dữ liệu**, không thay đổi cấu hình hệ thống.
- Mỗi job gom raw data trước, rồi mới phân tích thành `findings`/`metrics`.
- `save_report.yml` chạy sau cùng, luôn được gắn tag `always`.

---

## 2. Cấu hình Ansible (`ansible.cfg`)

**File:** `ansible-ops/ansible.cfg`

```ini
[defaults]
inventory = inventories/lab/inventory.ini
host_key_checking = True
interpreter_python = auto_silent
roles_path = roles
timeout = 30

[privilege_escalation]
become = True
become_method = sudo
```

**Giải thích từng dòng:**

| Dòng | Ý nghĩa |
|------|---------|
| `inventory = inventories/lab/inventory.ini` | Inventory mặc định khi chạy `ansible-playbook` mà không chỉ `-i`. |
| `host_key_checking = True` | Kiểm tra SSH host key. Giữ `True` để tránh man-in-the-middle. |
| `interpreter_python = auto_silent` | Ansible tự chọn Python trên host mà không in cảnh báo. |
| `roles_path = roles` | Thư mục tìm role, tính từ `ansible.cfg`. |
| `timeout = 30` | Timeout kết nối SSH (giây). |
| `become = True` | Tự động leo quyền (`sudo`) cho mọi task trừ khi task có `become: false`. |
| `become_method = sudo` | Dùng `sudo` thay vì `su`, `pbrun`, v.v. |

---

## 3. Inventory (`inventories/lab/`)

### `inventories/lab/inventory.ini`

```ini
[kubernetes_control_plane]
cp01 ansible_host=172.23.0.47
cp02 ansible_host=172.23.0.49
cp03 ansible_host=172.23.0.24

[kubernetes_workers]
wk01 ansible_host=172.23.0.46
wk02 ansible_host=172.23.0.48
wk03 ansible_host=172.23.0.28

[kubernetes_servers:children]
kubernetes_control_plane
kubernetes_workers

[kubernetes_servers:vars]
ansible_user=setup
ansible_python_interpreter=auto_silent
ansible_become_method=sudo
```

**Giải thích:**

- `[kubernetes_control_plane]`: Group chứa các node master của RKE2. Mỗi dòng là `alias ansible_host=IP`.
- `[kubernetes_workers]`: Group chứa worker node.
- `[kubernetes_servers:children]`: Group tổng hợp từ hai group trên. Playbook `check_os.yml` chạy trên group này (tất cả 6 node).
- `[kubernetes_servers:vars]`: Biến áp dụng cho toàn bộ group.
  - `ansible_user=setup` – SSH vào node bằng user `setup`.
  - `ansible_become_method=sudo` – Leo quyền bằng `sudo`.

### `group_vars/kubernetes_servers/all.yml`

```yaml
---
ansible_password: "{{ vault_ansible_password }}"
ansible_become_pass: "{{ vault_ansible_become_pass }}"
```

**Giải thích:** File này không chứa password thật. Nó tham chiếu đến biến `vault_*` được lưu trong `vault.yml` đã mã hóa bằng `ansible-vault`. Kỹ thuật này giúp commit `all.yml` lên git mà không lộ bí mật.

### `group_vars/kubernetes_servers/vault.yml.example`

```yaml
---
vault_ansible_password: "change-me"
vault_ansible_become_pass: "change-me"
```

**Giải thích:** File mẫu để tham khảo. Khi triển khai thật, copy thành `vault.yml` rồi chạy:

```bash
# Mã hóa vault.yml bằng ansible-vault
ansible-vault encrypt inventories/lab/group_vars/kubernetes_servers/vault.yml

# Chạy playbook với vault password
ansible-playbook playbooks/check_os.yml --ask-vault-pass
# hoặc dùng vault password file
ansible-playbook playbooks/check_os.yml --vault-password-file ~/.vault_pass
```

---

## 4. Playbook điều phối (`playbooks/`)

### `playbooks/check_os.yml`

```yaml
---
- name: Check OS jobs
  hosts: kubernetes_servers
  become: true
  gather_facts: false

  roles:
    - role: os_checks
      tags:
        - os
        - checks
```

**Giải thích từng dòng:**

| Trường | Ý nghĩa |
|--------|---------|
| `hosts: kubernetes_servers` | Chạy trên tất cả node (cả control-plane lẫn worker). |
| `become: true` | Leo quyền root để đọc journal, SMART, crontab hệ thống. |
| `gather_facts: false` | Tắt fact gathering vì role không cần `ansible_*` facts, tiết kiệm ~1–2s mỗi host. |
| `role: os_checks` | Gọi role tại `roles/os_checks/`. |
| `tags: [os, checks]` | Tag cấp playbook, cho phép lọc nhanh với `--tags os`. |

### `playbooks/check_kubernetes.yml`

```yaml
---
- name: Check Kubernetes jobs
  hosts: kubernetes_control_plane[0]
  become: true
  gather_facts: false

  roles:
    - role: k8s_checks
      tags:
        - kubernetes
        - checks
```

**Giải thích:**

- `hosts: kubernetes_control_plane[0]` – Chỉ chạy trên node **control-plane đầu tiên** (`cp01`). Lý do: `kubectl` và `kubeconfig` chỉ cần một điểm truy cập vào API server. Task nào cần chạy trên từng node sẽ dùng `delegate_to` bên trong role.

### `playbooks/check_all.yml`

```yaml
---
- import_playbook: check_os.yml

- import_playbook: check_kubernetes.yml
```

**Giải thích:** `import_playbook` khác `include_playbook` ở chỗ nó được xử lý tĩnh khi parse, không phải runtime. Thứ tự thực thi: OS checks trước → K8s checks sau.

---

## 5. Role `os_checks`

Role này chạy trên **mọi node** trong group `kubernetes_servers`. Mỗi node được kiểm tra độc lập.

---

### 5.1 Biến mặc định (`defaults/main.yml`)

```yaml
---
os_check_log_since: "24 hours ago"
os_check_top_process_count: 10
os_check_cpu_warning_percent: 80
os_check_cpu_critical_percent: 90
os_check_memory_warning_percent: 80
os_check_memory_critical_percent: 90
os_check_swap_warning_percent: 20
os_check_swap_critical_percent: 50
os_check_disk_warning_percent: 80
os_check_disk_critical_percent: 90
os_check_inode_warning_percent: 80
os_check_inode_critical_percent: 90
os_check_artifact_dir: "{{ playbook_dir }}/../artifacts"
os_check_include_raw: false
```

**Giải thích từng biến:**

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `os_check_log_since` | `"24 hours ago"` | Khoảng thời gian đọc journal. Format được journalctl chấp nhận. |
| `os_check_top_process_count` | `10` | Số process top CPU/RAM được ghi vào raw data. |
| `os_check_cpu_warning_percent` | `80` | Load average / vCPU vượt ngưỡng này → `warning`. |
| `os_check_cpu_critical_percent` | `90` | Load average / vCPU vượt ngưỡng này → `critical`. |
| `os_check_memory_warning_percent` | `80` | RAM used% vượt ngưỡng → `warning`. |
| `os_check_memory_critical_percent` | `90` | RAM used% vượt ngưỡng → `critical`. |
| `os_check_swap_warning_percent` | `20` | Swap used% vượt ngưỡng → `warning`. Ngưỡng thấp vì swap trên K8s node là dấu hiệu xấu. |
| `os_check_swap_critical_percent` | `50` | Swap used% vượt ngưỡng → `critical`. |
| `os_check_disk_warning_percent` | `80` | Disk used% vượt ngưỡng → `warning`. |
| `os_check_disk_critical_percent` | `90` | Disk used% vượt ngưỡng → `critical`. |
| `os_check_inode_warning_percent` | `80` | Inode used% vượt ngưỡng → `warning`. |
| `os_check_inode_critical_percent` | `90` | Inode used% vượt ngưỡng → `critical`. |
| `os_check_artifact_dir` | `{{ playbook_dir }}/../artifacts` | Thư mục ghi báo cáo JSON. `playbook_dir` là đường dẫn tới `playbooks/`, `..` lên một cấp thành `ansible-ops/`. |
| `os_check_include_raw` | `false` | Khi `true`, báo cáo JSON kèm toàn bộ raw output (dùng debug). Bật bằng `-e os_check_include_raw=true`. |

---

### 5.2 File điều phối (`tasks/main.yml`)

```yaml
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

- name: Save OS check report
  ansible.builtin.import_tasks: save_report.yml
  tags:
    - always
    - os_report
```

**Giải thích:**

- `import_tasks` xử lý **tĩnh** (static import): các task được nhúng vào playbook lúc parse. Điều này cho phép gắn `tags` từ bên ngoài vào từng file, không dùng `include_tasks` vì `include_tasks` xử lý động và không kế thừa tag tốt.
- `tags: always` trên `save_report.yml` đảm bảo task ghi báo cáo **luôn chạy**, kể cả khi người dùng chạy `--tags job_os_01`. Điều này tránh tình trạng chạy kiểm tra nhưng không có báo cáo.

---

### 5.3 JOB-OS-01 – Kiểm tra tài nguyên node

**File:** `tasks/job_os_01_node_resources.yml`

**Mục tiêu thu thập:**
- Số vCPU và load average
- RAM và swap
- Dung lượng và inode filesystem
- Filesystem đang mount read-only
- Top process theo CPU và theo RAM

---

#### Task 1: Khởi tạo biến

```yaml
- name: JOB-OS-01 | Initialize result lists
  ansible.builtin.set_fact:
    os_node_resource_findings: []
    os_node_resource_raw: {}
  changed_when: false
```

**Giải thích:**

- `set_fact` gán biến vào host variable scope cho phần còn lại của play.
- `os_node_resource_findings: []` – List rỗng sẽ chứa các finding `warning`/`critical` sau khi parse.
- `os_node_resource_raw: {}` – Dict rỗng sẽ chứa output thô của từng lệnh.
- `changed_when: false` – Báo Ansible task này không thay đổi hệ thống. Nếu không có dòng này, `set_fact` sẽ bị tính là "changed" và làm cho play report sai.

---

#### Task 2: Đọc số vCPU

```yaml
- name: JOB-OS-01 | Read CPU count
  ansible.builtin.command: nproc
  register: os_cpu_count
  changed_when: false
```

**Lệnh: `nproc`**

- In ra số **CPU logical** (vCPU) mà Linux đang nhìn thấy.
- Trên VM, con số này là số vCPU được hypervisor cấp cho guest OS.
- Khác `nproc --all` ở chỗ `nproc` trả số CPU **khả dụng** (có thể bị giới hạn bởi cgroup).
- Kết quả ví dụ: `8`

**`ansible.builtin.command` vs `ansible.builtin.shell`:**

| Module | Khi dùng |
|--------|---------|
| `command` | Chạy lệnh đơn giản, không cần pipe `\|`, wildcard `*`, redirect `>`, biến `$VAR` |
| `shell` | Khi cần pipe, wildcard, vòng lặp, toán tử `&&`, `\|\|`, hoặc redirect |

`nproc` không cần shell nên dùng `command`.

**`register: os_cpu_count`**

`register` lưu kết quả thực thi vào biến `os_cpu_count`. Biến này là dict gồm:

| Key | Nội dung |
|-----|---------|
| `os_cpu_count.stdout` | Output chuẩn dạng string (ví dụ: `"8"`) |
| `os_cpu_count.stdout_lines` | List các dòng output (ví dụ: `["8"]`) |
| `os_cpu_count.stderr` | Standard error |
| `os_cpu_count.rc` | Return code (0 = thành công) |

---

#### Task 3: Đọc load average

```yaml
- name: JOB-OS-01 | Read load average
  ansible.builtin.command: cat /proc/loadavg
  register: os_loadavg
  changed_when: false
```

**Lệnh: `cat /proc/loadavg`**

- `/proc/loadavg` là pseudo-file của kernel Linux, không phải file trên disk.
- Output ví dụ: `0.52 0.61 0.59 2/1234 56789`

| Cột | Ý nghĩa |
|-----|---------|
| Cột 1 (`0.52`) | Load average **1 phút** qua |
| Cột 2 (`0.61`) | Load average **5 phút** qua |
| Cột 3 (`0.59`) | Load average **15 phút** qua |
| Cột 4 (`2/1234`) | Số process đang chạy / tổng số process |
| Cột 5 (`56789`) | PID của process mới nhất |

**Cách đọc:** So sánh load 1 phút với số vCPU. Nếu load > số vCPU thì hàng đợi CPU đang tắc nghẽn.

---

#### Task 4: Đọc RAM và swap

```yaml
- name: JOB-OS-01 | Read memory and swap
  ansible.builtin.command: free -m
  register: os_memory
  changed_when: false
```

**Lệnh: `free -m`**

- Hiển thị thông tin RAM và swap.
- `-m` chuyển đơn vị sang **MiB** (mebibyte). Có thể dùng `-g` cho GiB hoặc `-b` cho bytes.

Output mẫu:
```
              total        used        free      shared  buff/cache   available
Mem:          15868        4523        1234         123       10111        11000
Swap:          2047           0        2047
```

| Cột | Ý nghĩa |
|-----|---------|
| `total` | Tổng RAM được cài đặt |
| `used` | RAM đang dùng bởi process |
| `free` | RAM hoàn toàn trống (thường thấp do Linux dùng làm cache) |
| `available` | RAM thực sự khả dụng cho process mới (cột quan trọng nhất) |
| `buff/cache` | RAM đang dùng làm buffer/cache của kernel, có thể giải phóng |

**Cách parse trong Ansible:**

```yaml
# os_memory.stdout_lines[0] là dòng header
# os_memory.stdout_lines[1] là dòng Mem
# os_memory.stdout_lines[2] là dòng Swap

memory_total_mb: "{{ os_memory.stdout_lines[1].split()[1] | int }}"
memory_used_mb:  "{{ os_memory.stdout_lines[1].split()[2] | int }}"
memory_available_mb: "{{ os_memory.stdout_lines[1].split()[6] | int }}"
swap_total_mb: "{{ os_memory.stdout_lines[2].split()[1] | int }}"
swap_used_mb:  "{{ os_memory.stdout_lines[2].split()[2] | int }}"
```

- `.split()` tách dòng theo khoảng trắng thành list.
- `[1]`, `[2]`, `[6]` lấy phần tử theo index 0-based.
- `| int` chuyển string thành số nguyên.

---

#### Task 5: Đọc dung lượng filesystem

```yaml
- name: JOB-OS-01 | Read filesystem usage
  ansible.builtin.command: df -PTh
  register: os_filesystems
  changed_when: false
```

**Lệnh: `df -PTh`**

| Flag | Ý nghĩa |
|------|---------|
| `-P` | POSIX output: mỗi filesystem chiếm đúng **một dòng** dù tên dài. Không có dòng tiếp nối. |
| `-T` | In thêm cột **loại filesystem** (ext4, xfs, tmpfs, overlay, v.v.) |
| `-h` | Human-readable: kích thước dạng `G`, `M`, `K` thay vì số blocks |

Output mẫu:
```
Filesystem     Type      Size  Used Avail Use% Mounted on
/dev/sda1      ext4       98G   35G   58G  38% /
tmpfs          tmpfs      16G  156M   16G   1% /dev/shm
/dev/sdb1      xfs       200G  120G   80G  60% /data
```

**Tại sao dùng `-P` thay vì mặc định?**

Không có `-P`, `df` có thể in tên filesystem dài trên một dòng và số liệu trên dòng tiếp theo, làm hỏng việc parse theo cột.

---

#### Task 6: Đọc inode usage

```yaml
- name: JOB-OS-01 | Read inode usage
  ansible.builtin.command: df -Pi
  register: os_inodes
  changed_when: false
```

**Lệnh: `df -Pi`**

| Flag | Ý nghĩa |
|------|---------|
| `-P` | POSIX output, một dòng mỗi filesystem |
| `-i` | Hiển thị **inode** thay vì dung lượng block |

**Inode là gì?**

Inode là metadata entry của filesystem, mỗi file/directory chiếm một inode. Khi inode hết, filesystem **không thể tạo file mới** dù disk vẫn còn dung lượng trống. Trường hợp này xảy ra khi có hàng triệu file nhỏ (log, container layer).

Output mẫu:
```
Filesystem      Inodes   IUsed   IFree IUse% Mounted on
/dev/sda1      6553600  185432 6368168    3% /
/dev/sdb1     13107200 9800000 1307200   75% /data
```

---

#### Task 7: Phát hiện filesystem mount read-only

```yaml
- name: JOB-OS-01 | Detect read-only filesystems
  ansible.builtin.shell: |
    findmnt -rn -o TARGET,OPTIONS | awk '$2 ~ /(^|,)ro(,|$)/ {print $0}'
  args:
    executable: /bin/bash
  register: os_readonly_filesystems
  changed_when: false
  failed_when: false
```

**Lệnh: `findmnt -rn -o TARGET,OPTIONS`**

| Flag | Ý nghĩa |
|------|---------|
| `-r` | Raw output – bỏ ký tự cây (không có `├─`, `└─`) |
| `-n` | Bỏ header dòng tiêu đề |
| `-o TARGET,OPTIONS` | Chỉ in 2 cột: mount point và danh sách option |

Output mẫu khi chưa lọc:
```
/                  rw,relatime,errors=remount-ro
/sys               rw,nosuid,nodev,noexec,relatime
/proc              rw,nosuid,nodev,noexec,relatime
/run               rw,nosuid,nodev,relatime,mode=755
/dev/shm           rw,nosuid,nodev
/boot              ro,relatime
```

**Lệnh: `awk '$2 ~ /(^|,)ro(,|$)/ {print $0}'`**

| Phần | Ý nghĩa |
|------|---------|
| `$2` | Cột thứ 2 (OPTIONS) |
| `~` | So khớp regex |
| `/(^|,)ro(,|$)/` | Tìm option `ro` đứng riêng: đầu chuỗi HOẶC sau dấu phẩy, theo sau là dấu phẩy HOẶC cuối chuỗi |
| `{print $0}` | In toàn bộ dòng nếu khớp |

**Tại sao dùng regex phức tạp thay vì chỉ grep `ro`?**

Option string có thể là `noatime,relatime,ro,nodiratime`. Nếu chỉ `grep ro` sẽ match cả `errors=remount-ro` hoặc `relatime`. Regex `(^|,)ro(,|$)` đảm bảo chỉ match option `ro` chính xác.

**`failed_when: false`:** Khi không có filesystem nào read-only, `awk` không in gì và lệnh trả `rc=0`. Nhưng một số hệ thống có thể không có `findmnt`, nên đặt `failed_when: false` để job không chết.

**`args: executable: /bin/bash`:** Buộc Ansible dùng bash vì lệnh có pipe `|`. Mặc định Ansible dùng `/bin/sh` có thể thiếu tính năng.

---

#### Task 8: Top process theo CPU

```yaml
- name: JOB-OS-01 | Read top CPU processes
  ansible.builtin.shell: |
    ps -eo pid,user,comm,%cpu,%mem --sort=-%cpu | head -n {{ os_check_top_process_count + 1 }}
  args:
    executable: /bin/bash
  register: os_top_cpu_processes
  changed_when: false
```

**Lệnh: `ps -eo pid,user,comm,%cpu,%mem --sort=-%cpu | head -n N`**

| Phần | Ý nghĩa |
|------|---------|
| `-e` | Lấy **tất cả** process trên hệ thống |
| `-o pid,user,comm,%cpu,%mem` | Chọn cột output: PID, user, tên lệnh ngắn, CPU%, MEM% |
| `--sort=-%cpu` | Sắp xếp **giảm dần** theo CPU% (dấu `-` là giảm dần) |
| `head -n N+1` | Lấy N dòng đầu + 1 dòng header |

`{{ os_check_top_process_count + 1 }}` – Biến `os_check_top_process_count` mặc định là `10`, cộng 1 để giữ dòng header. Kết quả là 11 dòng.

Output mẫu:
```
  PID USER     COMMAND         %CPU %MEM
 1234 root     containerd      45.2  3.1
 5678 nobody   etcd            12.3  8.5
 ...
```

---

#### Task 9: Top process theo RAM

```yaml
- name: JOB-OS-01 | Read top memory processes
  ansible.builtin.shell: |
    ps -eo pid,user,comm,%cpu,%mem --sort=-%mem | head -n {{ os_check_top_process_count + 1 }}
  args:
    executable: /bin/bash
  register: os_top_memory_processes
  changed_when: false
```

Tương tự task top CPU nhưng `--sort=-%mem` sắp xếp theo **RAM%** giảm dần. Giúp phát hiện process chiếm nhiều memory trên node.

---

#### Task 10: Lưu raw data

```yaml
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

**Giải thích:**

- Dùng `.stdout` cho lệnh trả một giá trị đơn (như `nproc`, `cat /proc/loadavg`).
- Dùng `.stdout_lines` cho lệnh trả bảng nhiều dòng (như `free`, `df`, `ps`). `stdout_lines` là list string, dễ xử lý trong template hoặc loop về sau.

---

#### Task 11: Lưu metrics ngắn gọn

```yaml
- name: JOB-OS-01 | Save compact node resource metrics
  ansible.builtin.set_fact:
    os_node_resource_metrics:
      cpu_count: "{{ os_cpu_count.stdout | int }}"
      load_1m: "{{ os_loadavg.stdout.split()[0] | default('0') }}"
      load_5m: "{{ os_loadavg.stdout.split()[1] | default('0') }}"
      load_15m: "{{ os_loadavg.stdout.split()[2] | default('0') }}"
      memory_total_mb: "{{ os_memory.stdout_lines[1].split()[1] | int }}"
      memory_used_mb: "{{ os_memory.stdout_lines[1].split()[2] | int }}"
      memory_available_mb: "{{ os_memory.stdout_lines[1].split()[6] | int }}"
      swap_total_mb: "{{ os_memory.stdout_lines[2].split()[1] | int }}"
      swap_used_mb: "{{ os_memory.stdout_lines[2].split()[2] | int }}"
      filesystems_count: "{{ (os_filesystems.stdout_lines | length) - 1 }}"
      readonly_filesystems_count: "{{ os_readonly_filesystems.stdout_lines | length }}"
      top_cpu_processes_count: "{{ os_check_top_process_count }}"
      top_memory_processes_count: "{{ os_check_top_process_count }}"
  changed_when: false
```

**Giải thích:**

- `| int` – Jinja2 filter chuyển string thành integer.
- `.split()[0]` – Tách chuỗi theo khoảng trắng, lấy phần tử index 0.
- `| default('0')` – Nếu giá trị là `None` hoặc `undefined`, dùng `'0'`.
- `filesystems_count: ... - 1` – Trừ 1 để bỏ dòng header của `df`.
- `readonly_filesystems.stdout_lines | length` – Đếm số dòng, tức số filesystem read-only.

---

### 5.4 JOB-OS-02 – Kiểm tra event log OS

**File:** `tasks/job_os_02_event_logs.yml`

**Mục tiêu:** Đọc log hệ thống để phát hiện kernel error, service failed, disk error, OOM killer, network down, segfault, containerd/kubelet error, authentication failure.

---

#### Task 1: Khởi tạo

```yaml
- name: JOB-OS-02 | Initialize event log result
  ansible.builtin.set_fact:
    os_event_log_raw: {}
    os_event_log_findings: []
  changed_when: false
```

---

#### Task 2: Đọc kernel error

```yaml
- name: JOB-OS-02 | Read kernel errors
  ansible.builtin.command:
    cmd: journalctl -k --since "{{ os_check_log_since }}" --priority=warning..alert --no-pager
  register: os_kernel_errors
  changed_when: false
  failed_when: false
```

**Lệnh: `journalctl -k --since "24 hours ago" --priority=warning..alert --no-pager`**

| Flag | Ý nghĩa |
|------|---------|
| `-k` | Chỉ đọc **kernel messages** – tương đương `dmesg` nhưng từ journal. Bao gồm hardware error, driver error, OOM từ kernel. |
| `--since "24 hours ago"` | Chỉ lấy log trong 24 giờ qua. Giá trị đến từ biến `os_check_log_since`. |
| `--priority=warning..alert` | Lọc mức độ nghiêm trọng từ **warning** đến **alert** (mức 4 đến 1). Bỏ `debug`, `info`, `notice` để giảm nhiễu. |
| `--no-pager` | Không mở `less` hay pager nào. Bắt buộc khi chạy non-interactive. |

**Bảng priority journalctl:**

| Priority | Mức | Ý nghĩa |
|----------|-----|---------|
| 0 | emerg | Hệ thống không dùng được |
| 1 | alert | Phải xử lý ngay |
| 2 | crit | Tình trạng nghiêm trọng |
| 3 | err | Lỗi |
| 4 | warning | Cảnh báo |
| 5 | notice | Bình thường nhưng đáng chú ý |
| 6 | info | Thông tin |
| 7 | debug | Debug |

`warning..alert` lấy từ mức 4 (warning) đến mức 1 (alert), tức các mức 4, 3, 2, 1.

**`failed_when: false`:** Một số hệ thống tối giản không có systemd journal, hoặc user không đủ quyền. Không nên làm chết job chỉ vì không đọc được kernel log.

---

#### Task 3: Đọc service bị failed

```yaml
- name: JOB-OS-02 | Read failed systemd services
  ansible.builtin.command:
    cmd: systemctl --failed --no-pager --plain
  register: os_failed_services
  changed_when: false
  failed_when: false
```

**Lệnh: `systemctl --failed --no-pager --plain`**

| Flag | Ý nghĩa |
|------|---------|
| `--failed` | Liệt kê unit đang ở trạng thái `failed`. |
| `--no-pager` | Không mở pager. |
| `--plain` | Output đơn giản, không có ký tự Unicode trang trí. Dễ parse hơn. |

Output khi có service failed:
```
  UNIT              LOAD   ACTIVE SUB    DESCRIPTION
● kubelet.service   loaded failed failed kubelet: The Kubernetes Node Agent

LOAD   = Reflects whether the unit definition was properly loaded.
ACTIVE = The high-level unit activation state.
SUB    = The low-level unit activation state.

1 loaded units listed.
```

Output khi không có service failed (rc có thể là 1):
```
0 loaded units listed.
```

---

#### Task 4: Lọc log theo pattern lỗi

```yaml
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
```

**Lệnh: `journalctl --since "..." --no-pager`**

- Giống task 2 nhưng **không có `-k`**: đọc log từ toàn bộ service và ứng dụng, không chỉ kernel.

**Lệnh: `grep -Ei 'pattern1|pattern2|...'`**

| Flag | Ý nghĩa |
|------|---------|
| `-E` | Extended regex – cho phép dùng `\|` làm OR. |
| `-i` | Case-insensitive – match cả `I/O Error` lẫn `i/o error`. |

**Các pattern và ý nghĩa:**

| Pattern | Phát hiện |
|---------|-----------|
| `I/O error` | Lỗi đọc/ghi disk ở cấp OS |
| `disk error` | Lỗi phần cứng disk |
| `filesystem error` | Lỗi filesystem (ext4, xfs journal error) |
| `read-only file system` | Filesystem bị remount read-only do lỗi |
| `oom-killer` | OOM Killer kill process do thiếu RAM |
| `segfault` | Process crash do vi phạm vùng nhớ |
| `link is down` | Network interface mất kết nối |
| `authentication failure` | Đăng nhập/xác thực thất bại (brute force, sai password) |
| `containerd` | Lỗi container runtime |
| `kubelet` | Lỗi Kubernetes node agent |

**`|| true`:**

`grep` trả `rc=1` khi không tìm thấy dòng nào khớp. Đây là kết quả bình thường (không có lỗi), không phải lỗi của script. `|| true` làm cho shell luôn trả `rc=0` kể cả khi grep không match gì.

---

#### Task 5: Lưu raw data

```yaml
- name: JOB-OS-02 | Save raw event log result
  ansible.builtin.set_fact:
    os_event_log_raw:
      kernel_errors: "{{ os_kernel_errors.stdout_lines }}"
      failed_services: "{{ os_failed_services.stdout_lines }}"
      error_patterns: "{{ os_error_patterns.stdout_lines }}"
      kernel_errors_stderr: "{{ os_kernel_errors.stderr_lines | default([]) }}"
      failed_services_stderr: "{{ os_failed_services.stderr_lines | default([]) }}"
      error_patterns_stderr: "{{ os_error_patterns.stderr_lines | default([]) }}"
  changed_when: false
```

**Giải thích:** Lưu cả `stderr_lines` để debug khi không đọc được journal (ví dụ thiếu quyền). `| default([])` tránh lỗi Jinja2 khi biến không có trường `stderr_lines`.

---

### 5.5 JOB-OS-03 – Kiểm tra cron job OS

**File:** `tasks/job_os_03_cron_jobs.yml`

**Mục tiêu:** Kiểm kê tất cả tác vụ định kỳ trên node. Job này chỉ đọc, không sửa.

---

#### Task 1: Đọc `/etc/crontab`

```yaml
- name: JOB-OS-03 | Read /etc/crontab
  ansible.builtin.command:
    cmd: cat /etc/crontab
  register: os_system_crontab
  changed_when: false
  failed_when: false
```

**File `/etc/crontab`:** Cron hệ thống. Khác với user crontab, file này có thêm cột `user` chỉ định user chạy lệnh:

```
# m h dom mon dow user  command
17 *  * * *  root  cd / && run-parts --report /etc/cron.hourly
25 6  * * *  root  test -x /usr/sbin/anacron || run-parts --report /etc/cron.daily
```

---

#### Task 2: Tìm file trong `/etc/cron.d`

```yaml
- name: JOB-OS-03 | Find files in /etc/cron.d
  ansible.builtin.find:
    paths: /etc/cron.d
    file_type: file
  register: os_cron_d_files
  changed_when: false
  failed_when: false
```

**Module `ansible.builtin.find`:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `paths` | `/etc/cron.d` | Thư mục cần tìm |
| `file_type` | `file` | Chỉ lấy file thường, bỏ qua directory và symlink |

Kết quả `os_cron_d_files.files` là list dict, mỗi item có key `path`, `size`, `mode`, v.v.

**Tại sao không dùng `ls -la /etc/cron.d`?** Module `find` an toàn hơn, trả dict có cấu trúc, không cần parse text có thể bị format khác nhau tùy OS.

---

#### Task 3: Đọc nội dung từng file trong `/etc/cron.d`

```yaml
- name: JOB-OS-03 | Read /etc/cron.d files
  ansible.builtin.command:
    cmd: cat {{ item.path }}
  loop: "{{ os_cron_d_files.files | default([]) }}"
  register: os_cron_d_content
  changed_when: false
  failed_when: false
```

**`loop`:** Chạy task cho từng file tìm được. `item` là mỗi dict trong list `os_cron_d_files.files`. `item.path` là đường dẫn đầy đủ.

**`| default([])`:** Nếu `/etc/cron.d` không tồn tại, `find` module trả `files: []`. Filter `default([])` tránh lỗi khi biến không tồn tại.

**`os_cron_d_content.results`:** Khi dùng `loop` với `register`, kết quả được gom vào field `results` là list, mỗi phần tử tương ứng một lần lặp.

---

#### Task 4: Liệt kê script trong thư mục cron định kỳ

```yaml
- name: JOB-OS-03 | List periodic cron scripts
  ansible.builtin.shell: |
    for d in /etc/cron.hourly /etc/cron.daily /etc/cron.weekly /etc/cron.monthly; do
      [ -d "$d" ] && find "$d" -maxdepth 1 -type f -printf '%p\n'
    done
  args:
    executable: /bin/bash
  register: os_periodic_cron_files
  changed_when: false
  failed_when: false
```

**Giải thích từng lệnh shell:**

| Phần | Ý nghĩa |
|------|---------|
| `for d in /etc/cron.hourly ...` | Lặp qua 4 thư mục cron định kỳ chuẩn |
| `[ -d "$d" ]` | Kiểm tra thư mục có tồn tại không (`-d` = is directory) |
| `&&` | Chỉ chạy lệnh tiếp theo nếu `[ -d ]` thành công |
| `find "$d" -maxdepth 1 -type f` | Tìm file ngay trong thư mục, không đi vào thư mục con (`-maxdepth 1`) |
| `-printf '%p\n'` | In full path của file, mỗi file một dòng |

**Các thư mục cron định kỳ:**

| Thư mục | Khi chạy |
|---------|---------|
| `/etc/cron.hourly` | Mỗi giờ |
| `/etc/cron.daily` | Mỗi ngày |
| `/etc/cron.weekly` | Mỗi tuần |
| `/etc/cron.monthly` | Mỗi tháng |

---

#### Task 5: Đọc danh sách user hệ thống

```yaml
- name: JOB-OS-03 | Read /etc/passwd users
  ansible.builtin.command:
    cmd: getent passwd
  register: os_passwd_users
  changed_when: false
  failed_when: false
```

**Lệnh: `getent passwd`**

- `getent` đọc database từ NSS (Name Service Switch), bao gồm `/etc/passwd` và các nguồn khác (LDAP, NIS nếu có).
- Mỗi dòng output có format: `username:password:uid:gid:gecos:home:shell`
- Dùng để lấy danh sách user cần kiểm tra crontab.

---

#### Task 6: Đọc crontab từng user

```yaml
- name: JOB-OS-03 | Read user crontabs
  ansible.builtin.command:
    cmd: crontab -u {{ item.split(':')[0] }} -l
  loop: "{{ os_passwd_users.stdout_lines | default([]) }}"
  register: os_user_crontabs
  changed_when: false
  failed_when: false
```

**Lệnh: `crontab -u USERNAME -l`**

| Flag | Ý nghĩa |
|------|---------|
| `-u USERNAME` | Chỉ định user cần đọc crontab |
| `-l` | List (hiển thị) nội dung crontab |

**`item.split(':')[0]`:**

- Mỗi dòng `getent passwd` có format `username:x:uid:gid:...`
- `.split(':')` tách theo dấu `:` thành list.
- `[0]` lấy phần tử đầu tiên là username.

**`failed_when: false`:** `crontab -l` trả `rc=1` khi user không có crontab. Đây là trạng thái bình thường.

---

#### Task 7: Đọc systemd timer

```yaml
- name: JOB-OS-03 | Read systemd timers
  ansible.builtin.command:
    cmd: systemctl list-timers --all --no-pager --plain
  register: os_systemd_timers
  changed_when: false
  failed_when: false
```

**Lệnh: `systemctl list-timers --all --no-pager --plain`**

| Flag | Ý nghĩa |
|------|---------|
| `list-timers` | Liệt kê các unit timer của systemd |
| `--all` | Hiển thị cả timer đang inactive |
| `--no-pager` | Không mở pager |
| `--plain` | Output đơn giản, không có ký tự trang trí |

**Tại sao cần kiểm tra systemd timer?**

Nhiều tác vụ định kỳ hiện đại (backup, logrotate, update) đã chuyển từ cron sang systemd timer. Nếu chỉ kiểm tra cron, bỏ qua systemd timer sẽ thiếu bức tranh toàn diện.

---

#### Task 8: Lưu raw data

```yaml
- name: JOB-OS-03 | Save raw cron job result
  ansible.builtin.set_fact:
    os_cron_jobs_raw:
      system_crontab: "{{ os_system_crontab.stdout_lines | default([]) }}"
      system_crontab_stderr: "{{ os_system_crontab.stderr_lines | default([]) }}"
      cron_d_files: "{{ os_cron_d_files.files | default([]) }}"
      cron_d_content: "{{ os_cron_d_content.results | default([]) }}"
      periodic_cron_files: "{{ os_periodic_cron_files.stdout_lines | default([]) }}"
      passwd_users: "{{ os_passwd_users.stdout_lines | default([]) }}"
      user_crontabs: "{{ os_user_crontabs.results | default([]) }}"
      systemd_timers: "{{ os_systemd_timers.stdout_lines | default([]) }}"
      systemd_timers_stderr: "{{ os_systemd_timers.stderr_lines | default([]) }}"
  changed_when: false
```

---

### 5.6 JOB-OS-04 – Kiểm tra SMART ổ đĩa

**File:** `tasks/job_os_04_smart.yml`

**SMART** (Self-Monitoring, Analysis and Reporting Technology) là công nghệ giám sát sức khỏe ổ đĩa được controller/firmware cung cấp.

**Lưu ý:** Với VM thông thường, dữ liệu SMART của ổ vật lý không được expose vào guest OS. Job này xử lý 3 trường hợp:
1. Máy vật lý có `smartctl` → kiểm tra bình thường.
2. VM có SMART passthrough → kiểm tra nếu `smartctl --scan-open` tìm thấy thiết bị.
3. VM không expose SMART → trả `skipped`, không kết luận gì về ổ vật lý.

---

#### Task 1: Khởi tạo

```yaml
- name: JOB-OS-04 | Initialize SMART result
  ansible.builtin.set_fact:
    os_smart_raw: {}
    os_smart_findings: []
    os_smart_skipped: []
    os_smart_should_run: false
  changed_when: false
```

`os_smart_should_run: false` là "công tắc" điều kiện. Nếu sau kiểm tra điều kiện không đủ để đọc SMART, các task đọc thật sẽ bị bỏ qua (`when: os_smart_should_run`).

---

#### Task 2: Phát hiện loại ảo hóa

```yaml
- name: JOB-OS-04 | Detect virtualization type
  ansible.builtin.command:
    cmd: systemd-detect-virt
  register: os_virtualization_type
  changed_when: false
  failed_when: false
```

**Lệnh: `systemd-detect-virt`**

- Phát hiện hệ thống đang chạy trong môi trường ảo hóa nào.
- Đọc thông tin từ DMI/SMBIOS, `/proc/cpuinfo`, cgroup, namespace.

| Output | Ý nghĩa |
|--------|---------|
| `none` | Máy vật lý (bare metal) |
| `kvm` | KVM/QEMU |
| `vmware` | VMware ESXi |
| `microsoft` | Hyper-V |
| `oracle` | Oracle VirtualBox |
| `xen` | Xen hypervisor |
| `docker` | Chạy trong Docker container |
| `lxc` | Chạy trong LXC container |

`failed_when: false` – Một số phiên bản systemd cũ có thể không có lệnh này.

---

#### Task 3: Chuẩn hóa kết quả ảo hóa

```yaml
- name: JOB-OS-04 | Normalize virtualization type
  ansible.builtin.set_fact:
    os_virtualization_normalized: >-
      {{
        os_virtualization_type.stdout
        if os_virtualization_type.rc == 0
        else 'none'
      }}
  changed_when: false
```

**Jinja2 conditional:**

```
value_if_true if condition else value_if_false
```

Nếu `systemd-detect-virt` chạy thành công (`rc == 0`): dùng stdout.
Nếu lệnh không tồn tại (`rc != 0`): coi là `'none'` (máy vật lý).

`>-` là YAML block scalar cho phép viết Jinja2 nhiều dòng mà không bị lỗi indent.

---

#### Task 4: Kiểm tra smartctl có sẵn không

```yaml
- name: JOB-OS-04 | Check smartctl availability
  ansible.builtin.shell: |
    command -v smartctl
  args:
    executable: /bin/bash
  register: os_smartctl_command
  changed_when: false
  failed_when: false
```

**Lệnh: `command -v smartctl`**

- `command -v` là **shell builtin** (không phải external command) dùng để tìm executable trong `$PATH`.
- Trả đường dẫn đầy đủ nếu tìm thấy, ví dụ: `/usr/sbin/smartctl`.
- Trả `rc=1` nếu không tìm thấy.

**Tại sao dùng `shell` thay vì `command` module?**

`command -v` là shell builtin, không phải external binary. Ansible `command` module chạy binary trực tiếp, không qua shell, nên không thực thi được builtin. Phải dùng `shell` module.

---

#### Task 5: Quét thiết bị SMART

```yaml
- name: JOB-OS-04 | Scan SMART-capable devices
  ansible.builtin.command:
    cmd: smartctl --scan-open
  register: os_smart_scan
  changed_when: false
  failed_when: false
  when: os_smartctl_command.rc == 0
```

**Lệnh: `smartctl --scan-open`**

- Quét các thiết bị storage mà smartctl có thể mở và nhận diện.
- `--scan-open` khác `--scan`: nó thực sự mở thiết bị để xác nhận có quyền truy cập và thiết bị phản hồi SMART.

Output mẫu:
```
/dev/sda -d sat # /dev/sda, ATA device
/dev/sdb -d sat # /dev/sdb, ATA device
/dev/nvme0 -d nvme # /dev/nvme0, NVMe device
```

`when: os_smartctl_command.rc == 0` – Chỉ chạy nếu `smartctl` đã được tìm thấy.

---

#### Task 6: Xây dựng danh sách thiết bị

```yaml
- name: JOB-OS-04 | Build SMART device list
  ansible.builtin.set_fact:
    os_smart_device_lines: >-
      {{
        os_smart_scan.stdout_lines
        | default([])
        | reject('match', '^\\s*$')
        | reject('match', '^#')
        | list
      }}
  changed_when: false
  when: os_smartctl_command.rc == 0
```

**Jinja2 filter chain:**

| Filter | Tác dụng |
|--------|---------|
| `default([])` | Nếu `stdout_lines` là undefined, dùng list rỗng |
| `reject('match', '^\\s*$')` | Loại dòng trống (chỉ có whitespace) |
| `reject('match', '^#')` | Loại dòng comment bắt đầu bằng `#` |
| `list` | Chuyển kết quả thành list |

---

#### Task 7: Quyết định có chạy kiểm tra SMART không

```yaml
- name: JOB-OS-04 | Decide whether SMART check should run
  ansible.builtin.set_fact:
    os_smart_should_run: >-
      {{
        os_smartctl_command.rc == 0
        and ((os_smart_device_lines | default([]) | length) > 0)
      }}
  changed_when: false
```

`os_smart_should_run = True` khi:
1. `smartctl` được tìm thấy (`rc == 0`), **VÀ**
2. Có ít nhất một thiết bị SMART (`length > 0`).

---

#### Task 8: Đánh dấu skipped khi không thể chạy

```yaml
- name: JOB-OS-04 | Mark skipped when SMART cannot run
  ansible.builtin.set_fact:
    os_smart_skipped: >-
      {{
        os_smart_skipped
        + [
          {
            'job': 'JOB-OS-04',
            'target': inventory_hostname,
            'severity': 'skipped',
            'check': (
              'os.smart.smartctl_missing'
              if os_smartctl_command.rc != 0
              else (
                'os.smart.vm_not_exposed'
                if os_virtualization_normalized != 'none'
                else 'os.smart.no_devices'
              )
            ),
            'message': (
              'smartctl is not installed'
              if os_smartctl_command.rc != 0
              else (
                'SMART data is not exposed to the VM'
                if os_virtualization_normalized != 'none'
                else 'No SMART-capable devices were detected'
              )
            ),
            'evidence': [
              'virtualization=' ~ os_virtualization_normalized,
              'smart_devices=' ~ ((os_smart_device_lines | default([]) | length) | string)
            ]
          }
        ]
      }}
  changed_when: false
  when: not os_smart_should_run
```

**Giải thích logic điều kiện lồng nhau:**

```
check =
  nếu smartctl thiếu      → 'os.smart.smartctl_missing'
  nếu là VM               → 'os.smart.vm_not_exposed'
  nếu không tìm thấy disk → 'os.smart.no_devices'
```

**`os_smart_skipped + [...]`:** Thêm một phần tử vào list bằng cách nối list. Jinja2 không có `.append()`, cách thêm phần tử vào list là `list + [new_item]`.

**`~ os_virtualization_normalized`:** Toán tử `~` trong Jinja2 là string concatenation (nối chuỗi).

---

#### Task 9: Đọc dữ liệu SMART thật (chỉ khi điều kiện đủ)

```yaml
- name: JOB-OS-04 | Run SMART checks only when prerequisites are met
  when: os_smart_should_run
  block:
    - name: JOB-OS-04 | Read SMART data for detected devices
      ansible.builtin.command:
        cmd: smartctl -x {{ item.split()[0] }}
      loop: "{{ os_smart_device_lines }}"
      register: os_smart_data
      changed_when: false
      failed_when: false
```

**`block:`** – Nhóm nhiều task lại dưới một điều kiện `when`. Nếu `os_smart_should_run` là false, toàn bộ block bị bỏ qua.

**Lệnh: `smartctl -x /dev/sda`**

| Flag | Ý nghĩa |
|------|---------|
| `-x` | In **toàn bộ** thông tin SMART mở rộng: health, attributes, error log, self-test log, NVMe log |

**`item.split()[0]`:**

Mỗi dòng từ `--scan-open` có dạng `/dev/sda -d sat # comment`. `.split()[0]` lấy cột đầu tiên là đường dẫn thiết bị.

---

#### Task 10: Phát hiện health failure từ raw output

```yaml
    - name: JOB-OS-04 | Detect SMART health failures from raw output
      ansible.builtin.set_fact:
        os_smart_findings: >-
          {{
            os_smart_findings
            + [
              {
                'job': 'JOB-OS-04',
                'target': inventory_hostname,
                'severity': 'critical',
                'check': 'os.smart.health_failed',
                'message': 'SMART health check reports a failed or critical state',
                'evidence': item.stdout_lines | default([])
              }
            ]
          }}
      loop: "{{ os_smart_data.results | default([]) }}"
      changed_when: false
      when:
        - item.stdout is defined
        - item.stdout is search('(?i)(SMART overall-health self-assessment test result:\s*FAILED|SMART Health Status:\s*FAILED|critical warning:\s*[1-9]|Media and Data Integrity Errors:\s*[1-9])')
```

**`item.stdout is search('regex')`** – Jinja2 test `search` tìm pattern regex trong chuỗi (khác với `match` chỉ match từ đầu chuỗi).

**Regex giải thích:**

| Pattern | Ý nghĩa |
|---------|---------|
| `(?i)` | Case-insensitive |
| `SMART overall-health self-assessment test result:\s*FAILED` | Output của `smartctl -H` cho HDD/SSD SATA khi health failed |
| `SMART Health Status:\s*FAILED` | Output tương tự cho một số controller |
| `critical warning:\s*[1-9]` | NVMe critical warning register khác 0 |
| `Media and Data Integrity Errors:\s*[1-9]` | NVMe có lỗi media không hồi phục được |

---

### 5.7 Save report (`tasks/save_report.yml`)

**File:** `tasks/save_report.yml`

**Mục tiêu:** Tổng hợp kết quả từ 4 job OS, tính status tổng, ghi file JSON về máy control node.

**Output files (trên máy control):**

```
artifacts/
└── os/
    └── <hostname>/
        ├── job-os-01-resources.json
        ├── job-os-02-event-logs.json
        ├── job-os-03-cron-jobs.json
        ├── job-os-04-smart.json
        └── os-summary.json
```

---

#### Task: Tạo thư mục artifact

```yaml
- name: OS report | Ensure host artifact directory exists on control node
  ansible.builtin.file:
    path: "{{ os_check_artifact_dir }}/os/{{ inventory_hostname }}"
    state: directory
    mode: "0755"
  delegate_to: localhost
  become: false
  changed_when: false
```

**`delegate_to: localhost`** – Chạy task này trên **máy control** (laptop/server chạy ansible-playbook), không chạy trên remote node. Điều này tạo thư mục trên máy control để ghi file báo cáo về.

**`become: false`** – Không cần sudo trên máy control. Ghi đè `become: true` ở level playbook cho task cụ thể này.

---

#### Task: Build report JOB-OS-01

```yaml
- name: OS report | Build JOB-OS-01 report
  ansible.builtin.set_fact:
    os_job_01_report:
      job: JOB-OS-01
      name: Kiểm tra tài nguyên node
      host: "{{ inventory_hostname }}"
      status:
        overall: >-
          {{
            'critical'
            if ((os_node_resource_findings | default([])) | selectattr('severity', 'equalto', 'critical') | list | length) > 0
            else (
              'warning'
              if ((os_node_resource_findings | default([])) | selectattr('severity', 'equalto', 'warning') | list | length) > 0
              else 'ok'
            )
          }}
      metrics: "{{ os_node_resource_metrics | default({}) }}"
      findings: "{{ os_node_resource_findings | default([]) }}"
  changed_when: false
```

**`selectattr('severity', 'equalto', 'critical')`** – Jinja2 filter lọc list dict theo trường `severity` bằng `'critical'`.

**Logic status:**

```
overall =
  'critical' nếu có bất kỳ finding nào severity=critical
  'warning'  nếu không có critical nhưng có warning
  'ok'       nếu không có gì
```

---

#### Task: Bật raw data khi debug

```yaml
- name: OS report | Add raw data to per-job reports when debug is enabled
  ansible.builtin.set_fact:
    os_job_01_report: "{{ os_job_01_report | combine({'raw': os_node_resource_raw | default({})}, recursive=True) }}"
    os_job_02_report: "{{ os_job_02_report | combine({'raw': os_event_log_raw | default({})}, recursive=True) }}"
    os_job_03_report: "{{ os_job_03_report | combine({'raw': os_cron_jobs_raw | default({})}, recursive=True) }}"
    os_job_04_report: "{{ os_job_04_report | combine({'raw': os_smart_raw | default({})}, recursive=True) }}"
  changed_when: false
  when: os_check_include_raw | bool
```

**`combine({'raw': ...}, recursive=True)`** – Jinja2 filter merge dict. `recursive=True` merge sâu, không chỉ overwrite top-level key.

**`| bool`** – Chuyển string `"true"`/`"false"` thành boolean. Cần thiết vì biến truyền từ `-e os_check_include_raw=true` ban đầu là string.

---

#### Task: Ghi file JSON

```yaml
- name: OS report | Save JOB-OS-01 report
  ansible.builtin.copy:
    content: "{{ os_job_01_report | to_nice_json }}"
    dest: "{{ os_check_artifact_dir }}/os/{{ inventory_hostname }}/job-os-01-resources.json"
    mode: "0644"
  delegate_to: localhost
  become: false
```

**`to_nice_json`** – Jinja2 filter convert dict/list thành JSON có indent (pretty-print), dễ đọc.

**`ansible.builtin.copy` với `content:`** – Khác với copy file, khi dùng `content:` thì nội dung là inline string, không phải file trên disk.

---

## 6. Role `k8s_checks`

Role này chỉ chạy trên **một node control-plane** (`cp01`) vì mọi thao tác đi qua Kubernetes API. Task nào cần chạy trên từng node (crictl stats) sẽ dùng `delegate_to`.

---

### 6.1 Biến mặc định (`defaults/main.yml`)

```yaml
---
k8s_check_kubectl: /var/lib/rancher/rke2/bin/kubectl
k8s_check_kubeconfig: /etc/rancher/rke2/rke2.yaml
k8s_check_crictl: /var/lib/rancher/rke2/bin/crictl
k8s_check_event_since: "24h"
k8s_check_pending_pod_minutes: 10
k8s_check_cpu_request_warning_percent: 80
k8s_check_cpu_request_critical_percent: 90
k8s_check_memory_request_warning_percent: 80
k8s_check_memory_request_critical_percent: 90
k8s_check_warning_event_repeat_threshold: 3
k8s_check_alertmanager_url: ""
k8s_check_artifact_dir: "{{ playbook_dir }}/../artifacts"
k8s_check_include_raw: false
```

**Giải thích từng biến:**

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `k8s_check_kubectl` | `/var/lib/rancher/rke2/bin/kubectl` | Đường dẫn kubectl của RKE2. Khác với kubectl cài hệ thống (thường ở `/usr/bin/kubectl`). |
| `k8s_check_kubeconfig` | `/etc/rancher/rke2/rke2.yaml` | Kubeconfig của RKE2 với quyền admin. |
| `k8s_check_crictl` | `/var/lib/rancher/rke2/bin/crictl` | Đường dẫn crictl của RKE2. |
| `k8s_check_event_since` | `"24h"` | Lọc event trong 24 giờ. (Hiện tại chưa dùng trực tiếp vì Kubernetes Event API không có filter thời gian.) |
| `k8s_check_pending_pod_minutes` | `10` | Pod Pending quá N phút thì tạo alert. |
| `k8s_check_cpu_request_warning_percent` | `80` | CPU request / allocatable vượt ngưỡng → warning. |
| `k8s_check_cpu_request_critical_percent` | `90` | CPU request / allocatable vượt ngưỡng → critical. |
| `k8s_check_memory_request_warning_percent` | `80` | Memory request / allocatable vượt ngưỡng → warning. |
| `k8s_check_memory_request_critical_percent` | `90` | Memory request / allocatable vượt ngưỡng → critical. |
| `k8s_check_warning_event_repeat_threshold` | `3` | Event Warning lặp ≥ N lần mới tạo finding. |
| `k8s_check_alertmanager_url` | `""` | URL Alertmanager. Rỗng = không tích hợp Alertmanager. |
| `k8s_check_artifact_dir` | `{{ playbook_dir }}/../artifacts` | Thư mục ghi báo cáo. |
| `k8s_check_include_raw` | `false` | Bật raw data debug. |

---

### 6.2 File điều phối (`tasks/main.yml`)

```yaml
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

- name: Save Kubernetes check report
  ansible.builtin.import_tasks: save_report.yml
  tags:
    - always
    - k8s_report
```

**Lưu ý quan trọng:** JOB-K8S-03 phụ thuộc vào dữ liệu từ JOB-K8S-01 (node conditions, pod list) và JOB-K8S-02 (warning events). Do đó thứ tự chạy phải là 01 → 02 → 03.

---

### 6.3 JOB-K8S-01 – Kiểm tra tài nguyên

**File:** `tasks/job_k8s_01_resources.yml`

---

#### Task 1: Khởi tạo

```yaml
- name: JOB-K8S-01 | Initialize Kubernetes resource result
  ansible.builtin.set_fact:
    k8s_resource_raw: {}
    k8s_resource_findings: []
    k8s_resource_skipped: []
  changed_when: false
```

---

#### Task 2: Đọc danh sách node

```yaml
- name: JOB-K8S-01 | Read Kubernetes nodes as JSON
  ansible.builtin.command:
    cmd: "{{ k8s_check_kubectl }} --kubeconfig {{ k8s_check_kubeconfig }} get nodes -o json"
  register: k8s_nodes_json
  changed_when: false
```

**Lệnh: `kubectl --kubeconfig /etc/rancher/rke2/rke2.yaml get nodes -o json`**

| Phần | Ý nghĩa |
|------|---------|
| `--kubeconfig` | Chỉ rõ kubeconfig. RKE2 đặt kubeconfig tại `/etc/rancher/rke2/rke2.yaml` với permission 0600, chỉ root đọc được. Playbook chạy với `become: true` nên truy cập được. |
| `get nodes` | Lấy tất cả node object trong cluster |
| `-o json` | Output dạng JSON thay vì text table |

**Dữ liệu JSON chứa:**

```json
{
  "items": [
    {
      "metadata": { "name": "cp01" },
      "status": {
        "conditions": [
          { "type": "Ready", "status": "True" },
          { "type": "MemoryPressure", "status": "False" },
          { "type": "DiskPressure", "status": "False" }
        ],
        "capacity": { "cpu": "8", "memory": "16Gi", "pods": "110" },
        "allocatable": { "cpu": "7800m", "memory": "15Gi", "pods": "110" }
      }
    }
  ]
}
```

**Tại sao dùng `-o json` thay vì text?**

JSON có cấu trúc cố định, parse bằng `from_json` trong Ansible an toàn và không bị ảnh hưởng bởi thay đổi cột, locale, hay timezone. Nếu parse text table, một thay đổi nhỏ trong format sẽ làm hỏng logic.

---

#### Task 3: Đọc tất cả pod

```yaml
- name: JOB-K8S-01 | Read all pods as JSON
  ansible.builtin.command:
    cmd: "{{ k8s_check_kubectl }} --kubeconfig {{ k8s_check_kubeconfig }} get pods -A -o json"
  register: k8s_pods_json
  changed_when: false
```

**`-A` (viết tắt của `--all-namespaces`):** Lấy pod từ tất cả namespace trong cluster.

**Dữ liệu JSON pod chứa:**
- `metadata.name`, `metadata.namespace`
- `spec.nodeName` – Node đang chạy
- `status.phase` – Running, Pending, Failed, Succeeded, Unknown
- `spec.containers[].resources.requests` – CPU/RAM request
- `spec.containers[].resources.limits` – CPU/RAM limit
- `status.containerStatuses[].state` – Trạng thái từng container

---

#### Task 4: Thử Metrics API cho node

```yaml
- name: JOB-K8S-01 | Try Metrics API for node usage
  ansible.builtin.command:
    cmd: "{{ k8s_check_kubectl }} --kubeconfig {{ k8s_check_kubeconfig }} top nodes --no-headers"
  register: k8s_top_nodes
  changed_when: false
  failed_when: false
```

**Lệnh: `kubectl top nodes --no-headers`**

- Lấy CPU/RAM **usage thực tế** của từng node từ Metrics Server.
- Khác với `capacity`/`allocatable` là tĩnh, `top nodes` là số thực tế đang tiêu thụ.

Output mẫu:
```
cp01   245m   3%    4523Mi   28%
cp02   198m   2%    3891Mi   24%
wk01   1200m  15%   8234Mi   51%
```

**`--no-headers`:** Bỏ dòng header để output gọn hơn khi parse.

**`failed_when: false`:** Nếu Metrics Server không được cài (phổ biến trong môi trường nhỏ), lệnh này fail với message `Metrics API not available`. Không nên làm fail toàn bộ job vì vẫn có thể kiểm tra qua capacity/request/limit.

---

#### Task 5: Thử Metrics API cho pod

```yaml
- name: JOB-K8S-01 | Try Metrics API for pod usage
  ansible.builtin.command:
    cmd: "{{ k8s_check_kubectl }} --kubeconfig {{ k8s_check_kubeconfig }} top pods -A --no-headers"
  register: k8s_top_pods
  changed_when: false
  failed_when: false
```

Tương tự task 4 nhưng cho pod. `-A` lấy mọi namespace.

---

#### Task 6: Fallback sang crictl khi không có Metrics API

```yaml
- name: JOB-K8S-01 | Fallback to crictl stats when Metrics API is unavailable
  ansible.builtin.command:
    cmd: "{{ k8s_check_crictl }} stats -o json"
  loop: "{{ groups['kubernetes_servers'] | default([]) }}"
  delegate_to: "{{ item }}"
  register: k8s_crictl_stats
  changed_when: false
  failed_when: false
  when: k8s_top_pods.rc != 0
```

**`crictl stats -o json`**

- `crictl` (Container Runtime Interface CLI) giao tiếp trực tiếp với container runtime (containerd).
- `stats` trả CPU/RAM usage của container trên node đang chạy crictl.
- `-o json` trả dữ liệu có cấu trúc.

**`loop: "{{ groups['kubernetes_servers'] }}"` + `delegate_to: "{{ item }}"`**

Đây là pattern quan trọng:
- `loop` lặp qua danh sách hostname trong group `kubernetes_servers`.
- `delegate_to: "{{ item }}"` chuyển hướng từng lần lặp sang chạy trực tiếp trên node đó.
- Kết quả là task chạy `crictl stats` trên **từng node** dù play đang chạy trên `cp01`.
- `register: k8s_crictl_stats` gom tất cả kết quả vào `.results`.

**Tại sao crictl phải chạy trên từng node?**

Container runtime chỉ biết container đang chạy trên chính node đó. Không có cách nào lấy stats của tất cả node từ một điểm trung tâm mà không có Metrics Server.

---

#### Task 7: Đánh dấu skipped khi Metrics API không có

```yaml
- name: JOB-K8S-01 | Mark Metrics API skipped when unavailable
  ansible.builtin.set_fact:
    k8s_resource_skipped: >-
      {{
        k8s_resource_skipped
        + [
          {
            'job': 'JOB-K8S-01',
            'target': 'cluster',
            'severity': 'skipped',
            'check': 'k8s.metrics_api',
            'message': 'Metrics API is unavailable; fallback to crictl stats was attempted',
            'evidence': [k8s_top_pods.stderr | default('')]
          }
        ]
      }}
  changed_when: false
  when: k8s_top_pods.rc != 0
```

---

#### Task 8: Lưu raw data

```yaml
- name: JOB-K8S-01 | Save Kubernetes resource raw result
  ansible.builtin.set_fact:
    k8s_resource_raw:
      nodes: "{{ k8s_nodes_json.stdout | from_json }}"
      pods: "{{ k8s_pods_json.stdout | from_json }}"
      metrics_api:
        top_nodes_available: "{{ k8s_top_nodes.rc == 0 }}"
        top_nodes: "{{ k8s_top_nodes.stdout_lines | default([]) }}"
        top_nodes_error: "{{ k8s_top_nodes.stderr_lines | default([]) }}"
        top_pods_available: "{{ k8s_top_pods.rc == 0 }}"
        top_pods: "{{ k8s_top_pods.stdout_lines | default([]) }}"
        top_pods_error: "{{ k8s_top_pods.stderr_lines | default([]) }}"
      runtime_stats:
        crictl_results: "{{ k8s_crictl_stats.results | default([]) }}"
      skipped: "{{ k8s_resource_skipped }}"
  changed_when: false
```

**`| from_json`** – Jinja2 filter parse chuỗi JSON thành dict/list Python. Sau khi parse, có thể dùng `.get('items', [])`, `selectattr()`, `map()`, v.v.

---

#### Task 9: Tính metrics ngắn gọn

```yaml
- name: JOB-K8S-01 | Initialize compact Kubernetes metrics
  ansible.builtin.set_fact:
    k8s_resource_metrics:
      nodes_total: "{{ (k8s_resource_raw.get('nodes', {}).get('items', [])) | length }}"
      pods_total: "{{ (k8s_resource_raw.get('pods', {}).get('items', [])) | length }}"
      pods_running: "{{ (k8s_resource_raw.get('pods', {}).get('items', []) | selectattr('status.phase', 'equalto', 'Running') | list) | length }}"
      pods_pending: "{{ (k8s_resource_raw.get('pods', {}).get('items', []) | selectattr('status.phase', 'equalto', 'Pending') | list) | length }}"
      pods_failed: "{{ (k8s_resource_raw.get('pods', {}).get('items', []) | selectattr('status.phase', 'equalto', 'Failed') | list) | length }}"
      pods_succeeded: "{{ (k8s_resource_raw.get('pods', {}).get('items', []) | selectattr('status.phase', 'equalto', 'Succeeded') | list) | length }}"
      pods_capacity_total: 0
      pods_allocatable_total: 0
      metrics_api_top_nodes_available: "{{ k8s_top_nodes.rc == 0 }}"
      metrics_api_top_pods_available: "{{ k8s_top_pods.rc == 0 }}"
  changed_when: false
```

**`selectattr('status.phase', 'equalto', 'Running')`** – Lọc list pod theo giá trị của field `status.phase`. Hỗ trợ dot notation để truy cập nested field.

---

#### Task 10: Tính tổng pod capacity từng node

```yaml
- name: JOB-K8S-01 | Sum pod capacity and allocatable from nodes
  ansible.builtin.set_fact:
    k8s_resource_metrics: >-
      {{
        k8s_resource_metrics
        | combine(
          {
            'pods_capacity_total': ((k8s_resource_metrics.get('pods_capacity_total', 0) | int) + (item.get('status', {}).get('capacity', {}).get('pods', 0) | int)),
            'pods_allocatable_total': ((k8s_resource_metrics.get('pods_allocatable_total', 0) | int) + (item.get('status', {}).get('allocatable', {}).get('pods', 0) | int))
          },
          recursive=True
        )
      }}
  loop: "{{ k8s_resource_raw.get('nodes', {}).get('items', []) }}"
  changed_when: false
```

**Pattern cộng dồn qua loop:**

Jinja2/Ansible không có built-in `sum` trên dict list theo nested key. Cách duy nhất là loop và dùng `combine` để cập nhật biến dần:

```
Lần 1: pods_capacity_total = 0 + node_cp01.capacity.pods = 110
Lần 2: pods_capacity_total = 110 + node_cp02.capacity.pods = 220
...
```

---

### 6.4 JOB-K8S-02 – Kiểm tra event toàn cụm

**File:** `tasks/job_k8s_02_events.yml`

---

#### Task 1: Khởi tạo

```yaml
- name: JOB-K8S-02 | Initialize Kubernetes event result
  ansible.builtin.set_fact:
    k8s_events_raw: {}
    k8s_warning_events: []
    k8s_event_findings: []
    k8s_event_skipped: []
  changed_when: false
```

---

#### Task 2: Đọc event toàn cluster

```yaml
- name: JOB-K8S-02 | Read events from all namespaces
  ansible.builtin.command:
    cmd: "{{ k8s_check_kubectl }} --kubeconfig {{ k8s_check_kubeconfig }} get events -A -o json"
  register: k8s_events_json
  changed_when: false
  failed_when: false
```

**Lệnh: `kubectl get events -A -o json`**

| Phần | Ý nghĩa |
|------|---------|
| `get events` | Lấy Kubernetes Event object |
| `-A` | Tất cả namespace |
| `-o json` | JSON có cấu trúc |

**Kubernetes Event:**

- Mỗi Event liên quan đến một object (Pod, Node, Deployment, PVC...).
- Có `type`: `Normal` hoặc `Warning`.
- Có `reason`: mã ngắn ví dụ `OOMKilling`, `BackOff`, `FailedMount`.
- Có `message`: mô tả chi tiết.
- Có `count`: số lần xảy ra.
- **TTL ngắn**: mặc định Kubernetes chỉ giữ event trong ~1 giờ (configurable).

---

#### Task 3: Lưu raw event (safe parse)

```yaml
- name: JOB-K8S-02 | Save raw events
  ansible.builtin.set_fact:
    k8s_events_raw: >-
      {{
        (k8s_events_json.stdout | default('{"items":[]}', true) | from_json)
        if k8s_events_json.rc == 0
        else {'items': []}
      }}
  changed_when: false
```

**`| default('{"items":[]}', true)`**

Tham số thứ hai `true` của filter `default` kích hoạt chế độ "boolean=true", tức là trả default khi giá trị là empty string, `None`, hoặc `undefined`. Nếu kubectl thất bại, stdout có thể là empty string, cần dùng default trước khi `from_json`.

---

#### Task 4: Đánh dấu skipped khi kubectl lỗi

```yaml
- name: JOB-K8S-02 | Mark event check skipped when kubectl fails
  ansible.builtin.set_fact:
    k8s_event_skipped: >-
      {{
        k8s_event_skipped
        + [
          {
            'job': 'JOB-K8S-02',
            'target': 'cluster',
            'severity': 'skipped',
            'check': 'k8s.events.read',
            'message': 'Cannot read Kubernetes events',
            'evidence': k8s_events_json.stderr_lines | default([])
          }
        ]
      }}
  changed_when: false
  when: k8s_events_json.rc != 0
```

---

#### Task 5: Lọc Warning event

```yaml
- name: JOB-K8S-02 | Extract Warning events
  ansible.builtin.set_fact:
    k8s_warning_events: >-
      {{
        k8s_events_raw.get('items', [])
        | default([])
        | selectattr('type', 'equalto', 'Warning')
        | list
      }}
  changed_when: false
```

Event `type=Normal` là vận hành bình thường (pod started, container created). Chỉ `type=Warning` cần chú ý.

---

#### Task 6: Tạo findings từ Warning event

```yaml
- name: JOB-K8S-02 | Create findings from Warning events
  ansible.builtin.set_fact:
    k8s_event_findings: >-
      {{
        k8s_event_findings
        + [
          {
            'job': 'JOB-K8S-02',
            'target': (
              (item.get('metadata', {}).get('namespace', item.get('namespace', 'default')))
              ~ '/'
              ~ (item.get('involvedObject', {}).get('kind', item.get('regarding', {}).get('kind', 'Object')))
              ~ '/'
              ~ (item.get('involvedObject', {}).get('name', item.get('regarding', {}).get('name', item.get('metadata', {}).get('name', 'unknown'))))
            ),
            'severity': 'warning',
            'check': 'k8s.event.' ~ item.get('reason', 'warning'),
            'message': item.get('message', item.get('note', 'Kubernetes warning event')),
            'evidence': [
              'reason=' ~ item.get('reason', ''),
              'count=' ~ (item.get('count', item.get('series', {}).get('count', 1)) | string),
              'lastTimestamp=' ~ item.get('lastTimestamp', item.get('eventTime', item.get('deprecatedLastTimestamp', '')))
            ]
          }
        ]
      }}
  loop: "{{ k8s_warning_events }}"
  changed_when: false
```

**Target format: `namespace/kind/name`**

Ví dụ: `kube-system/Pod/coredns-abc123`

**Hỗ trợ cả Event API cũ và mới:**

| Field | API cũ (`v1 Event`) | API mới (`events.k8s.io/v1`) |
|-------|---------------------|-------------------------------|
| Object liên quan | `involvedObject.name` | `regarding.name` |
| Thông điệp | `message` | `note` |
| Thời gian | `lastTimestamp` | `eventTime` hoặc `deprecatedLastTimestamp` |
| Số lần lặp | `count` | `series.count` |

Code dùng `.get('involvedObject', {}).get('name', ...)` với fallback sang API mới để tương thích cả hai.

---

### 6.5 JOB-K8S-03 – Kiểm tra và tạo cảnh báo

**File:** `tasks/job_k8s_03_alerts.yml`

Job này tổng hợp dữ liệu từ JOB-K8S-01 và JOB-K8S-02 để sinh ra danh sách alert, không phụ thuộc vào Prometheus hay Alertmanager.

---

#### Task 1: Khởi tạo

```yaml
- name: JOB-K8S-03 | Initialize alert result
  ansible.builtin.set_fact:
    k8s_generated_alerts: []
    k8s_external_alerts: []
    k8s_alert_raw: {}
  changed_when: false
```

---

#### Task 2: Tạo alert từ Warning event

```yaml
- name: JOB-K8S-03 | Generate alerts from Warning events
  ansible.builtin.set_fact:
    k8s_generated_alerts: >-
      {{
        k8s_generated_alerts
        + [
          {
            'job': 'JOB-K8S-03',
            'target': (item.get('metadata', {}).get('namespace', 'default')) ~ '/' ~ (item.get('involvedObject', {}).get('name', item.get('regarding', {}).get('name', 'unknown'))),
            'severity': 'warning',
            'check': 'k8s.alert.warning_event',
            'message': item.get('reason', 'Warning') ~ ': ' ~ item.get('message', item.get('note', '')),
            'evidence': [
              'reason=' ~ item.get('reason', ''),
              'count=' ~ (item.get('count', item.get('series', {}).get('count', 1)) | string)
            ]
          }
        ]
      }}
  loop: "{{ k8s_warning_events | default([]) }}"
  changed_when: false
```

Dữ liệu `k8s_warning_events` đến từ JOB-K8S-02. Vì dùng `import_tasks` (static), biến được chia sẻ trong cùng play scope.

---

#### Task 3: Tạo alert từ node condition bất thường

```yaml
- name: JOB-K8S-03 | Generate alerts from NotReady or Pressure nodes
  ansible.builtin.set_fact:
    k8s_generated_alerts: >-
      {{
        k8s_generated_alerts
        + [
          {
            'job': 'JOB-K8S-03',
            'target': item.0.metadata.name,
            'severity': 'critical' if item.1.type == 'Ready' else 'warning',
            'check': 'k8s.node.' ~ item.1.type,
            'message': 'Node condition is not healthy: ' ~ item.1.type ~ '=' ~ item.1.status,
            'evidence': [
              'node=' ~ item.0.metadata.name,
              'condition=' ~ item.1.type,
              'status=' ~ item.1.status,
              'reason=' ~ (item.1.reason | default(''))
            ]
          }
        ]
      }}
  loop: "{{ ((k8s_resource_raw | default({})).get('nodes', {}).get('items', [])) | subelements('status.conditions', skip_missing=True) }}"
  changed_when: false
  when:
    - (item.1.type == 'Ready' and item.1.status != 'True') or
      (item.1.type in ['MemoryPressure', 'DiskPressure', 'PIDPressure'] and item.1.status == 'True')
```

**`subelements('status.conditions', skip_missing=True)`**

Filter `subelements` transform list of dicts thành list of tuples. Mỗi tuple là `(parent_dict, sub_element)`:

```
Input: [node_cp01, node_cp02]
node_cp01.status.conditions = [Ready, MemoryPressure, DiskPressure]

Output: [
  (node_cp01, Ready),
  (node_cp01, MemoryPressure),
  (node_cp01, DiskPressure),
  (node_cp02, Ready),
  ...
]
```

`item.0` = node, `item.1` = condition.
`skip_missing=True` bỏ qua node không có field `status.conditions`.

**Logic cảnh báo:**

| Condition | Status khỏe | Status bệnh | Severity |
|-----------|-------------|-------------|---------|
| `Ready` | `True` | `False` hoặc `Unknown` | `critical` |
| `MemoryPressure` | `False` | `True` | `warning` |
| `DiskPressure` | `False` | `True` | `warning` |
| `PIDPressure` | `False` | `True` | `warning` |

---

#### Task 4: Tạo alert từ pod không healthy

```yaml
- name: JOB-K8S-03 | Generate alerts from non-running pods
  ansible.builtin.set_fact:
    k8s_generated_alerts: >-
      {{
        k8s_generated_alerts
        + [
          {
            'job': 'JOB-K8S-03',
            'target': item.get('metadata', {}).get('namespace', 'default') ~ '/' ~ item.get('metadata', {}).get('name', 'unknown'),
            'severity': 'warning',
            'check': 'k8s.pod.phase',
            'message': 'Pod is not running or completed: ' ~ (item.status.phase | default('Unknown')),
            'evidence': [
              'namespace=' ~ item.get('metadata', {}).get('namespace', 'default'),
              'pod=' ~ item.get('metadata', {}).get('name', 'unknown'),
              'phase=' ~ item.get('status', {}).get('phase', 'Unknown')
            ]
          }
        ]
      }}
  loop: "{{ (k8s_resource_raw | default({})).get('pods', {}).get('items', []) }}"
  changed_when: false
  when:
    - item.get('status', {}).get('phase', 'Unknown') not in ['Running', 'Succeeded']
```

**Pod phase:**

| Phase | Ý nghĩa | Alert? |
|-------|---------|--------|
| `Running` | Pod đang chạy bình thường | Không |
| `Succeeded` | Pod hoàn thành (Job/CronJob) | Không |
| `Pending` | Pod chưa được schedule hoặc đang pull image | Có |
| `Failed` | Pod thất bại và không restart | Có |
| `Unknown` | API server không liên lạc được node | Có |

---

#### Task 5: Lấy alert từ Alertmanager (nếu có)

```yaml
- name: JOB-K8S-03 | Try Alertmanager API when configured
  ansible.builtin.uri:
    url: "{{ k8s_check_alertmanager_url }}/api/v2/alerts"
    method: GET
    return_content: true
  register: k8s_alertmanager_response
  changed_when: false
  failed_when: false
  when: k8s_check_alertmanager_url | length > 0
```

**Module `ansible.builtin.uri`:**

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `url` | Alertmanager API URL | Endpoint lấy alert đang active |
| `method` | `GET` | HTTP GET request |
| `return_content` | `true` | Lưu response body vào `content` và `json` |

**`when: k8s_check_alertmanager_url | length > 0`** – Chỉ chạy khi biến `k8s_check_alertmanager_url` không rỗng.

**Alertmanager API:** `/api/v2/alerts` trả list alert đang firing/pending theo format:

```json
[
  {
    "labels": { "alertname": "KubePodCrashLooping", "namespace": "default" },
    "annotations": { "summary": "Pod is crash looping" },
    "status": { "state": "firing" },
    "startsAt": "2024-01-01T10:00:00Z"
  }
]
```

---

#### Task 6: Lưu external alert

```yaml
- name: JOB-K8S-03 | Save external Alertmanager alerts
  ansible.builtin.set_fact:
    k8s_external_alerts: "{{ k8s_alertmanager_response.json | default([]) }}"
  changed_when: false
  when:
    - k8s_check_alertmanager_url | length > 0
    - k8s_alertmanager_response is defined
    - k8s_alertmanager_response.status | default(0) == 200
```

**`k8s_alertmanager_response.json`** – Khi `return_content: true`, module `uri` tự parse JSON response thành dict/list.

---

### 6.6 Save report (`tasks/save_report.yml`)

**Mục tiêu:** Tổng hợp kết quả từ 3 job K8s, ghi file JSON về máy control.

**Output files:**

```
artifacts/
└── k8s/
    ├── job-k8s-01-resources.json
    ├── job-k8s-02-events.json
    ├── job-k8s-03-alerts.json
    └── kubernetes-summary.json
```

**Lưu ý:** Báo cáo K8s ghi vào `artifacts/k8s/` (một thư mục chung) thay vì tách theo host như OS. Lý do: K8s là cluster-wide, không phải per-host.

#### Cấu trúc JOB-K8S-03 report status:

```
overall =
  'critical' nếu có alert severity=critical (Node NotReady)
  'warning'  nếu có alert severity=warning (Warning events, pod failed, pressure)
  'ok'       nếu không có alert
```

#### Cấu trúc summary report:

```
overall =
  'critical' nếu JOB-K8S-03 critical
  'warning'  nếu JOB-K8S-01/02/03 warning hoặc skipped
  'ok'       nếu tất cả ok
```

---

## 7. Quy ước chung và schema kết quả

### Schema finding/alert chuẩn

Mọi finding, alert, skipped entry phải theo schema:

```yaml
job: JOB-OS-01              # Mã job tạo ra finding
target: "hostname"           # Host, namespace/object bị ảnh hưởng
severity: warning            # critical | warning | info | skipped
check: os.cpu.load           # Mã kiểm tra ngắn để lọc/gom nhóm
message: "Load average exceeds threshold"  # Mô tả dễ đọc
evidence:                    # Bằng chứng cụ thể từ command/API
  - "load_1m=9.5"
  - "cpu_count=8"
detected_at: "{{ ansible_date_time.iso8601 }}"  # Không bắt buộc trong code hiện tại
```

### Nguyên tắc `changed_when` và `failed_when`

| Rule | Áp dụng |
|------|---------|
| `changed_when: false` | **Bắt buộc** cho mọi task kiểm tra (không thay đổi hệ thống) |
| `failed_when: false` | Khi command có thể không tồn tại, output có thể rỗng, hoặc lỗi là trạng thái bình thường |
| Không dùng `ignore_errors: true` | `ignore_errors` che giấu lỗi. Thay vào đó dùng `failed_when: false` và lưu stderr |

### Biến kết quả theo layer

| Layer | Biến | Mục đích |
|-------|------|---------|
| Raw | `os_node_resource_raw`, `k8s_resource_raw`, ... | Dữ liệu thô đầy đủ từ command/API |
| Metrics | `os_node_resource_metrics`, `k8s_resource_metrics` | Số liệu ngắn gọn cho report |
| Findings | `os_node_resource_findings`, `k8s_event_findings`, ... | Warning/critical theo schema chuẩn |
| Skipped | `os_smart_skipped`, `k8s_resource_skipped`, ... | Lý do không kiểm tra được |
| Report | `os_job_01_report`, `k8s_job_01_report`, ... | Dict hoàn chỉnh ghi vào JSON |
| Summary | `os_summary_report`, `k8s_summary_report` | File nhỏ xem nhanh status |

---

## 8. Cách chạy

### Chạy từ thư mục dự án

```bash
cd ansible-ops
```

### Syntax check (không cần host thật)

```bash
# Kiểm tra cú pháp YAML và Ansible
ansible-playbook playbooks/check_all.yml --syntax-check
```

### Chạy toàn bộ (OS + K8s)

```bash
ansible-playbook playbooks/check_all.yml --ask-vault-pass
```

### Chạy chỉ OS checks

```bash
ansible-playbook playbooks/check_os.yml --ask-vault-pass
```

### Chạy chỉ K8s checks

```bash
ansible-playbook playbooks/check_kubernetes.yml --ask-vault-pass
```

### Chạy riêng từng job OS

```bash
# Chỉ JOB-OS-01 (tài nguyên node)
ansible-playbook playbooks/check_os.yml --tags job_os_01 --ask-vault-pass

# Chỉ JOB-OS-02 (event log)
ansible-playbook playbooks/check_os.yml --tags job_os_02 --ask-vault-pass

# Chỉ JOB-OS-03 (cron jobs)
ansible-playbook playbooks/check_os.yml --tags job_os_03 --ask-vault-pass

# Chỉ JOB-OS-04 (SMART)
ansible-playbook playbooks/check_os.yml --tags job_os_04 --ask-vault-pass
```

> **Lưu ý:** `save_report.yml` luôn chạy kèm vì có tag `always`.

### Chạy riêng từng job K8s

```bash
# Chỉ JOB-K8S-01 (tài nguyên)
ansible-playbook playbooks/check_kubernetes.yml --tags job_k8s_01 --ask-vault-pass

# Chỉ JOB-K8S-02 (events)
ansible-playbook playbooks/check_kubernetes.yml --tags job_k8s_02 --ask-vault-pass

# Chỉ JOB-K8S-03 (alerts – cần chạy 01 và 02 trước để có dữ liệu)
ansible-playbook playbooks/check_kubernetes.yml --tags job_k8s_03 --ask-vault-pass
```

### Bật debug raw data

```bash
# Thêm -e os_check_include_raw=true để report JSON kèm full raw output
ansible-playbook playbooks/check_os.yml -e os_check_include_raw=true --ask-vault-pass

# Tương tự cho K8s
ansible-playbook playbooks/check_kubernetes.yml -e k8s_check_include_raw=true --ask-vault-pass
```

### Chạy trên host cụ thể

```bash
# Chỉ kiểm tra node cp01
ansible-playbook playbooks/check_os.yml --limit cp01 --ask-vault-pass

# Chỉ kiểm tra worker nodes
ansible-playbook playbooks/check_os.yml --limit kubernetes_workers --ask-vault-pass
```

### Dry run (check mode)

```bash
# --check không thực thi thật, chỉ mô phỏng
# Lưu ý: command/shell module không chạy trong check mode, nên kết quả không hoàn toàn chính xác
ansible-playbook playbooks/check_os.yml --check --ask-vault-pass
```

### Xem output chi tiết hơn

```bash
# -v: verbose, -vv: rất verbose, -vvv: debug
ansible-playbook playbooks/check_os.yml -v --ask-vault-pass
```

---

## 9. Thứ tự triển khai khuyến nghị

Khi phát triển thêm logic phân tích (parse finding từ raw data), nên theo thứ tự:

1. **Viết JOB-OS-01** → kiểm tra raw output, in ra debug, xác nhận lấy được dữ liệu.
2. **Parse JOB-OS-01** → thêm logic so sánh với ngưỡng để sinh finding warning/critical.
3. **Viết JOB-OS-02** → kiểm tra lọc log đúng pattern.
4. **Viết JOB-K8S-01** → kiểm tra JSON node/pod parse đúng.
5. **Viết JOB-K8S-02** → kiểm tra lọc Warning event.
6. **Viết JOB-K8S-03** → tổng hợp alert từ dữ liệu các job trước.
7. **Viết JOB-OS-03 và JOB-OS-04** → ít ngưỡng hơn, chủ yếu kiểm kê.
8. **Hoàn thiện save_report.yml** → đảm bảo status tổng hợp chính xác.
9. **Chạy toàn bộ trên môi trường lab** → xem báo cáo JSON thực tế.
---

## 10. Tags va cach chay rieng le

Phan nay bo sung cho tat ca role hien tai. Muc tieu cua tag la cho phep chay
rieng tung nhom cong viec khi can test nhanh, debug loi, hoac chi muon cai mot
nhom tool.

### 10.1 Nguyen tac gan tag

- Tag cap playbook dung de chay nhom lon: `prepare_tools`, `os`, `kubernetes`, `checks`.
- Tag cap job dung de chay tung job: `job_os_01`, `job_k8s_01`, ...
- Tag theo ten nghiep vu dung de doc de hieu hon: `os_resources`, `k8s_events`, `smart_tools`.
- `save_report.yml` duoc gan tag `always`, nen khi chay rieng mot job, task ghi report van chay.
- `prepare_tools` khong tao report JSON. Role nay chi check command, neu thieu thi cai package tuong ung.

### 10.2 Tags cua prepare_tools

| Tag | Tac dung |
|---|---|
| `prepare_tools` | Chay toan bo role chuan bi cong cu |
| `tool_check` | Chi chay task check command, khong cai package |
| `tool_install` | Chay check command va cai package neu thieu |
| `os_tools` | Cong cu OS chung: `nproc`, `free`, `df`, `findmnt`, `awk`, `ps`, `journalctl`, `systemctl` |
| `cron_tools` | Cong cu cron: `crontab` |
| `smart_tools` | Cong cu SMART: `smartctl` |

```bash
# Chay toan bo prepare_tools
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
  --ask-vault-pass -v

# Chi check command, khong cai
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
  --ask-vault-pass --tags tool_check -v

# Chi chuan bi smartctl cho JOB-OS-04
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
  --ask-vault-pass --tags smart_tools -v
```

### 10.3 Tags cua OS checks

| Tag | Tac dung |
|---|---|
| `os` | Chay toan bo role OS khi dung `check_all.yml` |
| `checks` | Chay cac role kiem tra |
| `job_os_01` / `os_resources` | Chay `JOB-OS-01` - tai nguyen node |
| `job_os_02` / `os_event_logs` | Chay `JOB-OS-02` - event log OS |
| `job_os_03` / `os_cron_jobs` | Chay `JOB-OS-03` - cron job OS |
| `job_os_04` / `os_smart` | Chay `JOB-OS-04` - SMART |
| `os_report` | Chay phan ghi report OS |

```bash
# Chay tat ca job OS
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml \
  --ask-vault-pass -v

# Chi chay JOB-OS-01
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml \
  --ask-vault-pass --tags job_os_01 -v

# Chi chay JOB-OS-04 SMART
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_os.yml \
  --ask-vault-pass --tags job_os_04 -v
```

### 10.4 Tags cua Kubernetes checks

| Tag | Tac dung |
|---|---|
| `kubernetes` | Chay toan bo role Kubernetes khi dung `check_all.yml` |
| `checks` | Chay cac role kiem tra |
| `job_k8s_01` / `k8s_resources` | Chay `JOB-K8S-01` - tai nguyen cluster |
| `job_k8s_02` / `k8s_events` | Chay `JOB-K8S-02` - event toan cum |
| `job_k8s_03` / `k8s_alerts` | Chay `JOB-K8S-03` - alert |
| `k8s_report` | Chay phan ghi report Kubernetes |

```bash
# Chay tat ca job Kubernetes
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_kubernetes.yml \
  --ask-vault-pass -v

# Chi chay JOB-K8S-01
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_kubernetes.yml \
  --ask-vault-pass --tags job_k8s_01 -v

# Chay JOB-K8S-01 va JOB-K8S-02 de lay du ngu canh cho event/resource
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_kubernetes.yml \
  --ask-vault-pass --tags job_k8s_01,job_k8s_02 -v
```

Luu y: `JOB-K8S-03` sinh alert dua tren bien duoc tao tu `JOB-K8S-01` va
`JOB-K8S-02`. Neu chi chay rieng `job_k8s_03`, report co the thieu ngu canh
node/pod/event.

### 10.5 Chay tat ca hoac chay theo nhom tu check_all.yml

`check_all.yml` import theo thu tu:

```yaml
- import_playbook: prepare_tools.yml
  tags:
    - prepare_tools

- import_playbook: check_os.yml
  tags:
    - os
    - checks

- import_playbook: check_kubernetes.yml
  tags:
    - kubernetes
    - checks
```

```bash
# Chay tat ca: prepare tools + OS + Kubernetes
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml \
  --ask-vault-pass -v

# Chi chay prepare_tools tu check_all
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml \
  --ask-vault-pass --tags prepare_tools -v

# Chi chay OS tu check_all
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml \
  --ask-vault-pass --tags os -v

# Chi chay Kubernetes tu check_all
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml \
  --ask-vault-pass --tags kubernetes -v

# Chay ca OS va Kubernetes, bo qua prepare_tools
ansible-playbook -i inventories/lab/inventory.ini playbooks/check_all.yml \
  --ask-vault-pass --tags checks -v
```

### 10.6 Cach them tag cho job moi

Khi them mot job moi vao role, them tag ngay tai `tasks/main.yml`:

```yaml
- name: JOB-OS-05 - ten job moi
  ansible.builtin.import_tasks: job_os_05_new_check.yml
  tags:
    - job_os_05
    - os_new_check
```

Neu job co report rieng, dam bao `save_report.yml` doc bien bang `default(...)`
de khi chay tag rieng cac job khac khong lam report bi loi.
