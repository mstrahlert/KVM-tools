# KVM-tools

Various tools for the KVM hypervisor.

## list_vms.py
List all VMs with their allocated memory and cpu, along with a grand total.

## virt-backup.py
Backup VMs by utilising LVM snapshots to copy the diskimage to secondary storage. Makes use of http://gitweb.firewall-services.com/?p=virt-backup;a=blob_plain;f=virt-backup;hb=HEAD to make the actual backup.

Configuration is done by editing virt-backup.conf.

In order to run, add virt-backup.py as a daily reoccuring entry in crontab.
