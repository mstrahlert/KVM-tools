# KVM-tools

Various tools for the KVM hypervisor.

## list_vms.py
List all VMs with their allocated memory and cpu, along with a grand total.

## virt-backup.py
Backup VMs by utilising LVM snapshots to copy the diskimage to secondary storage. Makes use of [virt-backup](http://gitweb.firewall-services.com/?p=virt-backup;a=blob_plain;f=virt-backup;hb=HEAD) to make the actual backup. Unless setting api to libvirt in configuration file `/etc/virt-backup.conf` which is the default in the provided example configuration.

In order to run, add `virt-backup.py` as a service in your daemon-tool.
Configuration is provided for systemd in `virt-backup.service`.

    cp virt-backup.service /etc/systemd/system/
    systemctl enable virt-backup
    systemctl start virt-backup
