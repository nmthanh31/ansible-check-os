# Inventories

Hiện dự án chỉ sử dụng inventory `lab/`. `inventory.ini` chứa host/group,
`group_vars/all.yml` chứa biến chung. Không lưu credential plain text.

Máy cần kiểm tra phần cứng phải thuộc group `physical_servers`:

```ini
[physical_servers]
physical-server-01 ansible_host=192.0.2.11 ansible_user=audit \
  bmc_address=192.0.2.111 bmc_vendor=dell

[physical_servers:vars]
bmc_username={{ vault_bmc_username }}
bmc_password={{ vault_bmc_password }}
```

`ansible_host` là IP hệ điều hành dùng cho SSH. `bmc_address` là IP quản trị
iDRAC/iLO/IPMI. Hai địa chỉ này thường khác nhau.
