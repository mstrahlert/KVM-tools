#!/usr/bin/env python
#
# Magnus Strahlert @ 180305
#  List memory & cpu of all KVM VMs along with the grand total

from subprocess import PIPE, Popen
import xml.etree.ElementTree as ET

def cmdline(command):
  process = Popen(args = command, stdout = PIPE, shell = True,
                  universal_newlines = True)
  return process.communicate()[0]

def truncate(text, maxlen):
  if not text:
    return text
  if len(text) > maxlen:
    text = text[:maxlen-2] + ".."

  return text

def main():
  guest_vms = cmdline("virsh list --all --table")

  _memtot=0
  _cputot=0

  for vm in guest_vms.splitlines():
    vm = vm.split()
    if len(vm) == False or len(vm) < 3 or vm[0] == "Id":
      continue

    xmlroot = ET.fromstring(cmdline("virsh dumpxml %s" % vm[1])) 
    _mem = xmlroot.findtext("memory")
    _cpu = xmlroot.findtext("vcpu")
    _title = xmlroot.findtext("title")
    _memtot += int(_mem)
    _cputot += int(_cpu)

    print("%35s: %.2fGb, %s vcpu, %s" % ((truncate(_title, 34) or vm[1]),
                                         int(_mem) / 1024 / 1024., _cpu,
                                         " ".join(vm[2:])))

  print("%35s: %.2fGb, %s vcpu" % ("** Total **", int(_memtot) / 1024 / 1024.,
                                   _cputot))

if __name__ == "__main__":
  main()
