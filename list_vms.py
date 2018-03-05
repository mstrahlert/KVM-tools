#!/usr/bin/env python
#
# Magnus Strahlert @ 180305
#  List memory & cpu of all KVM VMs along with the grand total

from subprocess import PIPE, Popen
import xml.etree.ElementTree as ET

def cmdline(command):
  process = Popen(args = command, stdout = PIPE, shell = True, universal_newlines = True)
  return process.communicate()[0]

def main():
  guest_vms = cmdline("virsh list --all --name")

  _memtot=0
  _cputot=0

  for vm in guest_vms.splitlines():
    if len(vm) == False:
      continue

    xmlroot = ET.fromstring(cmdline("virsh dumpxml %s" % vm)) 
    _mem = xmlroot.findtext("memory")
    _cpu = xmlroot.findtext("vcpu")
    _memtot += int(_mem)
    _cputot += int(_cpu)

    print("%25s: %.2fGb, %s vcpu" % (vm, int(_mem) / 1024 / 1024., _cpu))

  print("%25s: %.2fGb, %s vcpu" % ("** Total **", int(_memtot) / 1024 / 1024., _cputot))

if __name__ == "__main__":
  main()