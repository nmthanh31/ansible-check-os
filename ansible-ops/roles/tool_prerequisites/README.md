# tool_prerequisites

Role nay chay truoc cac job kiem tra de dam bao node co cong cu can thiet.
Logic duoc giu don gian: check command, neu chua co thi cai package tuong ung.

## Nhom tag

| Tag | Tac dung |
|---|---|
| `prepare_tools` | Chay toan bo role |
| `tool_check` | Chay cac task check command |
| `tool_install` | Chay cac task cai package |
| `os_tools` | Cong cu cho `JOB-OS-01/02`: `nproc`, `free`, `df`, `findmnt`, `awk`, `ps`, `journalctl`, `systemctl` |
| `cron_tools` | Cong cu cho `JOB-OS-03`: `crontab` |
| `smart_tools` | Cong cu cho `JOB-OS-04`: `smartctl` |

## Lenh chay

Chay tat ca:

```bash
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass -v
```

Chi chuan bi SMART:

```bash
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags smart_tools -v
```

Chi chuan bi cron:

```bash
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags cron_tools -v
```

Chi chuan bi cong cu OS chung:

```bash
ansible-playbook -i inventories/lab/inventory.ini playbooks/prepare_tools.yml \
--ask-vault-pass --tags os_tools -v
```
