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

  arr = {}
  for (i, vm) in enumerate(guest_vms.splitlines()):
    if len(vm.split()) == False or len(vm.split()) < 3 or vm.split()[0] == "Id":
      continue

    arr[i] = vm.split()

  for vm in sorted(arr.items(), key=lambda item: item[1][1]):
    xmlroot = ET.fromstring(cmdline("virsh dumpxml %s" % vm[1][1]))
    _mem = xmlroot.findtext("memory")
    _cpu = xmlroot.findtext("vcpu")
    _title = xmlroot.findtext("title")
    _memtot += int(_mem)
    _cputot += int(_cpu)

    print("%35s: %.2fGb, %s vcpu, %s" % ((truncate(_title, 34) or vm[1][1]),
                                         int(_mem) / 1024 / 1024., _cpu,
                                         " ".join(vm[1][2:])))

  print("%35s: %.2fGb, %s vcpu" % ("** Total **", int(_memtot) / 1024 / 1024.,
                                   _cputot))

if __name__ == "__main__":
  main()
